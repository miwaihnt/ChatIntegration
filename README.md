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


-- マッピングテーブルの作成
CREATE OR REPLACE TABLE document_mapping (
    source_filename STRING COMMENT 'RAGが返す元ファイル名',
    target_url STRING COMMENT '対応するConfluenceのURL',
    note STRING COMMENT '備考（バージョンや用途など）'
);

-- 検証用レコードの挿入
INSERT INTO document_mapping (source_filename, target_url, note)
VALUES (
    '2024_0228_データ分析基盤概要書1.6.1版.pdf',
    'http://hdsrv015.hdsrv.gvm-jp.groupis-gn.ntt/confluence/pages/viewpage.action?pageId=79762025&preview=/79762025/251364326/2024_0228_%E3%83%87%E3%83%BC%E3%82%BF%E5%88%86%E6%9E%90%E5%9F%BA%E7%9B%A4%E6%A6%82%E8%A6%81%E6%9B%B81.6.1%E7%89%88.pdf',
    'プレビュー付きリンク'
);


//confuluence用UDF
CREATE OR REPLACE FUNCTION s3_to_confluence_url(
  s3_uris ARRAY,
  mapping_json STRING
)
RETURNS ARRAY
LANGUAGE PYTHON
RUNTIME_VERSION = '3.9'
PACKAGES = ()
HANDLER = 'convert'
AS $$
def convert(s3_uris, mapping_json):
    import json
    import os

    mapping = json.loads(mapping_json)
    result = []
    for uri in s3_uris:
        filename = os.path.basename(uri)
        mapped = mapping.get(filename)
        # ? マッピングがなければ None を返す（リンク生成対象から除外可能に）
        result.append(mapped if mapped else None)
    return result
$$;


import streamlit as st
import json
import time
import uuid
import os
from snowflake.snowpark.context import get_active_session

session = get_active_session()

if "session_id" not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())

def chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []
        with st.chat_message("assistant"):
            first_utterance = "こんにちは。お困りのことがありましたら、何でもお聞かせください。"
            st.markdown(first_utterance)
        st.session_state.messages.append({"role": "assistant", "content": first_utterance})
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("チャットボットへの質問を入力してください。"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("回答を生成中..."):
            session_id = st.session_state['session_id']

            result = session.sql(f"""
                SELECT STREAMLIT_DB.CHATBOT_SCHEMA.CALL_BEDROCK_AGENT_WITH_CITATIONS('{prompt}', '{session_id}') AS result
            """).collect()

            response = ''
            citation_links = []
            debug_logs = []

            if result:
                obj = result[0]['RESULT']
                if isinstance(obj, str):
                    obj = json.loads(obj)

                response = obj.get("replay_text", "")
                citations = obj.get("citations", [])
                debug_logs.append(f"[INFO] Retrieved {len(citations)} citations.")

                s3_uris = []
                if citations:
                    for c in citations:
                        uri = c.get("uri")
                        if uri:
                            s3_uris.append(uri)
                            filename = os.path.basename(uri)
                            debug_logs.append(f"[DEBUG] Citation name: {c.get('name', 'unknown')}")
                            debug_logs.append(f"[DEBUG] S3 URI: {uri}")
                            debug_logs.append(f"[DEBUG] Extracted filename: {filename}")

                if s3_uris:
                    df_mapping = session.table("document_mapping").to_pandas()
                    df_mapping.columns = [c.upper() for c in df_mapping.columns]
                    mapping_dict = dict(zip(df_mapping["SOURCE_FILENAME"], df_mapping["TARGET_URL"]))
                    mapping_json = json.dumps(mapping_dict)

                    debug_logs.append(f"[DEBUG] Mapping Dict Keys: {list(mapping_dict.keys())}")

                    s3_uri_sql_array = ", ".join([f"'{u}'" for u in s3_uris])
                    query = f"""
                        SELECT s3_to_confluence_url(ARRAY_CONSTRUCT({s3_uri_sql_array}), '{mapping_json}') AS urls
                    """
                    mapped_urls_str = session.sql(query).collect()[0]["URLS"]
                    mapped_urls = json.loads(mapped_urls_str)

                    debug_logs.append(f"[DEBUG] mapped_urls = {json.dumps(mapped_urls, ensure_ascii=False)}")

                    seen_links = set()  # 重複リンクの排除用セット

                    for citation, uri, url in zip(citations, s3_uris, mapped_urls):
                        name = citation.get("name", "ドキュメント")

                        if url and url not in seen_links:
                            citation_links.append((name, url))
                            seen_links.add(url)
                            debug_logs.append(f"[MAP] {uri} → {url}")
                        else:
                            reason = "未マッピング" if not url else "重複"
                            debug_logs.append(f"[SKIP] {uri} → {url}（{reason}）")

            if response == f"""Error: 'attribution'""":
                response = "すみません。もう一度内容を変えて質問してください。"

        with st.chat_message("assistant"):
            st.markdown(response)

            if citation_links:
                st.markdown("### ?? 参考にしたドキュメント")
                for name, url in citation_links:
                    st.markdown(
                        f'- ?? <a href="{url}" target="_blank" rel="noopener noreferrer">{name}</a>',
                        unsafe_allow_html=True
                    )

            if debug_logs:
                with st.expander("??? デバッグログを見る"):
                    for log in debug_logs:
                        st.code(log)

def main():
    with st.sidebar:
        st.title("チャットボット")
        st.caption("質問カテゴリを選択し、質問を入力してください。")
        st.markdown('------')

        llm_func = st.radio(
            "質問カテゴリ",
            ["データ分析基盤全体", "データ流通設計審議会", "データカタログの内容"],
            horizontal=True
        )

    if llm_func in ["データ分析基盤全体", "データ流通設計審議会", "データカタログの内容"]:
        chat()

if __name__ == "__main__":
    main()
