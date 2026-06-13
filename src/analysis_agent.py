import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm


from dotenv import load_dotenv

load_dotenv(".env")

LLM_MODEL = os.getenv("LLM_MODEL")  
BASE_URL = os.getenv("BASE_URL")


llm_model = LiteLlm(
    model=f"openai/{LLM_MODEL}",
    api_base=BASE_URL,
)

def get_analysis_agent(tools: list=None) -> dict:
    analysis_agent_instructions_path = "src/prompts/analysis_agent_instruction_prompt.md"

    try:
        with open(analysis_agent_instructions_path, "r") as f:
            analysis_agent_instructions = f.read()


        root_agent = LlmAgent(
            model=llm_model,
            name="lease_application_analysis_agent",
            description="Analyzes lease application information against policy data and provides whether the application meets the criteria.",
            instruction=analysis_agent_instructions,
            tools=tools or [],
        )

        return {"status": "success", "agent": root_agent}

    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {analysis_agent_instructions_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
