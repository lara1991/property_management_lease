import asyncio
import json
import uuid
from typing import AsyncGenerator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from analysis_agent import get_analysis_agent
from vector_db_operations.retriever import retrieve_from_knowledge_base

APP_NAME = "Lease Application Analysis"

session_service = InMemorySessionService()


async def _run_agent_async(input_data: dict, user_id: str, session_id: str) -> dict:
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    agent_result = get_analysis_agent(tools=[retrieve_from_knowledge_base])
    if agent_result["status"] != "success":
        return {"status": "error", "message": agent_result["message"]}

    runner = Runner(
        agent=agent_result["agent"],
        session_service=session_service,
        app_name=APP_NAME,
    )

    message_text = json.dumps(input_data, indent=2)

    tool_calls = []
    final_response = None
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(parts=[Part(text=message_text)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    print(f"[AGENT] tool call  → {part.function_call.name}({part.function_call.args})")
                    tool_calls.append({
                        "name": part.function_call.name,
                        "query": part.function_call.args.get("query", ""),
                        "result": None,
                    })
                elif hasattr(part, "function_response") and part.function_response:
                    print(f"[AGENT] tool result ← {part.function_response.name}")
                    resp = part.function_response.response
                    result_text = resp.get("result", str(resp)) if isinstance(resp, dict) else str(resp)
                    for entry in reversed(tool_calls):
                        if entry["name"] == part.function_response.name and entry["result"] is None:
                            entry["result"] = result_text
                            break
        if event.is_final_response():
            final_response = event.content.parts[0].text

    if final_response is not None:
        return {"status": "success", "response": final_response, "tool_calls": tool_calls}
    return {"status": "error", "message": "No final response received."}


def run_agent(input_data: dict, user_id: str = "default_user", session_id: str = "default_session") -> dict:
    return asyncio.run(_run_agent_async(input_data, user_id, session_id))


async def stream_agent_async(
    input_data: dict,
    user_id: str = "gradio_user",
) -> AsyncGenerator[dict, None]:
    """
    Async generator that streams agent events as they happen.

    Yields dicts with ``type`` in:
    - ``"tool_call"``   — agent requested a tool; includes ``query`` and ``all_calls``
    - ``"tool_result"`` — tool responded;           includes ``all_calls``
    - ``"final"``       — final LLM answer;          includes ``response`` and ``tool_calls``
    - ``"error"``       — something went wrong;      includes ``message``
    """
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    agent_result = get_analysis_agent(tools=[retrieve_from_knowledge_base])
    if agent_result["status"] != "success":
        yield {"type": "error", "message": agent_result["message"]}
        return

    runner = Runner(
        agent=agent_result["agent"],
        session_service=session_service,
        app_name=APP_NAME,
    )

    message_text = json.dumps(input_data, indent=2)
    tool_calls: list[dict] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(parts=[Part(text=message_text)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    entry = {
                        "name": part.function_call.name,
                        "query": part.function_call.args.get("query", ""),
                        "result": None,
                    }
                    tool_calls.append(entry)
                    yield {"type": "tool_call", "query": entry["query"], "all_calls": list(tool_calls)}

                elif hasattr(part, "function_response") and part.function_response:
                    resp = part.function_response.response
                    result_text = resp.get("result", str(resp)) if isinstance(resp, dict) else str(resp)
                    for entry in reversed(tool_calls):
                        if entry["name"] == part.function_response.name and entry["result"] is None:
                            entry["result"] = result_text
                            break
                    yield {"type": "tool_result", "all_calls": list(tool_calls)}

        if event.is_final_response():
            yield {
                "type": "final",
                "response": event.content.parts[0].text,
                "tool_calls": list(tool_calls),
            }



