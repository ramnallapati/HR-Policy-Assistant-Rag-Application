import hmac
import logging
import os
import re
import shutil
from pathlib import Path

import gradio as gr

try:  # local runs: read variables from .env (not needed on Hugging Face Spaces)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from rag import HRPolicyRAG

# Optional: only needed if the Space is created on ZeroGPU hardware (free accounts).
# Harmless no-op on normal CPU hardware. Nothing ever requests a GPU.
try:
    import spaces

    @spaces.GPU
    def _zerogpu_noop():
        return None
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hr-policy-rag")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
POLICY_DIR = BASE_DIR / "policies"  # sample/base policies committed to the repo
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
POLICY_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))


# ---------------------------------------------------------------- users / auth
def configured_users():
    """USERS secret format: username:password:role,username:password:role"""
    raw = os.getenv("USERS", "").strip()
    if not raw:
        raise RuntimeError(
            "USERS is not set. Add a Space secret like "
            "USERS=employee:strong-pass:employee,admin:another-pass:admin"
        )
    users = {}
    for item in raw.split(","):
        parts = item.strip().split(":")
        if len(parts) == 3:
            users[parts[0]] = {"password": parts[1], "role": parts[2]}
    if not users:
        raise RuntimeError("USERS is set but no valid username:password:role entries were found.")
    return users


USERS = configured_users()


def authenticate(username, password):
    user = USERS.get((username or "").strip())
    return bool(user) and hmac.compare_digest(user["password"], password or "")


def role_of(request: gr.Request):
    username = getattr(request, "username", None)
    return USERS.get(username, {}).get("role") if username else None


# ------------------------------------------------------------------------ RAG
rag = HRPolicyRAG()


def seed_policies():
    """Index files in ./policies at startup (the Space disk is wiped on restart)."""
    already = {d["name"] for d in rag.list_documents()}
    for path in sorted(POLICY_DIR.iterdir()):
        if path.suffix.lower() in ALLOWED_EXTENSIONS and path.name not in already:
            try:
                count = rag.ingest_file(path)
                logger.info("Seeded %s (%d chunks)", path.name, count)
            except Exception:
                logger.exception("Could not seed %s", path.name)


seed_policies()


def format_answer(result):
    text = result["answer"]
    sources = result.get("sources") or []
    if sources:
        lines = ["", "---", "**Sources used**"]
        for s in sources:
            excerpt = re.sub(r"\s+", " ", s["excerpt"])
            lines.append(f"- **{s['document']}**, chunk {s['chunk']} (distance {s['distance']})")
            lines.append(f"  > {excerpt}")
        text += "\n" + "\n".join(lines)
    return text


def chat_fn(message, history):
    question = (message or "").strip()
    if not question:
        return "Please enter a question."
    if len(question) > 1500:
        return "Question must be 1,500 characters or fewer."
    try:
        return format_answer(rag.ask(question))
    except Exception:
        logger.exception("RAG query failed")
        return "The assistant could not process that request. Check the Space logs and configuration."


# ---------------------------------------------------------------- admin upload
def doc_rows():
    return [[d["name"], d["chunks"]] for d in rag.list_documents()]


def upload_fn(files, request: gr.Request):
    if role_of(request) != "admin":
        return "Administrator access is required.", doc_rows()
    if not files:
        return "Choose a PDF, TXT, or Markdown file.", doc_rows()
    messages = []
    for f in files:
        src = Path(f if isinstance(f, str) else f.name)
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", src.name)
        if Path(safe_name).suffix.lower() not in ALLOWED_EXTENSIONS:
            messages.append(f"❌ {safe_name}: unsupported file type (allowed: PDF, TXT, MD).")
            continue
        if src.stat().st_size > MAX_UPLOAD_MB * 1024 * 1024:
            messages.append(f"❌ {safe_name}: larger than {MAX_UPLOAD_MB} MB.")
            continue
        dest = UPLOAD_DIR / safe_name
        shutil.copy(src, dest)
        try:
            count = rag.ingest_file(dest)
            messages.append(f"✅ {safe_name}: {count} chunks added or updated.")
        except Exception:
            dest.unlink(missing_ok=True)
            logger.exception("Ingestion failed for %s", safe_name)
            messages.append(f"❌ {safe_name}: could not index. Make sure it contains readable text.")
    return "\n\n".join(messages), doc_rows()


def show_admin_tab(request: gr.Request):
    return gr.Tab(visible=role_of(request) == "admin")


# ------------------------------------------------------------------------- UI
with gr.Blocks(title="PeoplePolicy AI") as demo:
    gr.Markdown(
        "# PeoplePolicy AI\n"
        "HR policy assistant. Answers come only from the indexed policy documents. "
        "This is informational assistance, not an official HR decision."
    )
    with gr.Tab("Assistant"):
        gr.ChatInterface(
            fn=chat_fn,
            chatbot=gr.Chatbot(height=480),
            textbox=gr.Textbox(placeholder="Ask about leave, benefits, conduct…", max_length=1500),
            examples=["What does the policy say about annual leave?"],
        )
    with gr.Tab("Manage policies", visible=False) as admin_tab:
        gr.Markdown(
            "Admins only. Uploads are kept only until the Space restarts. "
            "Put permanent documents in the `policies/` folder of the repo."
        )
        files = gr.File(label="Policy files (PDF, TXT, MD)", file_count="multiple",
                        file_types=[".pdf", ".txt", ".md"])
        upload_btn = gr.Button("Upload and index", variant="primary")
        status = gr.Markdown()
        docs = gr.Dataframe(headers=["Document", "Chunks"], value=doc_rows,
                            interactive=False, label="Indexed documents")
        upload_btn.click(upload_fn, inputs=files, outputs=[status, docs])

    demo.load(show_admin_tab, inputs=None, outputs=admin_tab)

if __name__ == "__main__":
    demo.queue().launch(auth=authenticate, auth_message="Sign in to PeoplePolicy AI",
                        max_file_size=f"{MAX_UPLOAD_MB}mb")