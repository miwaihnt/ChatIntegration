import os
import base64
from email.mime.text import MIMEText
from typing import List, Dict

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_service() -> 'googleapiclient.discovery.Resource':
    creds_path = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_path:
        raise RuntimeError("GOOGLE_CREDENTIALS env var not set")
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
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

