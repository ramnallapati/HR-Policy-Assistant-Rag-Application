import os
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from rag import HRPolicyRAG

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "false").lower() == "true"

rag = HRPolicyRAG()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            flash("Administrator access is required.", "error")
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapper

def configured_users():
    # Configure comma-separated username:password:role entries in USERS.
    # Demo defaults are for local development only. Change them before deployment.
    raw = os.getenv("USERS", "employee:ChangeMe123:employee,admin:ChangeMe123:admin")
    users = {}
    for item in raw.split(","):
        parts = item.strip().split(":")
        if len(parts) == 3:
            users[parts[0]] = {"password": parts[1], "role": parts[2]}
    return users

@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "hr-policy-rag"})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = configured_users().get(username)
        if user and password == user["password"]:
            session.clear()
            session["username"] = username
            session["role"] = user["role"]
            return redirect(request.args.get("next") or url_for("index"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/")
@login_required
def index():
    return render_template("index.html", username=session["username"], role=session["role"])

@app.post("/api/chat")
@login_required
def chat():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    if len(question) > 1500:
        return jsonify({"error": "Question must be 1,500 characters or fewer."}), 400
    try:
        result = rag.ask(question)
        return jsonify(result)
    except Exception:
        app.logger.exception("RAG query failed")
        return jsonify({"error": "The assistant could not process that request. Check server configuration and logs."}), 500

@app.get("/api/documents")
@login_required
def documents():
    return jsonify({"documents": rag.list_documents()})

@app.route("/admin/upload", methods=["GET", "POST"])
@admin_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Choose a PDF, TXT, or Markdown file.", "error")
            return redirect(url_for("upload"))
        safe_name = secure_filename(file.filename)
        if not safe_name or not allowed_file(safe_name):
            flash("Unsupported file type. Allowed: PDF, TXT, MD.", "error")
            return redirect(url_for("upload"))
        destination = UPLOAD_DIR / safe_name
        file.save(destination)
        try:
            count = rag.ingest_file(destination)
            flash(f"Indexed {safe_name}: {count} text chunks added or updated.", "success")
        except Exception:
            destination.unlink(missing_ok=True)
            app.logger.exception("Document ingestion failed")
            flash("Could not index the file. Check that it contains readable text and review server logs.", "error")
        return redirect(url_for("upload"))
    return render_template("upload.html", username=session["username"], role=session["role"],
                           documents=rag.list_documents())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
