import asyncio
import json

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from analysis_agent import get_analysis_agent

APP_NAME = "Lease Application Analysis"

session_service = InMemorySessionService()


async def _run_agent_async(input_data: dict, user_id: str, session_id: str) -> dict:
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    agent_result = get_analysis_agent(tools=[])
    if agent_result["status"] != "success":
        return {"status": "error", "message": agent_result["message"]}

    runner = Runner(
        agent=agent_result["agent"],
        session_service=session_service,
        app_name=APP_NAME,
    )

    message_text = json.dumps(input_data, indent=2)

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(parts=[Part(text=message_text)]),
    ):
        if event.is_final_response():
            return {"status": "success", "response": event.content.parts[0].text}

    return {"status": "error", "message": "No final response received."}


def run_agent(input_data: dict, user_id: str = "default_user", session_id: str = "default_session") -> dict:
    return asyncio.run(_run_agent_async(input_data, user_id, session_id))





