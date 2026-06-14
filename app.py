import asyncio
import json
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import gradio as gr
from extract_pdf_data import extract_text_from_pdf
from get_structured_output import get_structured_output
from agent_execution import stream_agent_async
from email_handler import fetch_latest_pdf_attachment

# ── helpers ──────────────────────────────────────────────────────────────────

DECISION_BADGE = {
    "APPROVED": "🟢 APPROVED",
    "FLAGGED":  "🟡 FLAGGED",
    "REJECTED": "🔴 REJECTED",
}

def _parse_analysis_json(raw: str) -> dict | None:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


def _fmt_structured_data(data: dict) -> str:
    lines = []
    lines.append(f"**Applicant:** {data.get('applicant_name', 'N/A')}")
    lines.append(f"**Email:** {data.get('applicant_email', 'N/A')}")
    lines.append(f"**Unit:** {data.get('unit_id', 'N/A')}")

    rent = data.get("monthly_rent", {})
    lines.append(f"**Monthly Rent:** {rent.get('amount', 'N/A')} ({rent.get('written_form', 'N/A')})")

    income = data.get("monthly_income", {})
    confirmed = "✅ confirmed" if income.get("confirmed") else "⚠️ unconfirmed"
    lines.append(f"**Monthly Income:** {income.get('amount', 'N/A')} — {confirmed}")
    if income.get("confirmed_by") and income["confirmed_by"] != "N/A":
        lines.append(f"  Confirmed by: {income['confirmed_by']}")

    if data.get("pet_ownership"):
        pets = data.get("pets", {})
        qty = pets.get("all_pets_quantity", 0)
        lines.append(f"**Pets:** {qty} declared")
        for p in pets.get("all_pets", []):
            lines.append(
                f"  • {p.get('type', 'N/A')} | breed: {p.get('breed', 'N/A')} "
                f"| weight: {p.get('weight', 'N/A')}"
            )
    else:
        lines.append("**Pets:** None declared")

    if data.get("additional_comments") and data["additional_comments"] != "N/A":
        lines.append(f"**Comments:** {data['additional_comments']}")

    return "\n\n".join(lines)


def _fmt_tool_calls(tool_calls: list) -> tuple[str, str]:
    if not tool_calls:
        return "_No tool calls recorded._", "_No documents retrieved._"

    calls_lines = []
    docs_lines = []
    for i, tc in enumerate(tool_calls, start=1):
        name = tc["name"]
        is_reply = name == "reply_email_tool"
        label = tc.get("query", "")

        calls_lines.append(f"**Call {i}** — `{name}`")
        if is_reply:
            calls_lines.append("> Action: *Sending reply email to applicant*")
        else:
            calls_lines.append(f"> Query: *{label}*")
        status = "✅ done" if tc.get("result") else "⏳ waiting..."
        calls_lines.append(f"> Status: {status}")
        calls_lines.append("")

        if is_reply:
            docs_lines.append(f"### Call {i} — Reply Email Sent")
            if tc.get("result"):
                docs_lines.append(tc["result"])
            else:
                docs_lines.append("_⏳ Sending..._")
        else:
            docs_lines.append(f"### Call {i} — `{label}`")
            if tc.get("result"):
                docs_lines.append(tc["result"])
            else:
                docs_lines.append("_⏳ Retrieving..._")
        docs_lines.append("")

    return "\n".join(calls_lines), "\n".join(docs_lines)


def _fmt_analysis(parsed: dict) -> str:
    decision = parsed.get("decision", "UNKNOWN")
    badge = DECISION_BADGE.get(decision, decision)
    check_icon = lambda v: "✅" if v == "PASS" else ("❌" if v == "FAIL" else "⚠️")

    lines = [
        f"## {badge}",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Income-to-Rent Ratio | **{parsed.get('income_to_rent_ratio', 'N/A')}** |",
        f"| Income Check | {check_icon(parsed.get('income_check'))} {parsed.get('income_check', 'N/A')} |",
        f"| Pet Check | {check_icon(parsed.get('pet_check'))} {parsed.get('pet_check', 'N/A')} |",
        f"| Completeness Check | {check_icon(parsed.get('completeness_check'))} {parsed.get('completeness_check', 'N/A')} |",
        "",
    ]

    reasons = parsed.get("reasons", [])
    if reasons:
        lines.append("**Reasons:**")
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")

    notes = parsed.get("notes", "")
    if notes:
        lines.append(f"**Notes:** {notes}")

    return "\n".join(lines)


