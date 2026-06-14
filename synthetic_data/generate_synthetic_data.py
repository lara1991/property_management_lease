import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Unified structural foundation paths
MOCK_INPUTS_DIR = "synthetic_data/mock_inputs"
KNOWLEDGE_BASE_DIR = "synthetic_data/knowledge_base"

os.makedirs(MOCK_INPUTS_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

def create_pdf(filename, title, data_fields, additional_text="", header_note=""):
    """Compiles an industrial-style corporate document with realistic formatting noise."""
    filepath = os.path.join(MOCK_INPUTS_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1A365D"), spaceAfter=5)
    section_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=11, leading=14, textColor=colors.HexColor("#2B6CB0"), spaceBefore=10, spaceAfter=5)
    body_style = ParagraphStyle('FormBody', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor("#2D3748"))
    alert_style = ParagraphStyle('AlertBody', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor("#9B2C2C"))

    story = [Paragraph(title, title_style)]
    if header_note:
        story.append(Paragraph(f"<i>SYSTEM NOTE: {header_note}</i>", alert_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("APPLICATION DATA FIELDS (RAW EXTRACT)", section_style))
    
    table_data = [[Paragraph(f"<b>{k}:</b>", body_style), Paragraph(str(v), body_style)] for k, v in data_fields.items()]
    form_table = Table(table_data, colWidths=[180, 340])
    form_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
    ]))
    story.append(form_table)
    story.append(Spacer(1, 15))
    
    if additional_text:
        story.append(Paragraph("APPLICANT DECLARED COMMENTS & FOOTNOTES", section_style))
        story.append(Paragraph(additional_text, body_style))
        
    doc.build(story)
    print(f"🟢 Generated Complex Applicant File: {filepath}")

