import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Create structural foundation paths
MOCK_INPUTS_DIR = "synthetic_data/mock_inputs"
KNOWLEDGE_BASE_DIR = "synthetic_data/knowledge_base"

os.makedirs(MOCK_INPUTS_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

def create_pdf(filename, title, data_fields, additional_text="", header_note=""):
    """Compiles an industrial-style corporate document with realistic formatting noise."""
    filepath = os.path.join(MOCK_INPUTS_DIR, filename)
    
    doc = SimpleDocTemplate(
        filepath, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontSize=18, leading=22,
        textColor=colors.HexColor("#1A365D"), spaceAfter=5
    )
    
    section_style = ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'], fontSize=11, leading=14,
        textColor=colors.HexColor("#2B6CB0"), spaceBefore=10, spaceAfter=5
    )
    
    body_style = ParagraphStyle(
        'FormBody', parent=styles['Normal'], fontSize=9, leading=13,
        textColor=colors.HexColor("#2D3748")
    )
    
    alert_style = ParagraphStyle(
        'AlertBody', parent=styles['Normal'], fontSize=8, leading=11,
        textColor=colors.HexColor("#9B2C2C")
    )

    story = []
    
    # Document Header
    story.append(Paragraph(title, title_style))
    if header_note:
        story.append(Paragraph(f"<i>SYSTEM NOTE: {header_note}</i>", alert_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("APPLICATION DATA FIELDS (RAW EXTRACT)", section_style))
    
    # Grid Presentation
    table_data = []
    for key, val in data_fields.items():
        cell_key = Paragraph(f"<b>{key}:</b>", body_style)
        cell_val = Paragraph(str(val), body_style)
        table_data.append([cell_key, cell_val])
        
    form_table = Table(table_data, colWidths=[150, 300])
    form_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
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
    print(f"🟢 Generated Applicant File: {filepath}")

def create_knowledge_base():
    """Generates the internal corporate policies and criteria rules file."""
    filepath = os.path.join(KNOWLEDGE_BASE_DIR, "building_rules_and_eligibility.md")
    
    markdown_content = """# 🏢 Apex Property Management: Core Compliance & Eligibility Matrix

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
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content.strip())
        
    print(f"📘 Generated Internal Knowledge Base File: {filepath}")

def build_complete_dataset():
    print("🚀 Provisioning Self-Contained System Testing Environment...")
    
    # 1. Generate the Core Knowledge Base Document first
    create_knowledge_base()
    print("-" * 60)

    # 2. Generate PDF 1: Messy but Valid Data (Should Pass Auto-Approve)
    file_1_fields = {
        "Applicant Full Name": "S. Jenkins (Sarah)",
        "Contact Email Address": "sarah.j-91@outlook.co.uk",
        "Requested Unit Code / ID": "Apt #402 (Level 4)",
        "Base Monthly Rent Amount": "$1,500.00 (+ $50 storage locker fee items)",
        "Gross Monthly Income": "4500 USD base salary + approx 1000 USD variable performance bonus",
        "Household Pet Declaration": "Yes, pulling forward 1 cat details",
        "Pet Weight Specifications": "Around ~14-15 lbs max when last checked at the vet"
    }
    file_1_notes = (
        "Hi, I'm moving from out of state for work. My company handles partial relocation reimbursement. "
        "I need a parking pass allocated as well. My cat is friendly and neutered. Let me know if you need "
        "my paystubs forwarded directly via my supervisor."
    )
    create_pdf("perfect_app.pdf", "Lease Application Form - Rev 2024", file_1_fields, file_1_notes, 
               header_note="Scanned Copy - OCR Confidence Variable")

    # 3. Generate PDF 2: The Compliance Breach (Should Fail RAG Pet Policy -> 82 lbs vs 25 lbs limit)
    file_2_fields = {
        "Applicant Full Name": "VANCE, MARCUS E.",
        "Contact Email Address": "marcus.vance.records@corp-net.com",
        "Requested Unit Code / ID": "UNIT 402",
        "Base Monthly Rent Amount": "One Thousand Five Hundred Dollars ($1500)",
        "Gross Monthly Income": "$6,250.00 per month gross (Confirmed by HR)",
        "Household Pet Declaration": "1 Dog (Labrador mix)",
        "Pet Weight Specifications": "82 lbs total mass"
    }
    file_2_notes = (
        "Please note my dog Buster is legally an emotional support animal, though he is large (82 lbs). "
        "He is extremely quiet, very lazy, does not bark, and has lived in high-rise apartments before "
        "without any complaints from neighbors. Income threshold easily clears the 3x standard."
    )
    create_pdf("pet_violation.pdf", "Rental Application Form (Digital Input)", file_2_fields, file_2_notes)

    # 4. Generate PDF 3: The Corrupted Form (Should Trigger Structural Schema Review due to empty fields)
    file_3_fields = {
        "Applicant Full Name": "J. W. [Last name illegible due to smudge]",
        "Contact Email Address": "jw9901_beta@gmail.com",
        "Requested Unit Code / ID": "Studio Room ?? (The one near the elevator)",
        "Base Monthly Rent Amount": "n/a",
        "Gross Monthly Income": "",  # Crucial missing parameter
        "Household Pet Declaration": "None",
        "Pet Weight Specifications": "0"
    }
    file_3_notes = (
        "Sent from my iPhone. Please find attached my application. I forgot my exact proof of income documents "
        "at my old apartment but can email them next week when my account gets unlocked. "
        "Need to move in by next Tuesday if possible."
    )
    create_pdf("malformed.pdf", "Tenant Move-In Ingest Intake Sheet", file_3_fields, file_3_notes,
               header_note="WARNING: Critical Upload Error on Page 1")
    
    print("-" * 60)
    print("✨ Provisioning Complete. Your clean and messy sandboxed test environments are live.")

if __name__ == "__main__":
    build_complete_dataset()