# ── streaming pipeline ────────────────────────────────────────────────────────

_IDLE = (
    "_Waiting..._",   # email_info
    "_Waiting..._",   # structured
    "_Waiting..._",   # tool_calls
    "_Waiting..._",   # retrieved_docs
    "_Waiting..._",   # analysis
)

async def run_pipeline():
    email_md = "⏳ **Fetching latest PDF attachment from email...**"
    structured_md, calls_md, docs_md, analysis_md = "_Waiting..._", "_Waiting..._", "_Waiting..._", "_Waiting..._"
    yield (email_md, structured_md, calls_md, docs_md, analysis_md)

    # ── step 1: fetch email ──────────────────────────────────────────────────
    email_result = await asyncio.to_thread(fetch_latest_pdf_attachment)
    if email_result["status"] != "success":
        yield (f"❌ Email fetch failed: {email_result.get('message')}", structured_md, calls_md, docs_md, analysis_md)
        return

    email_md = (
        f"**From:** {email_result.get('sender', 'N/A')}\n\n"
        f"**Subject:** {email_result.get('subject', 'N/A')}\n\n"
        f"**Attachment saved to:** `{email_result.get('pdf_path')}`"
    )
    structured_md = "⏳ **Extracting and parsing application fields...**"
    yield (email_md, structured_md, calls_md, docs_md, analysis_md)

    # ── step 2: extract PDF ──────────────────────────────────────────────────
    pdf_path = email_result["pdf_path"]
    extraction = await asyncio.to_thread(extract_text_from_pdf, pdf_path)
    if extraction["status"] != "success":
        yield (email_md, f"❌ Extraction failed: {extraction.get('message')}", calls_md, docs_md, analysis_md)
        return

    # ── step 3: structured output ────────────────────────────────────────────
    structured_result = await asyncio.to_thread(get_structured_output, extraction["text"])
    if structured_result["status"] != "success":
        yield (email_md, f"❌ Parsing failed: {structured_result.get('message')}", calls_md, docs_md, analysis_md)
        return

    structured_data = structured_result["message"]
    structured_md = _fmt_structured_data(structured_data)
    calls_md = "⏳ **Agent is querying policy knowledge base...**"
    yield (email_md, structured_md, calls_md, docs_md, analysis_md)

    # ── step 4: stream agent ─────────────────────────────────────────────────
    async for event in stream_agent_async(structured_data, email_data=email_result):
        etype = event["type"]

        if etype == "error":
            analysis_md = f"❌ Agent error: {event['message']}"
            yield (email_md, structured_md, calls_md, docs_md, analysis_md)
            return

        elif etype == "tool_call":
            calls_md, docs_md = _fmt_tool_calls(event["all_calls"])
            yield (email_md, structured_md, calls_md, docs_md, analysis_md)

        elif etype == "tool_result":
            calls_md, docs_md = _fmt_tool_calls(event["all_calls"])
            yield (email_md, structured_md, calls_md, docs_md, analysis_md)

        elif etype == "final":
            calls_md, docs_md = _fmt_tool_calls(event.get("tool_calls", []))
            parsed = _parse_analysis_json(event["response"])
            if parsed:
                analysis_md = _fmt_analysis(parsed)
            else:
                analysis_md = "⚠️ _Model did not return structured JSON. Raw response:_\n\n" + event["response"]
            yield (email_md, structured_md, calls_md, docs_md, analysis_md)


# ── UI ────────────────────────────────────────────────────────────────────────

