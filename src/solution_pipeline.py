from extract_pdf_data import extract_text_from_pdf
from get_structured_output import get_structured_output



def process_lease_application(pdf_path: str) -> dict:
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
    return {"status": "success", "data": structured_data}


if __name__ == "__main__":
    pdf_file = "synthetic_data/mock_inputs/pet_violation.pdf"
    pdf_file = "synthetic_data/mock_inputs/malformed.pdf"
    pdf_file = "synthetic_data/mock_inputs/perfect_app.pdf"
    result = process_lease_application(pdf_file)
    if result["status"] == "success":
        print("Structured Data:")
        print(result["data"])
    else:
        print(f"Error: {result['message']}")