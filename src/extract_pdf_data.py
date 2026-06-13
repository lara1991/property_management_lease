from markitdown import MarkItDown

md = MarkItDown()
def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
    Returns:
        Extracted text as a string.
    """

    try:
        extracted_text = md.convert(pdf_path)
        return {
            "status": "success",
            "text": extracted_text.text_content,
            "metadata": {
                "source": pdf_path,
            },
        }
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return {"status": "error", "message": str(e), "metadata": {"source": pdf_path}}


if __name__ == "__main__":
    pdf_file = "synthetic_data/mock_inputs/pet_violation.pdf"
    result = extract_text_from_pdf(pdf_file)
    if result["status"] == "success":
        print("Extracted Text:")
        print(result["text"])
    else:
        print(f"Error: {result['message']}")