SECTION_STYLE = "border-left: 3px solid #ccc; padding-left: 12px; margin-bottom: 8px;"

with gr.Blocks(title="Lease Application Analyzer") as demo:
    gr.Markdown("# 🏢 Lease Application Analyzer\nFetches the latest unread PDF attachment from Gmail and runs the full compliance pipeline. All steps appear live as they complete.")

    with gr.Row():
        fetch_btn = gr.Button("📧 Fetch & Analyze Latest Email", variant="primary", size="lg")
        clear_btn = gr.Button("🗑️ Clear", variant="secondary", size="lg")

    gr.Markdown("---")

    gr.Markdown("### 📨 Email Source")
    email_out = gr.Markdown(value="_Press the button to start._")

    gr.Markdown("---")

    gr.Markdown("### 📋 Extracted Application Data")
    structured_out = gr.Markdown(value="_Waiting..._")

    gr.Markdown("---")

    gr.Markdown("### 🔍 Agent Tool Calls")
    tool_calls_out = gr.Markdown(value="_Waiting..._")

    gr.Markdown("---")

    gr.Markdown("### 📚 Retrieved Policy Documents")
    retrieved_out = gr.Markdown(value="_Waiting..._")

    gr.Markdown("---")

    gr.Markdown("### ⚖️ Analysis Decision")
    analysis_out = gr.Markdown(value="_Waiting..._")

    fetch_btn.click(
        fn=run_pipeline,
        inputs=[],
        outputs=[email_out, structured_out, tool_calls_out, retrieved_out, analysis_out],
    )

    clear_btn.click(
        fn=lambda: ("_Press the button to start._", "_Waiting..._", "_Waiting..._", "_Waiting..._", "_Waiting..._"),
        inputs=[],
        outputs=[email_out, structured_out, tool_calls_out, retrieved_out, analysis_out],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())


# ── helpers ──────────────────────────────────────────────────────────────────

DECISION_BADGE = {
    "APPROVED": "🟢 APPROVED",
    "FLAGGED":  "🟡 FLAGGED",
    "REJECTED": "🔴 REJECTED",
}

def _parse_analysis_json(raw: str) -> dict | None:
    """Try progressively looser strategies to extract the JSON object."""
    # 1. Strip markdown fences and try direct parse
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # 2. Find the first {...} block anywhere in the response
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


def _fmt_structured_data(data: dict) -> str:
    lines = []
    lines.append(f"**Applicant:** {data.get('applicant_name', 'N/A')}")
    lines.append(f"**Email:** {data.get('applicant_email', 'N/A')}")
    lines.append(f"**Unit:** {data.get('unit_id', 'N/A')}")

    rent = data.get("monthly_rent", {})
    lines.append(f"**Monthly Rent:** {rent.get('amount', 'N/A')} ({rent.get('written_form', 'N/A')})")

    income = data.get("monthly_income", {})
    confirmed = "✅ confirmed" if income.get("confirmed") else "⚠️ unconfirmed"
    lines.append(f"**Monthly Income:** {income.get('amount', 'N/A')} — {confirmed}")
    if income.get("confirmed_by") and income["confirmed_by"] != "N/A":
        lines.append(f"  Confirmed by: {income['confirmed_by']}")

    if data.get("pet_ownership"):
        pets = data.get("pets", {})
        qty = pets.get("all_pets_quantity", 0)
        lines.append(f"**Pets:** {qty} declared")
        for p in pets.get("all_pets", []):
            lines.append(
                f"  • {p.get('type', 'N/A')} | breed: {p.get('breed', 'N/A')} "
                f"| weight: {p.get('weight', 'N/A')}"
            )
    else:
        lines.append("**Pets:** None declared")

    if data.get("additional_comments") and data["additional_comments"] != "N/A":
        lines.append(f"**Comments:** {data['additional_comments']}")

    return "\n\n".join(lines)


