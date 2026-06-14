from extract_pdf_data import extract_text_from_pdf
from get_structured_output import get_structured_output
from agent_execution import run_agent
from email_handler import fetch_latest_pdf_attachment



def process_lease_application(pdf_path: str, email_result: dict) -> dict:
    """
    Process a lease application PDF and return structured data.

    Args:
        pdf_path: Path to the lease application PDF file.
    Returns:
        A dictionary containing the structured data extracted from the PDF.
    """
    
    # Step 1: Extract text from the PDF
    extraction_result = extract_text_from_pdf(pdf_path)
    if extraction_result["status"] != "success":
        return {"status": "error", "message": extraction_result["message"]}

    extracted_text = extraction_result["text"]

    # Step 2: Get structured output from the LLM
    structured_output_result = get_structured_output(extracted_text)
    if structured_output_result["status"] != "success":
        return {"status": "error", "message": structured_output_result["message"]}

    structured_data = structured_output_result["message"]

    input_to_agent_processing = {
        "structured_data": structured_data,
        "email_result": email_result,
    }
    analysis_result = run_agent(input_to_agent_processing)
    print("------------------------------------")
    # print(f"Analysis result: {analysis_result}")
    return {
        "status": "success",
        "data": structured_data,
        "analysis": analysis_result,
        "tool_calls": analysis_result.get("tool_calls", []),
    }


if __name__ == "__main__":
    pdf_file = "synthetic_data/mock_inputs/pet_violation.pdf"
    pdf_file = "synthetic_data/mock_inputs/malformed.pdf"
    # pdf_file = "synthetic_data/mock_inputs/perfect_app.pdf"

    # Step 0: Fetch the latest PDF attachment (if no path provided)
    email_result = fetch_latest_pdf_attachment()
    if email_result["status"] != "success":
        print(f"Error: {email_result['message']}")
        exit(1)
    pdf_path = email_result["pdf_path"]

    result = process_lease_application(pdf_path,email_result)
    if result["status"] == "success":
        print("Structured Data:")
        print(result["analysis"])
    else:
        print(f"Error: {result['message']}")