# PeoplePolicy AI — Enterprise HR Policy RAG

A Flask-based HR policy assistant using Retrieval-Augmented Generation (RAG), persistent ChromaDB vector storage, local Sentence Transformers embeddings, Groq LLM generation, Docker, and a responsive browser UI.

> **Portfolio/demo project.** Do not upload confidential employee records or deploy with the demo credentials. Before real organizational use, add enterprise SSO, document-level authorization, malware scanning, audit retention, secrets management, monitoring, and security review.

## Features

- Responsive Flask/Jinja chat interface.
- PDF, TXT, and Markdown policy ingestion (PDF extraction uses PyMuPDF).
- Chunking with overlap and semantic embeddings (`all-MiniLM-L6-v2`).
- Persistent ChromaDB collection with source filename and chunk metadata.
- Similarity retrieval and source excerpts shown with every generated answer.
- Groq API for answer generation; app can still test retrieval without an API key.
- Demo employee/admin roles; administrator-only document upload page.
- Upload size limit, extension allowlist, `secure_filename`, environment-based configuration.
- Docker image, Compose persistence volumes, health endpoint, Gunicorn, pytest smoke tests.

## Architecture

```text
Browser
  └── Flask + Jinja + JavaScript
        ├── Session-based demo authentication
        ├── /api/chat ──> RAG service
        │                  ├── Sentence Transformers embeddings
        │                  ├── ChromaDB persistent collection
        │                  └── Groq chat completion
        └── /admin/upload ──> PDF/TXT/MD extraction -> chunks -> embeddings -> ChromaDB
```

## Project structure

```text
hr_policy_rag_enterprise/
├── app.py
├── rag.py
├── requirements.txt
├── Dockerfile
├── compose.yaml
├── .env.example
├── .dockerignore
├── .gitignore
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── index.html
│   └── upload.html
├── static/
│   ├── app.js
│   └── style.css
├── data/
│   └── uploads/
└── tests/
    └── test_rag.py
```

## Requirements

- Python 3.11 recommended.
- Docker Desktop (for container execution).
- Groq API key for LLM answers. Obtain one from the Groq Console; API usage and model availability depend on your account.
- Internet access for the first installation/model download.

## Run locally on Windows (PowerShell)

```powershell
cd hr_policy_rag_enterprise
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a long random `SECRET_KEY`, a valid `GROQ_API_KEY`, and strong demo passwords in `USERS`. Example `USERS` syntax:

```dotenv
USERS=employee:your-strong-password:employee,admin:another-strong-password:admin
```

Avoid commas and colons in these demo passwords because this simple parser uses them as separators. This authentication is intentionally basic for local demonstration only.

Start the app:

```powershell
python app.py
```

Open <http://127.0.0.1:5000>.

### Demo accounts

Only when using the untouched `.env.example` values:

- Employee: `employee` / `ChangeMe123`
- Admin: `admin` / `ChangeMe123`

Change these immediately. Do not use the defaults on a public server.

### First use

1. Sign in as `admin`.
2. Open **Manage policies**.
3. Upload an approved text-based HR policy PDF, TXT, or MD.
4. Return to **Assistant** and ask a question that the policy answers.
5. Expand **Sources used** to inspect the retrieved policy excerpts.

Scanned PDFs may not contain extractable text. OCR is not included in this version; run OCR on approved documents before ingestion if needed.

## Run with Docker Compose

```powershell
Copy-Item .env.example .env
# Edit .env and set SECRET_KEY, GROQ_API_KEY, and strong USERS passwords.
docker compose up --build -d
docker compose logs -f
```

Open <http://localhost:5000>. Stop the app with `docker compose down`. Persistent ChromaDB and uploaded files live in Docker named volumes and remain after stopping containers. `docker compose down -v` deletes those volumes and their data.

The embedding model downloads on first startup and may take a few minutes. The initial image/model download can be large.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing secret | Unsafe demo fallback |
| `GROQ_API_KEY` | Groq API key | Empty |
| `GROQ_MODEL` | Generation model | `llama-3.3-70b-versatile` |
| `EMBEDDING_MODEL` | Sentence Transformers model | `sentence-transformers/all-MiniLM-L6-v2` |
| `CHROMA_PATH` | Persistent ChromaDB path | `./data/chroma` |
| `CHROMA_COLLECTION` | Collection name | `hr_policy_chunks` |
| `MAX_UPLOAD_MB` | Maximum uploaded file size | `15` |
| `COOKIE_SECURE` | Secure cookie flag (HTTPS) | `false` |
| `USERS` | Local demo user definitions | Demo employee/admin |

If using HTTPS, set `COOKIE_SECURE=true`. Use a secrets manager rather than storing production secrets in `.env`.

## API

### `GET /health`

Returns a lightweight health status.

### `POST /api/chat`

Requires login.

```json
{
  "question": "What does the policy say about annual leave?"
}
```

Response:

```json
{
  "answer": "Answer grounded in retrieved policy text ...",
  "sources": [
    {
      "document": "leave_policy.pdf",
      "chunk": 2,
      "distance": 0.31,
      "excerpt": "Relevant source text..."
    }
  ]
}
```

### `GET /api/documents`

Requires login. Returns document names and indexed chunk counts.

## Tests

```powershell
pytest -q
```

The included tests validate text chunking and retrieval behavior without requiring a live Groq call.

## Push to GitHub

Create an empty repository on GitHub, then run:

```powershell
git init
git add .
git status
git commit -m "Build enterprise HR policy RAG assistant"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/hr-policy-rag.git
git push -u origin main
```

Review `git status` before pushing. `.env`, uploaded documents, and ChromaDB data are ignored by Git. Never commit secrets or company policy documents without authorization.

## Deployment notes

- Run the included Docker image with a managed container host or your own server.
- Configure HTTPS at a trusted reverse proxy/platform.
- Store `CHROMA_PATH` and uploaded documents on persistent, access-controlled storage.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Add SSO/OIDC, MFA, CSRF protection for browser form posts, rate limiting, audit events, secrets management, backups, dependency scanning, malware scanning, and document retention controls before organizational use.
- Implement authorization at retrieval time if employees must see different policies. The demo has role-based upload access, but all logged-in users can query the same shared collection.
- Use an isolated, access-controlled Chroma collection or metadata filters for document permissions; do not rely on the LLM to enforce authorization.
- Validate answer quality with a curated test set (retrieval Recall@k, groundedness, citation correctness, abstention rate, latency) before use.
- Policy content may contain prompt injection. The prompt instructs the model to treat retrieved text as untrusted context, but prompt wording alone is not a security boundary.
- Consider using an organization-approved model and embedding service based on privacy, compliance, and retention requirements.

## Troubleshooting

**`GROQ_API_KEY is not configured`**  
Add a valid key to `.env`, restart the app/container, and verify it is not surrounded by literal quote characters.

**Model download fails**  
Check internet access and disk space. For restricted networks, pre-cache the Sentence Transformers model and configure your environment accordingly.

**No policy sources appear**  
Upload a supported file as admin and confirm the extracted PDF contains selectable text. Check logs for extraction or embedding errors.

**Docker health check is initially unhealthy**  
The first model download can take time; inspect `docker compose logs -f` and wait for startup to finish.

**Port 5000 is busy**  
Change the left side of the Compose port mapping, for example `"8080:5000"`, then open <http://localhost:8080>.

## License

Choose a license before publishing this repository. Do not imply affiliation with any real company whose policies you use as sample data.
