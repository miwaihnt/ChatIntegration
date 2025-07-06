import os
from typing import List, Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_service(token: Dict[str, str]) -> "googleapiclient.discovery.Resource":
    """Create Gmail API service using OAuth token dict."""
    creds = Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    service = build("gmail", "v1", credentials=creds)
    return service


def fetch_unread_messages(service, query: str = "is:unread") -> List[Dict]:
    try:
        result = service.users().messages().list(userId="me", q=query).execute()
        messages = result.get("messages", [])
        detailed = []
        for msg in messages:
            m = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            detailed.append(m)
        return detailed
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def mark_as_read(service, message_id: str):
    try:
        service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")

