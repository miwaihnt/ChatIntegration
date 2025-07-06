import os
from typing import Dict

from notion_client import Client


def get_client() -> Client:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN env var not set")
    return Client(auth=token)


def create_message_page(client: Client, database_id: str, message: Dict):
    props = message["payload"]
    client.pages.create(
        parent={"database_id": database_id},
        properties=props,
    )

