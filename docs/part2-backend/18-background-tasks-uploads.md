# 18 · Background tasks & file uploads

## Concept
Some work shouldn't make the client wait:
- **Indexing a knowledge-base document** (M5): chunk it, embed every chunk, write to the vector DB. This takes seconds or more.
- **AI triage of a new ticket** (M6): an LLM call takes 1–5 s.
- Sending emails, webhooks, cleanups.

The pattern is the same in every framework: **accept the request → save a record with `status="pending"` →
respond immediately (`202 Accepted`) → do the slow work afterwards → update the status**. The
client polls (`GET /kb/documents/{id}`) or gets notified.

FastAPI has **`BackgroundTasks`** built in. You add a function to it during the request, and it runs **in the same
process, after the response is sent**. That's perfect for learning and for small workloads. When you
need retries, persistence across restarts, scheduling or multiple worker machines, you graduate to a
real **task queue** (arq, Celery, RQ, Dramatiq), which is the BullMQ equivalent. See *When to graduate* below.

**File uploads** use `multipart/form-data`. FastAPI's `UploadFile` wraps a spooled temp file
(kept in memory while small and moved to disk when large) with async `read()`, plus `filename`, `content_type` and `size`.
It requires `python-multipart`, which is already included by `fastapi[standard]`.

## In Node you'd…
```js
// Express + multer + "fire and forget" (or BullMQ for real)
const upload = multer({ limits: { fileSize: 1_000_000 } });

app.post("/kb/documents", upload.single("file"), async (req, res) => {
  const doc = await db.kbDocument.create({ data: { filename: req.file.originalname, status: "pending" } });
  setImmediate(() => ingest(doc.id).catch(console.error));     // or: await queue.add("ingest", { id: doc.id })
  res.status(202).json(doc);
});
```
```python
@router.post("/kb/documents", status_code=202, response_model=KBDocumentOut)
async def upload_document(file: UploadFile, background: BackgroundTasks, service: KBServiceDep):
    doc = await service.create_from_upload(file)            # saves with status="pending"
    background.add_task(ingest_document, doc.id)            # runs after the response is sent
    return doc
```

| Node | FastAPI |
|---|---|
| `multer().single("file")` | a `file: UploadFile` parameter |
| `req.file.originalname` / `.mimetype` / `.size` | `file.filename` / `file.content_type` / `file.size` |
| `req.file.buffer` | `await file.read()` (bytes) |
| `req.body.title` (multipart field) | `title: Annotated[str, Form()]` |
| `setImmediate(fn)` / unawaited promise | `background.add_task(fn, *args)` |
| BullMQ + Redis | arq / Celery / RQ + Redis |
| BullMQ retries, delays, cron | the queue library's retry/schedule features (not `BackgroundTasks`) |

## Examples

### 1. A basic upload
```python
from pathlib import Path          # not fastapi.Path: that one is for path parameters
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

ALLOWED_SUFFIXES = {".md", ".txt"}
MAX_BYTES = 1_000_000   # 1 MB


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload(
    file: UploadFile,
    title: Annotated[str | None, Form(max_length=200)] = None,
) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, detail=f"Only {sorted(ALLOWED_SUFFIXES)} files are supported")

    raw = await file.read(MAX_BYTES + 1)          # read at most MAX_BYTES + 1
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, detail="File too large (max 1 MB)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(422, detail="File must be UTF-8 text") from None

    return {"filename": file.filename, "title": title or file.filename, "chars": len(text)}
```
Try it:
```bash
curl -F "file=@data/sample_kb/refunds.md" -F "title=Refund policy" localhost:8000/kb/documents
```
`/docs` renders a file picker for `UploadFile` parameters.

Notes:
- **You can't mix a JSON body with a file in one request.** Other fields must be `Form()` fields.
  For structured metadata, send multiple form fields, or a JSON string in one field.
- `file.filename` comes from the client. **Never use it as a filesystem path** (think `../../etc/passwd`).
  We store contents in the DB, so that's not an issue here. If you write to disk, generate your own name.
- Multiple files: `files: list[UploadFile]`.

