import os
import base64
from typing import Dict

import streamlit as st
from dotenv import load_dotenv

from gmail_fetcher import SCOPES, get_service, fetch_unread_messages, mark_as_read
from google_auth_oauthlib.flow import Flow
from notion_client_wrapper import get_client, create_message_page
from summarizer import summarize_and_classify

load_dotenv()

CHECK_INTERVAL = 60  # seconds

def process_messages(token: Dict[str, str]):
    """Fetch unread Gmail messages and push them to Notion."""
    st.write("Checking Gmail for new messages...")
    service = get_service(token)
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

    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    token = st.session_state.get("token")

    params = st.experimental_get_query_params()
    if not token and "code" in params:
        # User returned from OAuth consent screen
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri],
                    }
                },
                scopes=SCOPES,
                state=st.session_state.get("oauth_state"),
            )
            flow.redirect_uri = redirect_uri
            flow.fetch_token(code=params["code"][0])
            creds = flow.credentials
            st.session_state["token"] = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
            }
            st.experimental_set_query_params()  # clear params
            token = st.session_state["token"]
            st.success("Authenticated with Google")
        except Exception as e:
            st.error(f"Authentication failed: {e}")

    if not token:
        if st.button("Googleでログイン"):
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri],
                    }
                },
                scopes=SCOPES,
            )
            flow.redirect_uri = redirect_uri
            auth_url, state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )
            st.session_state["oauth_state"] = state
            st.markdown(
                f'<meta http-equiv="refresh" content="0; url={auth_url}">',
                unsafe_allow_html=True,
            )
            st.stop()
        st.stop()

    # Button to process messages when authenticated
    if st.button("Check now"):
        process_messages(token)

if __name__ == "__main__":
    main()