def _fmt_tool_calls(tool_calls: list) -> tuple[str, str]:
    """Return (calls_md, retrieved_docs_md)."""
    if not tool_calls:
        return "_No tool calls recorded._", "_No documents retrieved._"

    calls_lines = []
    docs_lines = []
    for i, tc in enumerate(tool_calls, start=1):
        calls_lines.append(f"**Call {i}** — `{tc['name']}`")
        calls_lines.append(f"> Query: *{tc['query']}*")
        status = "✅ result received" if tc.get("result") else "⏳ waiting for result..."
        calls_lines.append(f"> Status: {status}")
        calls_lines.append("")

        docs_lines.append(f"### Call {i} — `{tc['query']}`")
        if tc.get("result"):
            docs_lines.append(tc["result"])
        else:
            docs_lines.append("_⏳ Retrieving..._")
        docs_lines.append("")

    return "\n".join(calls_lines), "\n".join(docs_lines)


def _fmt_analysis(parsed: dict) -> str:
    decision = parsed.get("decision", "UNKNOWN")
    badge = DECISION_BADGE.get(decision, decision)
    check_icon = lambda v: "✅" if v == "PASS" else ("❌" if v == "FAIL" else "⚠️")

    lines = [
        f"## {badge}",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Income-to-Rent Ratio | **{parsed.get('income_to_rent_ratio', 'N/A')}** |",
        f"| Income Check | {check_icon(parsed.get('income_check'))} {parsed.get('income_check', 'N/A')} |",
        f"| Pet Check | {check_icon(parsed.get('pet_check'))} {parsed.get('pet_check', 'N/A')} |",
        f"| Completeness Check | {check_icon(parsed.get('completeness_check'))} {parsed.get('completeness_check', 'N/A')} |",
        "",
    ]

    reasons = parsed.get("reasons", [])
    if reasons:
        lines.append("**Reasons:**")
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")

    notes = parsed.get("notes", "")
    if notes:
        lines.append(f"**Notes:** {notes}")

    return "\n".join(lines)


# ── streaming pipeline ────────────────────────────────────────────────────────

INIT = ("_Upload a PDF and click Analyze._", "_No tool calls yet._", "_No documents retrieved yet._", "_No analysis yet._")

async def run_pipeline(pdf_file):
    if pdf_file is None:
        yield INIT
        return

    structured_md = "⏳ **Step 1/3 — Extracting text from PDF...**"
    calls_md, docs_md, analysis_md = "_Waiting..._", "_Waiting..._", "_Waiting..._"
    yield (structured_md, calls_md, docs_md, analysis_md)

    # ── step 1: extract PDF ──────────────────────────────────────────────────
    extraction = await asyncio.to_thread(extract_text_from_pdf, pdf_file)
    if extraction["status"] != "success":
        yield (f"❌ Extraction failed: {extraction.get('message')}", calls_md, docs_md, analysis_md)
        return

    structured_md = "⏳ **Step 2/3 — Parsing application fields...**"
    yield (structured_md, calls_md, docs_md, analysis_md)

    # ── step 2: structured output ────────────────────────────────────────────
    structured_result = await asyncio.to_thread(get_structured_output, extraction["text"])
    if structured_result["status"] != "success":
        yield (f"❌ Parsing failed: {structured_result.get('message')}", calls_md, docs_md, analysis_md)
        return

    structured_data = structured_result["message"]
    structured_md = _fmt_structured_data(structured_data)
    calls_md = "⏳ **Step 3/3 — Agent is querying policy knowledge base...**"
    yield (structured_md, calls_md, docs_md, analysis_md)

    # ── step 3: stream agent events ──────────────────────────────────────────
    async for event in stream_agent_async(structured_data):
        etype = event["type"]

        if etype == "error":
            analysis_md = f"❌ Agent error: {event['message']}"
            yield (structured_md, calls_md, docs_md, analysis_md)
            return

        elif etype == "tool_call":
            calls_md, docs_md = _fmt_tool_calls(event["all_calls"])
            yield (structured_md, calls_md, docs_md, analysis_md)

        elif etype == "tool_result":
            calls_md, docs_md = _fmt_tool_calls(event["all_calls"])
            yield (structured_md, calls_md, docs_md, analysis_md)

        elif etype == "final":
            calls_md, docs_md = _fmt_tool_calls(event.get("tool_calls", []))
            parsed = _parse_analysis_json(event["response"])
            if parsed:
                analysis_md = _fmt_analysis(parsed)
            else:
                # Model didn't follow JSON format — render raw response readably
                analysis_md = (
                    "⚠️ _Model did not return structured JSON. Raw response:_\n\n"
                    + event["response"]
                )
            yield (structured_md, calls_md, docs_md, analysis_md)


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="Lease Application Analyzer") as demo:
    gr.Markdown("# 🏢 Lease Application Analyzer\nUpload a lease application PDF. Results appear progressively as each step completes.")

    with gr.Row():
        with gr.Column(scale=1):
            pdf_input = gr.File(label="Upload Lease Application PDF", file_types=[".pdf"])
            analyze_btn = gr.Button("Analyze", variant="primary")

        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.Tab("📋 Extracted Application Data"):
                    structured_out = gr.Markdown(value=INIT[0])

                with gr.Tab("🔍 Agent Tool Calls"):
                    tool_calls_out = gr.Markdown(value=INIT[1])

                with gr.Tab("📚 Retrieved Policy Documents"):
                    retrieved_out = gr.Markdown(value=INIT[2])

                with gr.Tab("⚖️ Analysis Decision"):
                    analysis_out = gr.Markdown(value=INIT[3])

    analyze_btn.click(
        fn=run_pipeline,
        inputs=[pdf_input],
        outputs=[structured_out, tool_calls_out, retrieved_out, analysis_out],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())


