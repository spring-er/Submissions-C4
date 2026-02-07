import time
import streamlit as st

from storage import (
    load_settings, save_settings,
    load_chats, save_chats,
    new_thread, add_message, delete_thread
)
from llm import openrouter_chat

st.set_page_config(page_title="Streamlit Chatbot", page_icon="🤖", layout="wide")

DEFAULT_MODEL = "openai/gpt-4o-mini"


def fmt_time(ts: int) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def auto_title_from_text(text: str) -> str:
    """Turn the first user message into a short chat title."""
    words = text.strip().split()
    if not words:
        return "New Chat"
    title = " ".join(words[:6])
    return title[:40]


def ensure_session_state(chats: dict, settings: dict):
    """Initialize session-scoped state variables once."""
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()

    if "active_thread_id" not in st.session_state:
        if chats["order"]:
            st.session_state.active_thread_id = chats["order"][0]
        else:
            t = new_thread("New Chat")
            chats["threads"][t["id"]] = t
            chats["order"].insert(0, t["id"])
            save_chats(chats)
            st.session_state.active_thread_id = t["id"]

    if "show_timestamps" not in st.session_state:
        st.session_state.show_timestamps = settings.get("show_timestamps", True)


def build_system_prompt(style: str) -> str:
    if style == "Friendly":
        return "Be friendly, clear, and helpful."
    if style == "Professional":
        return "Be professional, structured, and concise."
    if style == "Direct":
        return "Be direct, no fluff, focus on actions."
    return "Be helpful."


def export_thread_text(thread: dict, assistant_name: str, show_timestamps: bool) -> str:
    lines = []
    lines.append(f"Chat: {thread['title']}")
    lines.append(
        f"Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(thread['created_at']))}"
    )
    lines.append("")

    for m in thread["messages"]:
        who = assistant_name if m["role"] == "assistant" else "You"
        stamp = f"[{fmt_time(m['ts'])}] " if show_timestamps else ""
        lines.append(f"{stamp}{who}: {m['content']}")
        lines.append("")
    return "\n".join(lines)


# Load persistent data
settings = load_settings()
chats = load_chats()

# Init in-memory state
ensure_session_state(chats, settings)

# Get current thread
active_id = st.session_state.active_thread_id
active_thread = chats["threads"][active_id]

# Read API key from Streamlit secrets (NOT sidebar)
api_key = st.secrets.get("OPENROUTER_API_KEY", "")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("Assistant Settings")
    assistant_name = st.text_input("Assistant Name", value=settings.get("assistant_name", "Demo Assistant"))
    response_style = st.selectbox(
        "Response Style",
        ["Friendly", "Professional", "Direct"],
        index=["Friendly", "Professional", "Direct"].index(settings.get("response_style", "Friendly")),
    )
    history_limit = st.slider("Max Chat History", 5, 100, int(settings.get("history_limit", 31)))
    show_timestamps = st.checkbox("Show Timestamps", value=bool(settings.get("show_timestamps", True)))

    st.divider()

    st.subheader("Model")
    model = st.text_input("Model", value=DEFAULT_MODEL)

    if st.button("Save Settings"):
        settings = {
            "assistant_name": assistant_name,
            "response_style": response_style,
            "history_limit": history_limit,
            "show_timestamps": show_timestamps,
        }
        save_settings(settings)
        st.session_state.show_timestamps = show_timestamps
        st.success("Saved!")

    st.divider()

    st.subheader("Chats")
    if st.button("➕ New Chat"):
        t = new_thread("New Chat")
        chats["threads"][t["id"]] = t
        chats["order"].insert(0, t["id"])
        save_chats(chats)
        st.session_state.active_thread_id = t["id"]
        st.rerun()

    # Chat picker (simple & stable)
    thread_ids = chats["order"]
    labels = [chats["threads"][tid]["title"] for tid in thread_ids]
    selected_index = st.selectbox(
        "Select Chat",
        options=list(range(len(thread_ids))),
        index=0,
        format_func=lambda i: labels[i],
    )

    chosen_id = thread_ids[selected_index]
    if chosen_id != st.session_state.active_thread_id:
        st.session_state.active_thread_id = chosen_id
        st.rerun()

    active_id = st.session_state.active_thread_id
    active_thread = chats["threads"][active_id]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Clear Messages"):
            active_thread["messages"] = []
            active_thread["updated_at"] = int(time.time())
            save_chats(chats)
            st.rerun()

    with col2:
        if st.button("🗑️ Delete Chat"):
            delete_thread(chats, active_id)
            if chats["order"]:
                st.session_state.active_thread_id = chats["order"][0]
            else:
                t = new_thread("New Chat")
                chats["threads"][t["id"]] = t
                chats["order"].insert(0, t["id"])
                st.session_state.active_thread_id = t["id"]
            save_chats(chats)
            st.rerun()

    st.divider()

    st.subheader("Session Stats")
    duration = int(time.time() - st.session_state.start_time)
    st.metric("Session Duration", f"{duration//60}m {duration%60}s")
    messages_sent = len([m for m in active_thread["messages"] if m["role"] == "user"])
    st.metric("Messages Sent", messages_sent)
    st.metric("Total Messages", len(active_thread["messages"]))

    st.divider()

    st.subheader("Actions")
    export_text = export_thread_text(active_thread, assistant_name, show_timestamps)
    st.download_button(
        "⬇️ Export Chat (.txt)",
        data=export_text.encode("utf-8"),
        file_name=f"{active_thread['title'].replace(' ', '_')}.txt",
        mime="text/plain",
    )

# ---------------- Main UI ----------------
st.title(f"🤖 {assistant_name}")
st.caption(f"Style: {response_style} | History Limit: {history_limit}")

for msg in active_thread["messages"]:
    with st.chat_message(msg["role"]):
        if show_timestamps:
            st.caption(fmt_time(msg["ts"]))
        st.markdown(msg["content"])

user_input = st.chat_input("Type your message...")
if user_input:
    now = int(time.time())

    # Save user message
    add_message(chats, active_id, "user", user_input, ts=now)

    # Auto-title on the first message of a new chat
    thread = chats["threads"][active_id]
    if thread["title"] == "New Chat" and len(thread["messages"]) == 1:
        thread["title"] = auto_title_from_text(user_input)

    save_chats(chats)

    # Build model messages (system + last N messages)
    sys = {"role": "system", "content": build_system_prompt(response_style)}
    recent = chats["threads"][active_id]["messages"][-history_limit:]
    model_messages = [sys] + [{"role": m["role"], "content": m["content"]} for m in recent]

    with st.chat_message("assistant"):
        try:
            reply = openrouter_chat(
                api_key=api_key,
                messages=model_messages,
                model=model,
                temperature=0.7,
                max_tokens=700,
                site_url="http://localhost:8501",
                app_name="Streamlit Chatbot",
            )
            st.markdown(reply)
            add_message(chats, active_id, "assistant", reply, ts=int(time.time()))
            save_chats(chats)
        except Exception as e:
            st.error(str(e))

    st.rerun()

