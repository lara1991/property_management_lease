import base64
import os
import tempfile

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

# We use the Gmail API with read-only and send permissions. Adjust scopes as needed.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")


def authenticate_gmail():
    """
    Authenticate with Gmail API using OAuth2.
    Opens a browser on first run to complete the OAuth flow and saves
    the token locally so subsequent calls are silent.

    Returns:
        An authorised Gmail API service object.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_latest_pdf_attachment(service=None) -> dict:
    """
    Find the most recent unread email that has a PDF attachment,
    download the attachment to a temp file, and return its details.

    The email is marked as processed by being read (the query targets
    unread messages; re-running will skip already-read ones unless the
    token is reset).

    Args:
        service: An authenticated Gmail API service. If None, calls
                 authenticate_gmail() automatically.

    Returns:
        On success:
            {
                "status": "success",
                "pdf_path": "/tmp/...",
                "sender": "someone@example.com",
                "subject": "Lease Application – John Doe",
                "body": "Plain-text email body, or empty string if none.",
            }
        On failure:
            {"status": "error", "message": "<reason>"}
    """
    try:
        if service is None:
            service = authenticate_gmail()

        # Search for unread emails that have attachments
        results = service.users().messages().list(
            userId="me",
            q="is:unread has:attachment filename:pdf",
            maxResults=1,
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return {"status": "error", "message": "No unread emails with PDF attachments found."}

        message_id = messages[0]["id"]
        message = service.users().messages().get(userId="me", id=message_id, format="full").execute()

        headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
        sender = headers.get("From", "Unknown")
        subject = headers.get("Subject", "No Subject")
        body = _extract_body(message["payload"])
        thread_id = message.get("threadId")
        rfc822_msg_id = headers.get("Message-ID")

        # Walk message parts to find the first PDF attachment
        pdf_part = _find_pdf_part(message["payload"])
        if pdf_part is None:
            return {"status": "error", "message": "Email found but no PDF attachment located in message parts."}

        attachment_id = pdf_part["body"]["attachmentId"]
        attachment = service.users().messages().attachments().get(
            userId="me", messageId=message_id, id=attachment_id
        ).execute()

        pdf_data = base64.urlsafe_b64decode(attachment["data"])

        # Write to a named temp file that persists until the caller is done with it
        filename = pdf_part.get("filename", "attachment.pdf")
        suffix = ".pdf" if not filename.endswith(".pdf") else ""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="lease_")
        tmp.write(pdf_data)
        tmp.close()

        return {
            "status": "success",
            "pdf_path": tmp.name,
            "sender": sender,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
            "rfc822_msg_id": rfc822_msg_id,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def _extract_body(payload: dict) -> str:
    """
    Recursively walk the MIME tree and return the plain-text body of the email.
    Prefers text/plain; falls back to text/html if no plain part is found.
    Returns an empty string if no body is found.
    """
    plain, html = _collect_body_parts(payload)
    text = plain or html
    if not text:
        return ""
    try:
        return base64.urlsafe_b64decode(text + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""


def _collect_body_parts(payload: dict) -> tuple[str, str]:
    """Return (plain_data, html_data) from the first matching parts found."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return body_data, ""
    if mime_type == "text/html" and body_data:
        return "", body_data

    plain, html = "", ""
    for part in payload.get("parts", []):
        p, h = _collect_body_parts(part)
        if p and not plain:
            plain = p
        if h and not html:
            html = h
    return plain, html


def _find_pdf_part(payload: dict) -> dict | None:
    """
    Recursively walk the MIME tree of a Gmail message payload and return
    the first part that is a PDF attachment.
    """
    mime_type = payload.get("mimeType", "")
    filename = payload.get("filename", "")

    if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
        if payload.get("body", {}).get("attachmentId"):
            return payload

    for part in payload.get("parts", []):
        result = _find_pdf_part(part)
        if result:
            return result

    return None

from email.mime.text import MIMEText
import base64


def send_reply_email(
    to_address: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
    message_id: str | None = None,
) -> dict:
    """
    Send a new email or reply to an existing email thread.

    If thread_id and message_id are supplied, the email is sent as a reply.
    Otherwise a new email is created.
    """
    try:
        service = authenticate_gmail()

        msg = MIMEText(body)
        msg["To"] = to_address
        msg["Subject"] = subject

        # Reply headers
        if message_id:
            msg["In-Reply-To"] = message_id
            msg["References"] = message_id

        raw_message = base64.urlsafe_b64encode(
            msg.as_bytes()
        ).decode()

        gmail_message = {
            "raw": raw_message
        }

        # Required for proper Gmail threading
        if thread_id:
            gmail_message["threadId"] = thread_id

        sent = (
            service.users()
            .messages()
            .send(userId="me", body=gmail_message)
            .execute()
        )

        return {
            "status": "success",
            "message": "Email sent successfully.",
            "gmail_message_id": sent["id"],
            "thread_id": sent.get("threadId"),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    result = fetch_latest_pdf_attachment()
    if result["status"] == "success":
        print("Email details:")
        print(f"Sender: {result['sender']}")
        print(f"Subject: {result['subject']}")
        print(f"Body: {result['body'][:100]}...")  # Print first 100 chars of body
        print(f"PDF saved to: {result['pdf_path']}")
        print(f"Thread ID: {result['thread_id']}")
        print(f"RFC822 Message ID: {result['rfc822_msg_id']}")
    else:
        print(f"Error: {result['message']}")