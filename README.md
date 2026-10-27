---
title: PeoplePolicy AI
emoji: 📋
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
---

# PeoplePolicy AI — Enterprise HR Policy RAG

An HR policy assistant using Retrieval-Augmented Generation (RAG), ChromaDB vector storage, local Sentence Transformers embeddings, Groq LLM generation, and a Gradio interface. Deployable for free as a Hugging Face Space.

> **Portfolio/demo project.** Do not upload confidential employee records or deploy with weak credentials. Before real organizational use, add enterprise SSO, document-level authorization, malware scanning, audit retention, secrets management, monitoring, and security review.

## Features

- Gradio chat interface with source excerpts shown under every answer.
- PDF, TXT, and Markdown policy ingestion (PDF extraction uses PyMuPDF).
- Chunking with overlap and semantic embeddings (`all-MiniLM-L6-v2`).
- ChromaDB collection with source filename and chunk metadata.
- Groq API for answer generation; retrieval still works without an API key.
- Employee/admin roles; administrator-only "Manage policies" tab (role checked on the server).
- Upload size limit, extension allowlist, sanitized filenames, environment-based configuration.
- Base policies in `policies/` are indexed automatically at startup.

## Architecture

```text
Browser
  └── Gradio app (app.py)
        ├── Username/password login (USERS secret)
        ├── Assistant tab ──> RAG service (rag.py)
        │                      ├── Sentence Transformers embeddings (CPU)
        │                      ├── ChromaDB collection
        │                      └── Groq chat completion
        └── Manage policies tab (admin) ──> PDF/TXT/MD extraction -> chunks -> embeddings -> ChromaDB
```

## Project structure

```text
hr_policy_rag_enterprise/
├── app.py
├── rag.py
├── requirements.txt
├── README.md
├── .gitignore
├── policies/
│   └── sample_leave_policy.md
├── data/            (created at runtime)
└── tests/
    └── test_rag.py
```

## Deploy to Hugging Face Spaces (free)

1. Create a new Space at huggingface.co/new-space and choose the **Gradio** SDK (if only ZeroGPU is offered on your account, choose that; `app.py` already includes the required no-op).
2. Upload `app.py`, `rag.py`, `requirements.txt`, `README.md`, and the `policies/` folder (or push them with git).
3. In **Settings → Variables and secrets**, add these secrets:
   - `GROQ_API_KEY`: your Groq API key.
   - `USERS`: for example `employee:strong-pass:employee,admin:another-pass:admin`
4. Wait for the build to finish, then open the direct `*.hf.space` URL if login misbehaves in the embedded page.

Notes for free Spaces:

- The disk is **not persistent**. Anything uploaded through the admin tab is lost when the Space restarts. Put permanent documents in `policies/`.
- A free Space's repository is public. Use only sample or non-confidential policies.
- Free Spaces sleep when idle and wake on the next visit.

## Run locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt gradio
$env:GROQ_API_KEY="your-key"
$env:USERS="employee:strong-pass:employee,admin:another-pass:admin"
python app.py
```

Open <http://127.0.0.1:7860>.

Avoid commas and colons in passwords because the simple `USERS` parser uses them as separators.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `GROQ_API_KEY` | Groq API key | Empty |
| `USERS` | `username:password:role` entries, comma-separated (required) | none |
| `GROQ_MODEL` | Generation model | `llama-3.3-70b-versatile` |
| `EMBEDDING_MODEL` | Sentence Transformers model | `sentence-transformers/all-MiniLM-L6-v2` |
| `CHROMA_PATH` | ChromaDB path | `./data/chroma` |
| `CHROMA_COLLECTION` | Collection name | `hr_policy_chunks` |
| `MAX_UPLOAD_MB` | Maximum uploaded file size | `15` |

## Tests

```powershell
pip install pytest
pytest -q
```

The tests validate text chunking and retrieval behavior without requiring a live Groq call.

## Limitations and production notes

- Authentication is basic and for demonstration only; add SSO/OIDC, MFA, rate limiting, and audit logging for real use.
- All logged-in users query the same shared collection. Implement authorization at retrieval time (metadata filters or separate collections) if employees must see different policies; do not rely on the LLM to enforce authorization.
- Policy content may contain prompt injection. The prompt treats retrieved text as untrusted, but prompt wording alone is not a security boundary.
- Scanned PDFs may not contain extractable text. OCR is not included.
- Validate answer quality with a curated test set (retrieval Recall@k, groundedness, citation correctness, abstention rate, latency) before real use.

## Troubleshooting

**`GROQ_API_KEY is not configured`**: add the secret in Space settings and restart the Space; make sure it has no surrounding quote characters.

**Space crashes with `USERS is not set`**: add the `USERS` secret as described above.

**No policy sources appear**: add files to `policies/` or upload as admin, and confirm PDFs contain selectable text. Check the Space logs for errors.

**Login loops in the embedded page**: open the direct `*.hf.space` URL.

## License

Choose a license before publishing this repository. Do not imply affiliation with any real company whose policies you use as sample data.