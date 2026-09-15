from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from chat import run_model_tool_loop
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import build_artifact_version

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

VERSION = "v3"
PROVIDER_NAME = "gemini"
MODEL_NAME = "gemini-3.5-flash-lite"

st.set_page_config(
    page_title="Northstar IT Helpdesk AI",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# STYLE
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
      .ns-banner {
          background: linear-gradient(120deg, #4338ca 0%, #6366f1 60%, #0ea5e9 100%);
          padding: 1.1rem 1.5rem;
          border-radius: 14px;
          color: white;
          margin-bottom: 0.9rem;
      }
      .ns-banner h1 { font-size: 1.5rem; margin: 0 0 0.2rem 0; }
      .ns-banner p { margin: 0; opacity: 0.92; font-size: 0.92rem; }

      .status-pill {
          display: inline-block;
          padding: 2px 10px;
          border-radius: 999px;
          font-size: 0.75rem;
          font-weight: 600;
          margin-right: 6px;
      }
      .status-pill.ok  { background: rgba(22,163,74,0.12); color: #16a34a; border: 1px solid rgba(22,163,74,0.35); }
      .status-pill.err { background: rgba(220,38,38,0.12); color: #dc2626; border: 1px solid rgba(220,38,38,0.35); }
      .status-pill.ver { background: rgba(99,102,241,0.12); color: #6366f1; border: 1px solid rgba(99,102,241,0.35); }

      .tool-header { font-size: 0.85rem; font-weight: 600; margin-bottom: 4px; }
      .error-banner {
          background: rgba(220,38,38,0.08);
          border: 1px solid rgba(220,38,38,0.35);
          color: #b91c1c;
          padding: 0.55rem 0.9rem;
          border-radius: 10px;
          font-size: 0.85rem;
          margin: 0.4rem 0 0.6rem 0;
      }
      .sim-note {
          font-size: 0.75rem;
          color: #6b7280;
          margin-top: 0.4rem;
      }
      div[data-testid="stChatInput"] {
          border-top: 1px solid rgba(99,102,241,0.25);
          padding-top: 0.5rem;
      }

      /* Đồng bộ tông màu chính (indigo) với banner, thay vì màu đỏ mặc định của Streamlit */
      .stTabs [data-baseweb="tab-highlight"] { background-color: #4f46e5 !important; }
      .stTabs [aria-selected="true"] { color: #4f46e5 !important; }
      .stButton > button:hover, .stButton > button:focus:not(:active) {
          border-color: #4f46e5 !important;
          color: #4f46e5 !important;
      }
      div[data-testid="stChatInput"] button svg { fill: #4f46e5 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# LOAD ARTIFACTS
# ----------------------------------------------------------------------------
prompt_path = ARTIFACTS_DIR / "system_prompt.md"
tools_path = ARTIFACTS_DIR / "tools.yaml"
system_prompt = prompt_path.read_text(encoding="utf-8")
tool_decls = load_tool_declarations(tools_path)
openai_tools = to_openai_tools(tool_decls)
version_info = build_artifact_version(VERSION, prompt_path, tools_path)


def is_tool_error(result) -> bool:
    return isinstance(result, dict) and "error" in result


def render_tool_event(event: dict, expanded: bool) -> None:
    err = is_tool_error(event.get("result", {}))
    badge = '<span class="status-pill err">❌ LỖI</span>' if err else '<span class="status-pill ok">✅ OK</span>'
    title = f"{'❌' if err else '⚡'} {event['tool']}"
    with st.expander(title, expanded=expanded):
        st.markdown(f"{badge}<span class='status-pill ver'>{VERSION}</span>", unsafe_allow_html=True)
        col_args, col_res = st.columns(2)
        with col_args:
            st.markdown("<div class='tool-header'>📥 Input</div>", unsafe_allow_html=True)
            st.json(event.get("args", {}))
        with col_res:
            st.markdown("<div class='tool-header'>📤 Output</div>", unsafe_allow_html=True)
            st.json(event.get("result", {}))


def save_transcript(label: str) -> Path | None:
    if not st.session_state.get("messages"):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in (label or "session")).strip("_") or "session"
    out_path = TRANSCRIPTS_DIR / f"{ts}_{safe_label}_{VERSION}.json"
    payload = {
        "version": VERSION,
        "provider": PROVIDER_NAME,
        "model": MODEL_NAME,
        "saved_at": ts,
        "label": label,
        "messages": st.session_state.messages,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def process_turn(user_text: str) -> None:
    """Run one full user -> assistant turn and append it to session state."""
    st.session_state.messages.append({"role": "user", "content": user_text, "version": VERSION})

    active_messages = [
        {"role": "system", "content": system_prompt},
        *st.session_state.history,
        {"role": "user", "content": user_text},
    ]

    try:
        with st.spinner("Đang phân tích yêu cầu và điều phối công cụ..."):
            provider = make_provider(PROVIDER_NAME)
            result = run_model_tool_loop(
                provider=provider,
                messages=active_messages,
                tools=openai_tools,
                model=MODEL_NAME,
                max_tool_rounds=4,
            )
    except Exception as exc:  # noqa: BLE001 — không để traceback thô văng ra UI khi demo
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "⚠️ Không hoàn tất được yêu cầu này do lỗi khi gọi provider "
                    f"(`{type(exc).__name__}`). Thử lại hoặc kiểm tra kết nối/API key."
                ),
                "tools": [],
                "version": VERSION,
                "provider_error": str(exc),
            }
        )
        return  # không đẩy lượt lỗi vào `history` để không làm nhiễu ngữ cảnh các lượt sau

    assistant_reply = result.get("assistant_text", "")
    tool_events = result.get("tool_events", [])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_reply,
            "tools": tool_events,
            "version": VERSION,
        }
    )
    st.session_state.history.append({"role": "user", "content": user_text})
    st.session_state.history.append({"role": "assistant", "content": assistant_reply})


# ----------------------------------------------------------------------------
# SESSION STATE
# ----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []
if "last_saved" not in st.session_state:
    st.session_state.last_saved = None

tool_call_count = sum(len(m.get("tools", [])) for m in st.session_state.messages)
tool_error_count = sum(
    1 for m in st.session_state.messages for e in m.get("tools", []) if is_tool_error(e.get("result", {}))
)

# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Hệ thống Trợ lý IT")
    st.markdown("---")

    st.subheader("Trạng thái Runtime")
    st.caption(f"**Version:** `{version_info.version}`")
    st.caption(f"**Artifact hash:** `{version_info.artifact_version}`")
    st.caption(f"**Provider:** `{PROVIDER_NAME}`")
    st.caption(f"**Model:** `{MODEL_NAME}`")

    st.markdown("---")
    st.subheader("🎯 Kịch bản Demo nhanh")
    demo_prompts = [
        ("🔹 Kiểm tra thiết bị (single-turn)", "Kiểm tra riêng kết nối VPN trên LT-204."),
        ("🔹 Làm rõ môi trường (clarify)", "Kiểm tra email ở môi trường demo của team QA."),
        ("🔹 Từ chối ngoài phạm vi (refusal)", "Gợi ý cho mình công thức nấu phở bò."),
        ("🔹 Ranh giới ghi dữ liệu (confirm)", "Tạo ticket mức high cho lỗi VPN trên LT-204 giúp mình."),
    ]
    for label, prompt_text in demo_prompts:
        if st.button(label, use_container_width=True):
            # Không gọi st.rerun() ở đây — script đang chạy trong chính lượt
            # rerun do click nút tạo ra, nên chỉ cần set state rồi để luồng
            # xử lý input ở cuối file xử lý luôn trong cùng lượt này.
            st.session_state.pending_input = prompt_text

    st.markdown("---")
    st.subheader("💾 Lưu transcript minh chứng")
    label_input = st.text_input("Nhãn (vd: case_multiturn_confirm)", key="transcript_label")
    if st.button("Lưu hội thoại hiện tại", use_container_width=True):
        saved_path = save_transcript(label_input)
        if saved_path:
            st.session_state.last_saved = str(saved_path)
            st.success(f"Đã lưu: `{saved_path.name}`")
        else:
            st.warning("Chưa có hội thoại nào để lưu.")

    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.history = []
        st.rerun()

# ----------------------------------------------------------------------------
# HEADER + QUICK STATS
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="ns-banner">
      <h1>🛠️ Northstar Labs — IT Helpdesk Portal</h1>
      <p>Trợ lý AI hỗ trợ chẩn đoán hạ tầng, tra cứu chính sách và điều phối xử lý sự cố.
      Mọi lượt gọi công cụ, tham số và kết quả/lỗi được ghi nhận minh bạch bên dưới.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

turn_count = sum(1 for m in st.session_state.messages if m["role"] == "user")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Lượt hội thoại", turn_count)
c2.metric("Tool call", tool_call_count)
c3.metric("Lỗi tool", tool_error_count)
c4.metric("Version đang chạy", VERSION)

tab_chat, tab_transcripts, tab_info = st.tabs(["💬 Trợ lý", "📁 Transcript", "ℹ️ Công cụ khả dụng"])

# ----------------------------------------------------------------------------
# TAB: CHAT (chỉ hiển thị lịch sử — KHÔNG đặt chat_input ở đây)
# ----------------------------------------------------------------------------
def render_message(msg: dict) -> None:
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg.get("provider_error"):
            st.caption(f"Chi tiết lỗi: `{msg['provider_error']}`")
        if msg.get("tools"):
            if any(is_tool_error(e.get("result", {})) for e in msg["tools"]):
                st.markdown(
                    "<div class='error-banner'>⚠️ Một hoặc nhiều tool trong lượt này trả về lỗi "
                    "thực thi — kiểm tra chi tiết bên dưới trước khi coi câu trả lời là đã hoàn tất.</div>",
                    unsafe_allow_html=True,
                )
            for event in msg["tools"]:
                render_tool_event(event, expanded=False)


with tab_chat:
    if not st.session_state.messages:
        # Chưa có hội thoại: chỉ hiện dòng hướng dẫn, KHÔNG tạo khung cuộn rỗng
        # (khung height=520 rỗng sẽ để lại một khoảng trắng vô nghĩa trước ô nhập).
        st.info("Chưa có hội thoại nào. Gõ yêu cầu ở ô nhập bên dưới hoặc bấm một kịch bản demo ở sidebar.")
    else:
        with st.container(height=520):
            for msg in st.session_state.messages:
                render_message(msg)

# ----------------------------------------------------------------------------
# TAB: TRANSCRIPTS
# ----------------------------------------------------------------------------
with tab_transcripts:
    st.subheader("📁 Transcript đã lưu")
    st.caption(f"Thư mục: `{TRANSCRIPTS_DIR.relative_to(ROOT)}`")

    saved_files = sorted(TRANSCRIPTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not saved_files:
        st.info("Chưa có transcript nào. Dùng nút **Lưu hội thoại hiện tại** ở sidebar sau khi chạy một kịch bản.")
    else:
        for f in saved_files:
            with st.expander(f.name, expanded=(str(f) == st.session_state.last_saved)):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    st.caption(
                        f"Version: `{data.get('version')}` · Nhãn: `{data.get('label') or '—'}` · "
                        f"Số lượt: {len(data.get('messages', []))}"
                    )
                    st.json(data)
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Không đọc được file: {exc}")
                st.download_button(
                    "⬇️ Tải xuống JSON",
                    data=f.read_bytes(),
                    file_name=f.name,
                    mime="application/json",
                    key=f"dl_{f.name}",
                )

# ----------------------------------------------------------------------------
# TAB: TOOL INFO
# ----------------------------------------------------------------------------
with tab_info:
    st.subheader("ℹ️ Công cụ khả dụng cho trợ lý")
    st.caption("Danh sách được nạp trực tiếp từ `artifacts/tools.yaml` đang chạy.")
    if not openai_tools:
        st.info("Không nạp được danh sách tool (kiểm tra `artifacts/tools.yaml`).")
    for tool in openai_tools:
        try:
            fn = tool["function"]
            with st.container(border=True):
                st.markdown(f"**`{fn['name']}`**")
                st.write(fn.get("description", ""))
        except Exception:  # noqa: BLE001
            st.json(tool)

# ----------------------------------------------------------------------------
# INPUT — đặt ở cấp ngoài cùng (không lồng trong tabs/container) để Streamlit
# ghim cố định xuống đáy màn hình, luôn thấy được bất kể đang xem tab nào.
# ----------------------------------------------------------------------------
st.markdown(
    "<p class='sim-note'>💡 Dữ liệu công ty/thiết bị trong demo là dữ liệu giả lập. "
    "Không nhập mật khẩu, OTP hoặc token thật.</p>",
    unsafe_allow_html=True,
)

pending = st.session_state.pop("pending_input", None)
typed = st.chat_input("Nhập yêu cầu cần trợ giúp kỹ thuật...")
user_input = typed or pending

if user_input:
    process_turn(user_input)
    st.rerun()