### 2. Background tasks
```python
import logging
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

def send_welcome_email(email: str) -> None:        # a sync function is fine (runs in a threadpool)
    logger.info("Sending welcome email to %s", email)

async def notify_webhook(url: str, payload: dict) -> None:   # async works too
    ...

@router.post("/users", status_code=201)
async def create_user(data: UserCreate, background: BackgroundTasks) -> UserOut:
    user = ...
    background.add_task(send_welcome_email, user.email)       # pass the function + its args
    background.add_task(notify_webhook, "https://hooks.example.com", {"id": str(user.id)})
    return user
```
Tasks run **in order, after** the response has been sent, in the same process.

### 3. The pending → done pattern (and why the task needs its own session)
```python
# app/services/kb_ingest.py
import logging
from uuid import UUID

from app.db.session import SessionLocal
from app.models.kb import KBDocument, KBDocumentStatus

logger = logging.getLogger(__name__)


async def ingest_document(document_id: UUID) -> None:
    """Background job: index a KB document. Opens its OWN DB session."""
    async with SessionLocal() as session:
        doc = await session.get(KBDocument, document_id)
        if doc is None:
            logger.warning("KB document %s disappeared before ingest", document_id)
            return
        try:
            # chapter 21 / M5 part 2: chunk doc.content, embed, upsert into Chroma
            doc.chunk_count = 0
            doc.status = KBDocumentStatus.INDEXED
        except Exception as exc:
            logger.exception("Ingest failed for %s", document_id)
            doc.status = KBDocumentStatus.FAILED
            doc.error = str(exc)[:500]
        await session.commit()
```
**Why its own session?** The request's session (from `Depends(get_session)`) has already been closed by the time the
task runs. Pass **IDs, not ORM objects**, to background tasks, and re-load inside the task. The same rule
applies to real queues, where the job payload must be serializable anyway.

**Why catch `Exception` here?** Nobody is waiting for this code. An uncaught error in a background task
is only logged and the document would stay `pending` forever. Record the failure so the API can show it.

### 4. A status enum + model
```python
class KBDocumentStatus(StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"

class KBDocument(Base):
    __tablename__ = "kb_documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)   # sha256: detect duplicates
    status: Mapped[KBDocumentStatus] = mapped_column(
        Enum(KBDocumentStatus, native_enum=False, length=20), default=KBDocumentStatus.PENDING
    )
    chunk_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(500))
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```
```python
import hashlib
content_hash = hashlib.sha256(text.encode()).hexdigest()
```

### 5. Testing uploads and background tasks
```python
def test_upload_markdown(client, agent_headers) -> None:
    resp = client.post(
        "/kb/documents",
        files={"file": ("faq.md", b"# Refunds\nWe refund within 30 days.", "text/markdown")},
        data={"title": "FAQ"},
        headers=agent_headers,
    )
    assert resp.status_code == 202
    doc_id = resp.json()["id"]

    # TestClient runs background tasks before returning, so the job has already finished here
    assert client.get(f"/kb/documents/{doc_id}", headers=agent_headers).json()["status"] == "indexed"
```
`files={"field": (filename, bytes, content_type)}` builds multipart, and `data=` adds form fields.
Because the task uses `SessionLocal` directly (not the overridden `get_session`), tests must make
`SessionLocal` point at the test DB too. One approach is to inject a session factory into the task. Another is to
monkeypatch `app.services.kb_ingest.SessionLocal` in a fixture (chapter 12).

### 6. When to graduate from `BackgroundTasks`
| Need | `BackgroundTasks` | Task queue (arq / Celery + Redis) |
|---|---|---|
| Survives a server restart or crash | ❌ the task is lost | ✅ the job is persisted in Redis |
| Retries with backoff | ❌ hand-rolled | ✅ built in |
| Runs on separate worker machines | ❌ same process as the API | ✅ scale workers independently |
| Heavy CPU work (e.g. local embeddings of 1000s of docs) | ⚠️ competes with API requests | ✅ isolated |
| Scheduling / cron | ❌ | ✅ |
| Setup complexity | none | Redis + a worker process |

