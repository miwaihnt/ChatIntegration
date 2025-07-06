# Chat Integration Bot

This project provides a Streamlit application to fetch customer messages
from Gmail and store them into a Notion database. Messages are summarized,
classified, and analyzed using OpenAI GPT-4.

Currently, only the Gmail integration is implemented. The application
periodically retrieves recent emails and saves them to a Notion database,
creating a page per customer.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Prepare environment variables in a `.env` file or in your shell:
   - `GOOGLE_CREDENTIALS` – path to your Gmail API credentials JSON file
   - `NOTION_TOKEN` – integration token for Notion API
   - `NOTION_DATABASE_ID` – target Notion database ID
   - `OPENAI_API_KEY` – API key for OpenAI

## Running

```bash
streamlit run src/app.py
```

The app will periodically check Gmail for new messages and push them to
Notion.
