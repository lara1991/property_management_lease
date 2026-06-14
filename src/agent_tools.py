from google.adk.tools import ToolContext
from vector_db_operations.retriever import retrieve_from_knowledge_base
from email_handler import send_reply_email

def retrieve_from_knowledge_base_tool(query: str, tool_context:ToolContext) -> str:
    """
    Search the Apex Property Management policy knowledge base and return
    relevant policy text for the given query.

    Use targeted queries that mention the specific unit type and policy
    aspect you need, e.g. "income ratio requirement Apt 402" or
    "pet weight limit Townhouse Suite". Call this tool multiple times
    with different queries if you need policy on more than one topic.

    Args:
        query: Natural-language query describing the policy to look up.

    Returns:
        Relevant policy excerpts as plain text, ranked by relevance.
    """
    return retrieve_from_knowledge_base(query)

def reply_email_tool(response: str, tool_context:ToolContext) -> str:
    """
    Send a new email or reply to an existing email thread.

    Args:
        response: The content to include in the email reply.

    Returns:
        A confirmation message that the email was sent.
    """

    email_data = tool_context.state.get("email_data", {})

    to_address = email_data.get("sender")
    subject = f"Re: {email_data.get('subject', '')}"
    thread_id = email_data.get("thread_id")
    rfc822_msg_id = email_data.get("rfc822_msg_id")

    email_send_result =  send_reply_email(
        to_address=to_address,
        subject=subject,
        body=response,
        thread_id=thread_id,
        message_id=rfc822_msg_id
    )

    return email_send_result


def get_all_tools() -> dict:
    """
    Return a dictionary of all available tools for the analysis agent.
    """
    return {
        "analysis_agent_tools": [retrieve_from_knowledge_base_tool, reply_email_tool]
    }
    