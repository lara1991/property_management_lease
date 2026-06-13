import json
import os
from litellm import completion
import instructor

from src.schemas import LeaseApplication

from dotenv import load_dotenv
load_dotenv(".env")

MODEL_NAME = os.getenv("LLM_MODEL", "gpt-4")
BASE_URL = os.getenv("BASE_URL", "http://localhost:11434/v1")

print(f"Using LLM model: {MODEL_NAME}")
print(f"Using LLM base URL: {BASE_URL}")

client = instructor.from_litellm(completion)


system_prompt = f"""
You are a helpful assistant that extracts structured data from provided user input.
Your output must strictly follow the provided structure, and you must not include any additional text or formatting.
Output must be in JSON format, and it must be valid JSON.
{json.dumps(LeaseApplication.model_json_schema(), indent=2)}"""


def get_structured_output(extracted_text: str) -> dict:
    """
    Get structured output from the LLM for a given input text.

    Args:
        extracted_text: The input text to process.

    Returns:
        A dictionary containing the structured output.
    """

    try:

        response = client.chat.completions.create(
            model=f"openai/{MODEL_NAME}",
            api_base=BASE_URL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": extracted_text
                }
            ],
            response_model=LeaseApplication,
            temperature=0.0,  # Use deterministic output for structured data
        )


        # response = completion(
        #     model=f"openai/{MODEL_NAME}",
        #     api_base=BASE_URL,
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {
        #             "role": "user",
        #             "content": extracted_text
        #         }
        #     ],
        #     response_format=LeaseApplication,
        #     temperature=0.0,  # Use deterministic output for structured data
        # )

        print(f"LLM response: {response}")
        print(type(response))

        structured_data = response.model_dump()
        return {
            "status": "success",
            "message": structured_data,
        }
    except Exception as e:
        print(f"Error parsing structured output: {e}")
        return {"status": "error", "message": str(e)}