**For TriageDesk:** `BackgroundTasks` is fine through M8 (single process, small KB). The
*pending/indexed/failed* status column you build now is exactly what a queue-based design needs, so
migrating later only swaps `background.add_task(f, id)` for `await queue.enqueue_job("f", id)`.
This migration is tracked as **R5** in [ROADMAP.md](../ROADMAP.md) and is **not implemented**.

## Gotchas
- **Background tasks share the server process.** A CPU-heavy task slows every request, and a crash
  or redeploy loses unfinished tasks. Track status in the DB so you can detect stuck `pending` rows.
- **Don't pass the request's session or ORM objects to tasks.** Pass IDs and open a new session.
- **Sync vs async tasks:** a sync `def` task runs in a thread pool (fine for blocking code). An `async def`
  task runs on the event loop, so it **must not block**. The local embedding model in chapter 21 is
  CPU-bound and blocking, so call it in a sync task or via `await asyncio.to_thread(...)`.
- **`await file.read()` with no limit reads the whole upload into memory.** Pass a max size, as in Example 1.
- **`content_type` is client-supplied**, so don't trust it for security. Check the suffix and that the content decodes.
- **422 vs 415 vs 413:** use 415 Unsupported Media Type for a bad file type, 413 Content Too Large for size, and 422 for undecodable content.
- **Forgetting `python-multipart`** gives a startup error about form data. It's included in `fastapi[standard]`.

## Exercises
1. Write `POST /upload-stats` that accepts one `.txt` file and returns its line count, word count and
   the 5 most common words (`collections.Counter`).
2. Add a background task that writes `"<filename> processed"` to the log after the response. Verify
   with `uv run fastapi dev` that the response arrives *before* the log line (add `time.sleep(2)` in a
   **sync** task).
3. Accept up to 3 files at once (`files: list[UploadFile]`) and reject a 4th with 422.
4. What happens if a background task raises an exception? Does the client see it? Try it.
5. Explain in two sentences why a background task should receive `document_id` instead of the `KBDocument` object.

<details><summary>Answers</summary>

1. ```python
   @app.post("/upload-stats")
   async def stats(file: UploadFile) -> dict:
       text = (await file.read()).decode("utf-8")
       words = text.lower().split()
       return {"lines": len(text.splitlines()), "words": len(words),
               "top": Counter(words).most_common(5)}
   ```
2. With a sync task containing `time.sleep(2)`, curl returns immediately and the log line appears 2 s later.
3. Validate in code with `if len(files) > 3: raise HTTPException(422, ...)`.
4. The response was already sent, so the client sees success. The exception is logged by the server. That's why the task must catch errors and record a `failed` status.
5. The ORM object belongs to the request's session, which is closed after the response, so using it later fails or uses stale data. IDs are also serializable, which a real queue requires.
</details>

## Apply to TriageDesk: M5 (part 1: upload + background hook)
M5 is split between this chapter (upload, storage, status, background hook) and
[chapter 21](../part3-ai/21-embeddings-vector-search.md) (chunking, embeddings, Chroma). Build this part first with a
**stub** ingest that marks documents `indexed` with `chunk_count = 0`.

**Goal:** Agents and admins can upload `.md`/`.txt` knowledge-base articles. Each upload is stored with
`status=pending`, the API answers `202` immediately, and a background task processes it and updates the status.

**Packages:** none new.

**Files**
| File | Purpose |
|---|---|
| `app/models/kb.py` | `KBDocumentStatus`, `KBDocument` (see Example 4). Import it in `app/models/__init__.py`. |
| `app/schemas/kb.py` | `KBDocumentOut` (no `content`), `KBDocumentDetail` (with `content`) |
| `app/services/kb_service.py` | `KBService.create_from_upload()`, `list()`, `get()`, `delete()` |
| `app/services/kb_ingest.py` | `ingest_document(document_id)`: the background job (stub now, real in ch 21) |
| `app/api/routes/kb.py` | the endpoints below |
| `app/main.py` (edit) | include the `kb` router |
| `alembic/versions/*_add_kb_documents.py` | migration |
| `data/sample_kb/` | 3–5 small markdown files for a fictional product (refunds, shipping, account, billing, troubleshooting) |
| `tests/test_kb.py` | tests |