# ── helpers ──────────────────────────────────────────────────────────────────

DECISION_BADGE = {
    "APPROVED": "🟢 APPROVED",
    "FLAGGED":  "🟡 FLAGGED",
    "REJECTED": "🔴 REJECTED",
}

def _parse_analysis_json(raw: str) -> dict | None:
    """Strip markdown fences and parse the agent's JSON response."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def _fmt_structured_data(data: dict) -> str:
    lines = []
    lines.append(f"**Applicant:** {data.get('applicant_name', 'N/A')}")
    lines.append(f"**Email:** {data.get('applicant_email', 'N/A')}")
    lines.append(f"**Unit:** {data.get('unit_id', 'N/A')}")

    rent = data.get("monthly_rent", {})
    lines.append(f"**Monthly Rent:** {rent.get('amount', 'N/A')} ({rent.get('written_form', 'N/A')})")

    income = data.get("monthly_income", {})
    confirmed = "✅ confirmed" if income.get("confirmed") else "⚠️ unconfirmed"
    lines.append(f"**Monthly Income:** {income.get('amount', 'N/A')} — {confirmed}")
    if income.get("confirmed_by") and income["confirmed_by"] != "N/A":
        lines.append(f"  Confirmed by: {income['confirmed_by']}")

    if data.get("pet_ownership"):
        pets = data.get("pets", {})
        qty = pets.get("all_pets_quantity", 0)
        lines.append(f"**Pets:** {qty} declared")
        for p in pets.get("all_pets", []):
            lines.append(
                f"  • {p.get('type', 'N/A')} | breed: {p.get('breed', 'N/A')} "
                f"| weight: {p.get('weight', 'N/A')}"
            )
    else:
        lines.append("**Pets:** None declared")

    if data.get("additional_comments") and data["additional_comments"] != "N/A":
        lines.append(f"**Comments:** {data['additional_comments']}")

    return "\n\n".join(lines)


def _fmt_tool_calls(tool_calls: list) -> tuple[str, str]:
    """Return (calls_md, retrieved_docs_md)."""
    if not tool_calls:
        return "_No tool calls recorded._", "_No documents retrieved._"

    calls_lines = []
    docs_lines = []
    for i, tc in enumerate(tool_calls, start=1):
        calls_lines.append(f"**Call {i}** — `{tc['name']}`")
        calls_lines.append(f"> Query: *{tc['query']}*")
        calls_lines.append("")

        docs_lines.append(f"### Call {i} — `{tc['query']}`")
        if tc.get("result"):
            docs_lines.append(tc["result"])
        else:
            docs_lines.append("_No result captured._")
        docs_lines.append("")

    return "\n".join(calls_lines), "\n".join(docs_lines)


def _fmt_analysis(parsed: dict) -> str:
    decision = parsed.get("decision", "UNKNOWN")
    badge = DECISION_BADGE.get(decision, decision)

    check_icon = lambda v: "✅" if v == "PASS" else ("❌" if v == "FAIL" else "⚠️")

    lines = [
        f"## {badge}",
        "",
        f"| Check | Result |",
        f"|---|---|",
        f"| Income-to-Rent Ratio | **{parsed.get('income_to_rent_ratio', 'N/A')}** |",
        f"| Income Check | {check_icon(parsed.get('income_check'))} {parsed.get('income_check', 'N/A')} |",
        f"| Pet Check | {check_icon(parsed.get('pet_check'))} {parsed.get('pet_check', 'N/A')} |",
        f"| Completeness Check | {check_icon(parsed.get('completeness_check'))} {parsed.get('completeness_check', 'N/A')} |",
        "",
    ]

    reasons = parsed.get("reasons", [])
    if reasons:
        lines.append("**Reasons:**")
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")

    notes = parsed.get("notes", "")
    if notes:
        lines.append(f"**Notes:** {notes}")

    return "\n".join(lines)


# ── pipeline wrapper ──────────────────────────────────────────────────────────

def run_pipeline(pdf_file):
    if pdf_file is None:
        return (
            gr.update(value="_Upload a PDF to begin._"),
            gr.update(value="_No tool calls yet._"),
            gr.update(value="_No documents retrieved yet._"),
            gr.update(value="_No analysis yet._"),
        )

    result = process_lease_application(pdf_file)

    if result["status"] != "success":
        msg = f"❌ Error: {result.get('message', 'Unknown error')}"
        return (
            gr.update(value=msg),
            gr.update(value=msg),
            gr.update(value=msg),
            gr.update(value=msg),
        )

    structured_md = _fmt_structured_data(result["data"])

    calls_md, docs_md = _fmt_tool_calls(result.get("tool_calls", []))

    analysis_raw = result["analysis"].get("response", "")
    parsed = _parse_analysis_json(analysis_raw)
    analysis_md = _fmt_analysis(parsed) if parsed else f"```\n{analysis_raw}\n```"

    return (
        gr.update(value=structured_md),
        gr.update(value=calls_md),
        gr.update(value=docs_md),
        gr.update(value=analysis_md),
    )


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="Lease Application Analyzer") as demo:
    gr.Markdown("# 🏢 Lease Application Analyzer\nUpload a lease application PDF and the agent will extract, retrieve policy, and deliver a compliance decision.")

    with gr.Row():
        with gr.Column(scale=1):
            pdf_input = gr.File(label="Upload Lease Application PDF", file_types=[".pdf"])
            analyze_btn = gr.Button("Analyze", variant="primary")

        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.Tab("📋 Extracted Application Data"):
                    structured_out = gr.Markdown(value="_Upload a PDF and click Analyze._")

                with gr.Tab("🔍 Agent Tool Calls"):
                    tool_calls_out = gr.Markdown(value="_No tool calls yet._")

                with gr.Tab("📚 Retrieved Policy Documents"):
                    retrieved_out = gr.Markdown(value="_No documents retrieved yet._")

                with gr.Tab("⚖️ Analysis Decision"):
                    analysis_out = gr.Markdown(value="_No analysis yet._")

    analyze_btn.click(
        fn=run_pipeline,
        inputs=[pdf_input],
        outputs=[structured_out, tool_calls_out, retrieved_out, analysis_out],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())

