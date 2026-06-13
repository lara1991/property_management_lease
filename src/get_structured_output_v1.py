import os
from litellm import completion

from src.schemas import LeaseApplication

from dotenv import load_dotenv
load_dotenv(".env")

MODEL_NAME = os.getenv("LLM_MODEL", "gpt-4")
BASE_URL = os.getenv("BASE_URL", "http://localhost:11434/v1")

print(f"Using LLM model: {MODEL_NAME}")
print(f"Using LLM base URL: {BASE_URL}")

def get_structured_output(extracted_text: str) -> dict:
    """
    Get structured output from the LLM for a given input text.

    Args:
        extracted_text: The input text to process.

    Returns:
        A dictionary containing the structured output.
    """

    try:
        response = completion(
            model=f"openai/{MODEL_NAME}",
            api_base=BASE_URL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from provided user input."},
                {
                    "role": "user",
                    "content": extracted_text
                }
            ],
            response_format=LeaseApplication,
            temperature=0.0,  # Use deterministic output for structured data
        )

        print(f"LLM response: {response.choices[0].message.content}")

        structured_data = LeaseApplication.model_validate_json(response.choices[0].message.content).dict()
        return {
            "status": "success",
            "message": structured_data,
        }
    except Exception as e:
        print(f"Error parsing structured output: {e}")
        return {"status": "error", "message": str(e)}