def create_knowledge_base():
    """Generates the comprehensive multi-layered internal corporate rules framework."""
    
    # DOCUMENT 1: Standard Building Rules & Criteria
    filepath_1 = os.path.join(KNOWLEDGE_BASE_DIR, "building_rules_and_eligibility.md")
    markdown_1 = """# 🏢 Apex Property Management: Core Compliance & Eligibility Matrix

This document defines standard underwriting limits, building policies, and criteria parameters for residential processing. All incoming automated pipelines must match fields strictly against these operational bounds.

---

## 🔐 Section 1: Standard Multi-Family Units (Apt 400 - Apt 499)
* **Target Focus Units:** Apt 402, Apt 405, Apt 410
* **Income-to-Rent Ratio:** Primary applicant must demonstrate a verified gross monthly income of at least **3.0x** the stated base rental list price.
* **Pet Policy Constraints:** Domesticated cats and dogs are permitted up to a maximum strict weight limit of **25 lbs** per household animal. Large breeds or exotic pets require written manual exception forms.
* **Occupancy Limit:** Maximum of 2 residents per studio/1-bedroom configuration.

## 🏡 Section 2: Residential Townhouse Clusters (Suite A - Suite Z)
* **Target Focus Units:** Townhouse Suite B, Townhouse Suite F
* **Income-to-Rent Ratio:** Baseline income parameter requires a **2.5x** multiplier relative to base rent pricing.
* **Pet Policy Constraints:** Medium/Large breed animals allowed up to **75 lbs** aggregate mass weight limits due to private yard accessibility. 
* **Occupancy Limit:** Maximum of 4 residents per layout.

## 💎 Section 3: Premium Premium Studios (Studio 100 - Studio 150)
* **Target Focus Units:** Luxury Studio 101, Luxury Studio 102
* **Income-to-Rent Ratio:** High density urban tiers mandate a **3.5x** verified underwriting threshold.
* **Pet Policy Constraints:** **STRICTLY NO PETS ALLOWED.** Any animal detection in extraction traces trips compliance flags automatically.
* **Co-Signer Rules:** Guarantors accepted only if personal credit parameters exceed 720 base indexing metrics.
"""
    with open(filepath_1, "w", encoding="utf-8") as f:
        f.write(markdown_1.strip())
    print(f"📘 Generated Compliance Matrix: {filepath_1}")

    # DOCUMENT 2: Live Inventory & Availability Status Ledger
    filepath_2 = os.path.join(KNOWLEDGE_BASE_DIR, "unit_availability_ledger.md")
    markdown_2 = """# 📊 Apex Property Management: Live Occupancy & Unit Availability Ledger

**Document ID:** AP-OPS-2026-Q2  
**Classification:** Internal Operational Use Only  

This ledger contains the real-time status, unit tiers, monthly base rents, and immediate availability markers for managed properties. Automated intake graphs must cross-reference this registry before confirming any lease approvals.

---

## 🔑 Section 1: Standard Multi-Family Inventory (Apt 400 - Apt 499)

### Unit: Apt 402
* **Unit Type:** 1-Bedroom / 1-Bathroom (Standard Floorplan)
* **Listed Base Rent:** $1,500.00 / month
* **Current Status:** **AVAILABLE**
* **Available Move-in Date:** Immediate
* **Operational Notes:** Freshly painted. Minor storage locker fee ($50.00) applies if selected by the tenant.

### Unit: Apt 405
* **Unit Type:** Studio (Standard)
* **Listed Base Rent:** $1,250.00 / month
* **Current Status:** **OCCUPIED**
* **Available Move-in Date:** Leased through October 2026

---

## 🏡 Section 2: Residential Townhouse Clusters (Suite A - Suite Z)

### Unit: Townhouse Suite B
* **Unit Type:** 3-Bedroom / 2.5-Bathroom (Private Yard)
* **Listed Base Rent:** $2,800.00 / month
* **Current Status:** **AVAILABLE**

---

## 💎 Section 3: Premium Premium Studios (Studio 100 - Studio 150)

### Unit: Luxury Studio 101
* **Unit Type:** Penthouse Studio (Urban Tier)
* **Listed Base Rent:** $2,100.00 / month
* **Current Status:** **UNDER MAINTENANCE**
* **Available Move-in Date:** Delayed until further notice
* **Operational Notes:** Water fixture upgrade in progress following an inspection anomaly. Do not issue automated lease generation.
"""
    with open(filepath_2, "w", encoding="utf-8") as f:
        f.write(markdown_2.strip())
    print(f"📊 Generated Unit Availability Ledger: {filepath_2}")

    # DOCUMENT 3: Underwriting Risk Criteria & Credit Framework
    filepath_3 = os.path.join(KNOWLEDGE_BASE_DIR, "credit_underwriting_protocols.md")
    markdown_3 = """# 🛡️ Apex Property Management: Credit Risk & Background Underwriting Protocols

**Document ID:** AP-FIN-UR-004  
**Classification:** Financial Compliance Guidelines  

This framework defines the financial risk thresholds required to approve an applicant based on credit data.

---

## 📉 Tier 1: Prime Credit Approval Matrix (Score 700+)
* **Eligibility Status:** Automatic Processing Permitted.
* **Security Deposit Requirement:** Equivalent to 1.0 Month of listed base rent.
* **Underwriting Rule:** If credit score is 700 or higher, proceed with standard income-to-rent multipliers.

## 📊 Tier 2: Conditional Credit Acceptance (Score 620 - 699)
* **Eligibility Status:** Conditional Risk Mitigation Required.
* **Security Deposit Requirement:** Increased to 1.5 Months of listed base rent.
* **Underwriting Rule:** Applicants within this window cannot be automatically approved. Flag for human review to assess background stability.

## 🚨 Tier 3: High-Risk / Sub-Prime Thresholds (Score Below 620)
* **Eligibility Status:** Strict Automated Halt / Mandatory Guarantor Node.
* **Underwriting Rule:** Any score beneath 620 requires an individual guarantor.
* **Co-Signer Exception Criteria:** Guarantor files must explicitly show a personal credit tier score exceeding **720** and an income ratio matching at least **5.0x** the target unit's rent.
"""
    with open(filepath_3, "w", encoding="utf-8") as f:
        f.write(markdown_3.strip())
    print(f"🛡️ Generated Credit Underwriting Protocols: {filepath_3}")

