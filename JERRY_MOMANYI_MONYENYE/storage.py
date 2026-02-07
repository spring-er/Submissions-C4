import json
import os
import time
import uuid
from typing import Any, Dict, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CHATS_PATH = os.path.join(DATA_DIR, "chats.json")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(path: str, default: Any):
    _ensure_data_dir()
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any):
    _ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings() -> Dict[str, Any]:
    return _read_json(
        SETTINGS_PATH,
        {
            "assistant_name": "Demo Assistant",
            "response_style": "Friendly",
            "history_limit": 31,
            "show_timestamps": True,
        },
    )


def save_settings(settings: Dict[str, Any]) -> None:
    _write_json(SETTINGS_PATH, settings)


def load_chats() -> Dict[str, Any]:
    # format:
    # { "threads": {thread_id: {...}}, "order": [thread_id,...] }
    return _read_json(CHATS_PATH, {"threads": {}, "order": []})


def save_chats(chats: Dict[str, Any]) -> None:
    _write_json(CHATS_PATH, chats)


def new_thread(title: str = "New Chat") -> Dict[str, Any]:
    now = int(time.time())
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],  # each: {role, content, ts}
    }


def add_message(chats: Dict[str, Any], thread_id: str, role: str, content: str, ts: Optional[int] = None):
    if ts is None:
        ts = int(time.time())
    thread = chats["threads"][thread_id]
    thread["messages"].append({"role": role, "content": content, "ts": ts})
    thread["updated_at"] = ts


def delete_thread(chats: Dict[str, Any], thread_id: str):
    if thread_id in chats["threads"]:
        del chats["threads"][thread_id]
    chats["order"] = [t for t in chats["order"] if t != thread_id]

