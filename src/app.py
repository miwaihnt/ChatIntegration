import os
import base64
import time
from typing import Dict

import streamlit as st
from dotenv import load_dotenv

from gmail_fetcher import get_service, fetch_unread_messages, mark_as_read
from notion_client_wrapper import get_client, create_message_page
from summarizer import summarize_and_classify

load_dotenv()

CHECK_INTERVAL = 60  # seconds

def process_messages():
    st.write("Checking Gmail for new messages...")
    service = get_service()
    notion = get_client()
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        st.error("NOTION_DATABASE_ID not set")
        return
    messages = fetch_unread_messages(service)
    for msg in messages:
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        sender = headers.get("From", "unknown")
        subject = headers.get("Subject", "(no subject)")
        body_data = msg["payload"]["parts"][0]["body"].get("data", "")
        body = base64.urlsafe_b64decode(body_data + "==").decode("utf-8")
        summary = summarize_and_classify(body)
        page_props = {
            "タイトル": {"title": [{"text": {"content": subject}}]},
            "送信者": {"rich_text": [{"text": {"content": sender}}]},
            "要約": {"rich_text": [{"text": {"content": summary.get("summary", "")}}]},
            "カテゴリ": {"select": {"name": summary.get("category", "その他")}},
            "感情": {"rich_text": [{"text": {"content": summary.get("sentiment", "")}}]},
        }
        create_message_page(notion, database_id, {"payload": page_props})
        mark_as_read(service, msg["id"])
        st.success(f"Stored email from {sender}")


def main():
    st.title("Customer Support Archive Bot")

    # Allow user to upload Gmail API credentials
    uploaded = st.file_uploader("Upload Gmail credentials JSON", type="json")
    if uploaded is not None:
        # Save uploaded credentials temporarily
        cred_path = "temp_credential.json"
        with open(cred_path, "wb") as f:
            f.write(uploaded.getbuffer())
        os.environ["GOOGLE_CREDENTIALS"] = os.path.abspath(cred_path)
        st.success("Credentials uploaded")
    else:
        st.warning("Please upload Gmail credential JSON")

    # Button to process messages, disabled when creds missing
    if st.button("Check now", disabled=uploaded is None):
        if uploaded is None:
            st.error("Upload credentials first")
        else:
            process_messages()

if __name__ == "__main__":
    main()