def build_complete_dataset():
    print("🚀 Provisioning Highly Complex Sandbox Testing Environment...")
    print("-" * 60)
    
    # 1. Establish RAG Internal Knowledge Matrix
    create_knowledge_base()
    print("-" * 60)

    # 2. FILE 1: Clean Messy Data (Passes Doc 1 Income, Doc 2 Inventory, Doc 3 Credit Tier 1)
    file_1_fields = {
        "Applicant Full Name": "S. Jenkins (Sarah)",
        "Contact Email Address": "sarah.j-91@outlook.co.uk",
        "Requested Unit Code / ID": "Apt #402 (Level 4)",
        "Base Monthly Rent Amount": "$1,500.00 (+ $50 storage locker fee items)",
        "Gross Monthly Income": "4500 USD base salary + approx 1000 USD variable performance bonus, confirmed by HR",
        "Background Credit Score": "740 (Verified via TransUnion pull)",
        "Household Pet Declaration": "Yes, pulling forward 1 cat details",
        "Pet Weight Specifications": "Around ~14-15 lbs max when last checked at the vet"
    }
    file_1_notes = "Moving from out of state for a new software engineering role. Let me know if you need paystubs forwarded directly via my supervisor."
    create_pdf("perfect_app.pdf", "Lease Application Form - Rev 2024", file_1_fields, file_1_notes, "Scanned Copy - OCR Confidence Variable")

    # 3. FILE 2: The Multi-Layer Breach (Fails Doc 1 Pet Weight limit, Flags Doc 3 Credit Tier 2 Conditional Audit)
    file_2_fields = {
        "Applicant Full Name": "VANCE, MARCUS E.",
        "Contact Email Address": "marcus.vance.records@corp-net.com",
        "Requested Unit Code / ID": "UNIT 402",
        "Base Monthly Rent Amount": "One Thousand Five Hundred Dollars ($1500)",
        "Gross Monthly Income": "$6,250.00 per month gross (Confirmed by HR)",
        "Background Credit Score": "Score: 642 (Inquiry flags detected)",
        "Household Pet Declaration": "1 Dog (Labrador mix)",
        "Pet Weight Specifications": "82 lbs total mass"
    }
    file_2_notes = "Buster is an emotional support animal. He is extremely lazy, quiet, and doesn't bark. Income clears comfortably."
    create_pdf("pet_violation.pdf", "Rental Application Form (Digital Input)", file_2_fields, file_2_notes)

    # 4. FILE 3: The Critical Infrastructure Fault (Fails Pydantic Income Schema, Fails Doc 2 Unit Availability Rule)
    file_3_fields = {
        "Applicant Full Name": "J. W. [Last name illegible due to smudge]",
        "Contact Email Address": "jw9901_beta@gmail.com",
        "Requested Unit Code / ID": "Luxury Studio 101 (Penthouse)",
        "Base Monthly Rent Amount": "n/a",
        "Gross Monthly Income": "",  # Induces Missing Data Crash Guard
        "Background Credit Score": "[CRITICAL ERROR: Failed to fetch bureau report]",
        "Household Pet Declaration": "None",
        "Pet Weight Specifications": "0"
    }
    file_3_notes = "Sent from my iPhone. I forgot my exact income documents at my old apartment. Need to move into Studio 101 by next Tuesday if possible."
    create_pdf("malformed.pdf", "Tenant Move-In Ingest Intake Sheet", file_3_fields, file_3_notes, "WARNING: Critical Upload Error on Page 1")
    
    print("-" * 60)
    print("✨ Datasets successfully synchronized. Your complex RAG validation environment is ready.")

if __name__ == "__main__":
    build_complete_dataset()