**Endpoint spec**
| Method | Path | Who | Request | Response | Codes |
|---|---|---|---|---|---|
| POST | `/kb/documents` | agent, admin | multipart: `file` (.md/.txt, ≤ 1 MB, UTF-8), `title?` form field | `KBDocumentOut` (`status: "pending"`) | 202, 401, 403, 409 duplicate content, 413, 415, 422 |
| GET | `/kb/documents` | agent, admin | `status?`, pagination | `list[KBDocumentOut]` | 200, 401, 403 |
| GET | `/kb/documents/{id}` | agent, admin | — | `KBDocumentDetail` | 200, 401, 403, 404 |
| DELETE | `/kb/documents/{id}` | admin | — | — (in M5 part 2 it also deletes the vectors) | 204, 401, 403, 404 |
| POST | `/kb/documents/{id}/reindex` | admin | — | `KBDocumentOut` (`status: "pending"`) | 202, 401, 403, 404 |

`KBDocumentOut`: `id, title, filename, status, chunk_count, error, created_at`.

**Acceptance criteria**
- [ ] Upload returns 202 with `status: "pending"` **before** the ingest runs (check it by hand with a `sleep` in the stub)
- [ ] After the task runs, the status becomes `indexed` (or `failed` with an `error` message)
- [ ] `.pdf`/`.docx` → 415; > 1 MB → 413; non-UTF-8 → 422; same content uploaded twice → 409
- [ ] Customers get 403 on every `/kb` route
- [ ] The background task opens its own session and receives only the document id
- [ ] A test proves that a task exception leaves the document `failed` (monkeypatch the stub to raise)
- [ ] `scripts/seed_kb.py` uploads every file in `data/sample_kb/` (it can call the service directly, without HTTP)
- [ ] `ruff` + `pytest` green

**Hints**
- Keep validation (suffix, size, decoding) in the route or a small helper. Keep persistence in `KBService`.
- Duplicate check: `select(KBDocument).where(KBDocument.content_hash == h)`.
- For testability, give `ingest_document` an optional `session_factory` parameter defaulting to
  `SessionLocal`. Tests then monkeypatch the default, or the route passes a factory from a dependency.
- `reindex` sets the status back to `pending` and schedules the same task again. Make ingest **idempotent** (safe to run twice).
  That matters in chapter 21, where re-indexing must delete the old vectors first.

<details><summary>Reference sketch (peek only after trying)</summary>

```python
# app/api/routes/kb.py (partial)
@router.post("/documents", status_code=status.HTTP_202_ACCEPTED, response_model=KBDocumentOut)
async def upload_document(
    file: UploadFile,
    background: BackgroundTasks,
    service: KBServiceDep,
    user: AgentUser,
    title: Annotated[str | None, Form(max_length=200)] = None,
) -> KBDocument:
    text = await read_text_upload(file, max_bytes=1_000_000, allowed={".md", ".txt"})  # raises 413/415/422
    doc = await service.create_from_upload(
        filename=file.filename or "untitled", title=title, content=text, uploaded_by=user
    )  # raises ConflictError on duplicate hash
    background.add_task(ingest_document, doc.id)
    return doc
```
```python
# tests/test_kb.py: a failing ingest (partial)
def test_ingest_failure_marks_failed(client, agent_headers, monkeypatch) -> None:
    def boom(_doc) -> int:
        raise RuntimeError("embedding service down")

    monkeypatch.setattr("app.services.kb_ingest.index_document_chunks", boom)  # whatever your stub calls
    resp = client.post("/kb/documents", files={"file": ("a.md", b"# A", "text/markdown")},
                       headers=agent_headers)
    doc = client.get(f"/kb/documents/{resp.json()['id']}", headers=agent_headers).json()
    assert doc["status"] == "failed"
    assert "embedding service down" in doc["error"]
```
</details>
