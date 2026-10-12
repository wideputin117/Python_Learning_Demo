# 21 · Embeddings & vector search

## Concept

### The problem with keyword search
A customer writes *"how do I get my money back?"*. Your help article is titled *"Refund policy"*.
`WHERE body LIKE '%money back%'` finds nothing, because the words don't overlap even though the
**meaning** does. You need search by meaning: **semantic search**.

### Embeddings: meaning as a list of numbers
An **embedding model** turns text into a fixed-length list of floats (a **vector**). It's trained so
that texts with similar meaning end up as vectors that point in similar directions.

```
"refund"          → [0.9, 0.1, 0.0]
"money back"      → [0.8, 0.2, 0.1]
"password reset"  → [0.0, 0.1, 0.9]
```
Real models use hundreds of dimensions (the default model we'll use outputs 384), but the idea is the
same with 3. You can picture each vector as an arrow in space: "refund" and "money back" point almost
the same way, and "password reset" points somewhere else.

> An embedding model is **not** the same as Claude. It's a much smaller model that only produces vectors
> and never writes text. Claude doesn't provide embeddings. We use a small free model that runs locally
> on your CPU (bundled with ChromaDB), so there are no API keys and no cost per call.

### Cosine similarity: comparing directions
To compare two vectors we measure the angle between them with **cosine similarity**:

```
              a · b              (dot product)
cos(a, b) = ─────────    =   ─────────────────────────
            |a| × |b|        (length of a) × (length of b)
```
The result is 1.0 for the same direction, ~0 for unrelated, and −1 for opposite.

Worked by hand with the vectors above:
```
a = refund     = [0.9, 0.1, 0.0]     |a| = √(0.81 + 0.01 + 0)    = 0.906
b = money back = [0.8, 0.2, 0.1]     |b| = √(0.64 + 0.04 + 0.01) = 0.831
c = password   = [0.0, 0.1, 0.9]     |c| = √(0 + 0.01 + 0.81)    = 0.906

a·b = 0.9×0.8 + 0.1×0.2 + 0×0.1 = 0.74     cos(a,b) = 0.74 / (0.906×0.831) ≈ 0.98  ✅ very similar
a·c = 0.9×0   + 0.1×0.1 + 0×0.9 = 0.01     cos(a,c) = 0.01 / (0.906×0.906) ≈ 0.01  ❌ unrelated
```
Vector databases often report **distance** instead: `cosine distance = 1 − cosine similarity`, so
**smaller distance = more similar**.

### Vector search
1. **Index time:** embed every document (or chunk) once, store `(id, vector, text, metadata)`.
2. **Query time:** embed the question, find the *k* stored vectors closest to it ("top-k nearest
   neighbours"), and return their texts.

```
             index time                                   query time
KB article ──► chunk ──► embed ──► [vector DB]  ◄── embed ◄── "how do I get my money back?"
                                        │
                                        └──► top-k chunks: "Refund policy: …", "Returns: …"
```
Comparing against every vector is fine for thousands of items. Vector DBs use approximate indexes
(HNSW) to stay fast at millions.

### Chunking: why we split documents
You don't embed a 10-page document as one vector, for two reasons:
- **Precision:** one vector for 10 pages is a blurry average of 20 topics, so it matches nothing well.
- **Context cost:** later (ch22) we paste retrieved text into the prompt. You want the 3 relevant
  paragraphs, not 10 pages.

Common strategies:

| Strategy | How | Good for |
|---|---|---|
| Fixed size | every N characters, with overlap | anything, simple baseline |
| **Structure-aware** | split on markdown headings, then by size | **help-center docs (our case)** |
| Sentence / paragraph | split on blank lines / sentences | prose |

**Overlap** (e.g. the last 100 characters repeated at the start of the next chunk) stops an answer that
straddles a boundary from being cut in half. Typical starting point: **~800–1,200 characters per chunk, ~100–150 overlap**,
then tune using the eval in chapter 23.

Always store **metadata** with each chunk (document id, title, heading, chunk index). You'll need it
for citations (ch22), filtering, and deleting old chunks when a document changes.

### ChromaDB
**ChromaDB** is a vector database you can run **embedded** in your Python process (like SQLite: no
server), persisting to a folder. It embeds text for you with a default local model
(`all-MiniLM-L6-v2`, 384 dimensions; downloaded ~80 MB on first use).

| Chroma concept | Rough SQL equivalent |
|---|---|
| client (`PersistentClient(path=...)`) | DB connection |
| collection | table |
| `upsert(ids, documents, metadatas)` | INSERT … ON CONFLICT UPDATE |
| `query(query_texts, n_results, where)` | `SELECT … ORDER BY similarity LIMIT k` |
| `delete(where={...})` | DELETE … WHERE |

## In Node you'd…
| Node | Python |
|---|---|
| `chromadb` JS client talking to a Chroma **server** | `chromadb` embedded in-process (no server needed) |
| OpenAI/Voyage embeddings via HTTP | local default embedding function (or any custom one) |
| `pgvector` via Prisma raw SQL | same option exists in Python (see ROADMAP R3, not implemented) |
| `await collection.query(...)` | `collection.query(...)` is **synchronous**. Run it in a thread from async code |

## Examples
Install when you start this milestone:
```bash
uv add chromadb
```

### 1. Cosine similarity in pure Python (do it once by hand)
```python
import math

def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

print(round(cosine([0.9, 0.1, 0.0], [0.8, 0.2, 0.1]), 2))  # 0.98
```

### 2. Chroma basics
```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_data")      # persisted to disk
kb = client.get_or_create_collection(
    "kb_chunks",                                  # name: 3+ chars, [a-zA-Z0-9._-]
    configuration={"hnsw": {"space": "cosine"}},  # use cosine distance (the default is L2)
)

kb.upsert(
    ids=["7:0", "7:1"],                           # stable ids: f"{document_id}:{chunk_index}"
    documents=[
        "Refund policy: you can request a refund within 30 days of purchase...",
        "Refunds are paid back to the original payment method within 5-7 business days...",
    ],
    metadatas=[
        {"document_id": 7, "title": "Refunds", "heading": "Policy", "chunk_index": 0},
        {"document_id": 7, "title": "Refunds", "heading": "Timing", "chunk_index": 1},
    ],
)

results = kb.query(query_texts=["how do I get my money back?"], n_results=3)
# Results are lists-of-lists: one inner list PER QUERY TEXT.
for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    print(f"{1 - dist:.2f}  {meta['title']} / {meta['heading']}: {doc[:60]}")
```

### 3. Metadata filters
```python
kb.query(query_texts=["refund"], n_results=5, where={"document_id": 7})
kb.query(query_texts=["refund"], n_results=5, where={"$and": [{"category": "billing"}, {"chunk_index": {"$lt": 3}}]})
kb.delete(where={"document_id": 7})   # remove all chunks of a document before re-indexing it
```

### 4. A structure-aware chunker (pure Python, so easy to test)
```python
from dataclasses import dataclass

@dataclass
class Chunk:
    text: str
    heading: str
    index: int

def chunk_markdown(text: str, max_chars: int = 1000, overlap: int = 120) -> list[Chunk]:
    sections: list[tuple[str, str]] = []     # (heading, body)
    heading, lines = "", []
    for line in text.splitlines():
        if line.startswith("#"):
            if lines:
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line.lstrip("# ").strip(), []
        else:
            lines.append(line)
    if lines:
        sections.append((heading, "\n".join(lines).strip()))

    chunks: list[Chunk] = []
    for heading, body in sections:
        start = 0
        while start < len(body):
            piece = body[start : start + max_chars]
            if piece.strip():
                # Prefix the heading: it gives the embedding (and later the LLM) context.
                chunks.append(Chunk(text=f"{heading}\n{piece}".strip(), heading=heading, index=len(chunks)))
            start += max_chars - overlap
    return chunks
```

### 5. Calling sync libraries from async code
Chroma's client is synchronous, and embedding takes CPU time. Inside an `async def`, a direct call
**blocks the event loop** (chapter 11), so every other request waits. Two fixes:
```python
import asyncio

hits = await asyncio.to_thread(kb.query, query_texts=[q], n_results=5)   # run in a worker thread
```
Or write the function as a plain `def`. FastAPI runs sync routes, dependencies **and background tasks**
in a threadpool automatically.

### 6. A fake embedding function for tests
The real model downloads ~80 MB and is slow-ish. Tests should use a tiny deterministic fake,
injected the same way as the fake LLM:
```python
import hashlib
from chromadb import Documents, EmbeddingFunction, Embeddings

class FakeEmbedding(EmbeddingFunction[Documents]):
    """Bag-of-words hashed into 32 buckets: deterministic, instant, good enough for tests."""
    def __init__(self) -> None: ...
    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for text in input:
            v = [0.0] * 32
            for word in text.lower().split():
                v[int(hashlib.md5(word.encode()).hexdigest(), 16) % 32] += 1.0
            vectors.append(v)
        return vectors
    @staticmethod
    def name() -> str:
        return "fake"

test_client = chromadb.EphemeralClient()                     # in-memory, gone after the test
col = test_client.get_or_create_collection("kb_chunks", embedding_function=FakeEmbedding())
```

## Gotchas
- **Same embedding model at index and query time.** Vectors from different models live in different
  "spaces" and comparing them is meaningless. If you change the model, re-index everything.
- **Distance vs similarity.** Chroma returns *distances*. Smaller is closer. Don't sort descending.
- **Set the space to cosine at creation.** The default is L2. The configuration can't be changed later
  without recreating the collection.
- **Results are nested lists** (`results["documents"][0]`), one list per query text.
- **Metadata values must be scalars** (str/int/float/bool). Put lists into a comma-joined string.
- **Semantic search is bad at exact identifiers.** "Order #A-1234" or error code "E1043" are better
  matched by keyword search. Combining both ("hybrid search") is ROADMAP R3 (not implemented).
- **Keep IDs stable and deterministic** (`f"{doc_id}:{i}"`), so re-indexing overwrites instead of duplicating.
- **`chroma_data/` is local state.** It's already in `.gitignore`. Rebuild it with `scripts/seed_kb.py`.
- **Two sources of truth.** The SQL `kb_documents` row is the truth and Chroma is a derived index. If they
  drift, re-index from SQL. Never the other way around.

## Exercises
1. Compute by hand `cos([1, 0], [0, 1])` and `cos([1, 1], [2, 2])`. What do the results tell you about length vs direction?
2. Embed these with Chroma's default model and query "I can't log in": *"Reset your password from the
   login page"*, *"We ship to 40 countries"*, *"Two-factor authentication codes expire after 30 seconds"*.
   Print similarities. Is the ranking what you expected?
3. Write tests for `chunk_markdown`: (a) every chunk ≤ `max_chars` + heading length, (b) headings are
   preserved, (c) consecutive chunks of a long section overlap.
4. Why might a chunk size of 100 characters retrieve *worse* answers than 1,000, even though it's "more precise"?

<details><summary>Answers</summary>

1. `0` (perpendicular = unrelated) and `1.0`. `[2, 2]` is just a longer `[1, 1]`. Cosine ignores
   length and only compares direction. That's why it's the standard choice for text embeddings.
2. Typically password reset ranks first, 2FA second, shipping last. Login problems relate to
   authentication. Exact numbers depend on the model.
3. e.g. `assert all(len(c.text) <= 1000 + len(c.heading) + 1 for c in chunks)`. For overlap, check that
   the last 120 characters of chunk *i*'s body appear at the start of chunk *i+1*'s body.
4. Tiny chunks lose context. "within 30 days" without "refund policy" around it is ambiguous, both for
   the embedding and for the LLM reading it later. Chunk size is a trade-off you **measure** (ch23).
</details>

## Apply to TriageDesk

### M5, part 2: index the knowledge base into Chroma
**Prerequisites:** chapter 18's M5 part 1. KB documents are uploaded, stored in SQL (e.g. a
`kb_documents` table with `id`, `title`, `filename`, `content`, `status`), and an ingestion background
task exists as a stub. Now you fill in that stub. (Adapt the names below to what you built in ch18.)

**Install:** `uv add chromadb`

**Files to create / change:**
```
app/ai/chunking.py         # Chunk dataclass + chunk_markdown()
app/ai/vector_store.py     # VectorStore class + get_vector_store() dependency
app/services/kb_service.py # ingestion: chunk → upsert → status=indexed (fills the ch18 hook)
app/core/config.py         # + chroma_path: str = "./chroma_data", chunk_size, chunk_overlap
data/sample_kb/*.md        # 6–10 realistic help articles (refunds, shipping, password reset, 2FA, invoices, account deletion, …)
scripts/seed_kb.py         # load data/sample_kb into SQL + Chroma
tests/ai/test_chunking.py
tests/ai/test_vector_store.py
```

**Spec:**
- `VectorStore.__init__(self, client: chromadb.ClientAPI, embedding_function=None)` creates/gets two
  collections with cosine space: `kb_chunks` and `tickets`. Injecting the client lets tests pass
  `EphemeralClient()` + `FakeEmbedding()`.
- Methods (synchronous, so call them via `asyncio.to_thread` from async code or use them in sync background tasks):
  - `index_document(document_id: int, title: str, content: str) -> int` deletes old chunks for the
    document, chunks, upserts, and returns the chunk count
  - `delete_document(document_id: int) -> None`
  - `search_kb(query: str, k: int = 5) -> list[KBHit]` where `KBHit` is a Pydantic model:
    `chunk_id, document_id, title, heading, text, score` (score = `1 - distance`)
- Ingestion task: set `status="indexing"`, call `index_document`, then `status="indexed"` +
  `chunk_count`. On any exception, `status="failed"` + `error` message, and log it.
- `DELETE /kb/{id}` also removes the document's chunks from Chroma.
- New endpoint `GET /kb/search?q=...&k=5` (agent/admin). Useful for debugging retrieval *before* ch22 adds the LLM.

**Acceptance criteria:**
- [ ] `uv run python scripts/seed_kb.py` indexes all sample docs and prints chunk counts
- [ ] `GET /kb/search?q=how do I get my money back` returns the refunds article first
- [ ] re-uploading/re-indexing a document doesn't duplicate chunks (`collection.count()` unchanged)
- [ ] deleting a document removes its chunks
- [ ] chunker unit tests pass (size, headings, overlap)
- [ ] vector store tests use `EphemeralClient` + `FakeEmbedding` and need no download or network
- [ ] a failing ingestion leaves `status="failed"` with an error, and the API keeps working

**Hints:**
- `get_vector_store()` uses `@lru_cache` like `get_settings()`. Override it in tests with
  `app.dependency_overrides`.
- Upsert in batches (e.g. 100 chunks per call) for big documents.
- Start with the search endpoint and eyeball results for 10 realistic questions. If retrieval is bad,
  no prompt in ch22 will save you.

<details><summary>Reference sketch (peek only after trying)</summary>

```python
# app/ai/vector_store.py (partial)
import chromadb
from pydantic import BaseModel

from app.ai.chunking import chunk_markdown

COSINE = {"hnsw": {"space": "cosine"}}


class KBHit(BaseModel):
    chunk_id: str
    document_id: int
    title: str
    heading: str
    text: str
    score: float


class VectorStore:
    def __init__(self, client: chromadb.ClientAPI, embedding_function=None) -> None:
        kwargs = {"configuration": COSINE}
        if embedding_function is not None:
            kwargs["embedding_function"] = embedding_function
        self.kb = client.get_or_create_collection("kb_chunks", **kwargs)
        self.tickets = client.get_or_create_collection("tickets", **kwargs)

    def index_document(self, document_id: int, title: str, content: str) -> int:
        self.kb.delete(where={"document_id": document_id})
        chunks = chunk_markdown(content)
        if not chunks:
            return 0
        self.kb.upsert(
            ids=[f"{document_id}:{c.index}" for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[
                {"document_id": document_id, "title": title, "heading": c.heading, "chunk_index": c.index}
                for c in chunks
            ],
        )
        return len(chunks)

    def search_kb(self, query: str, k: int = 5) -> list[KBHit]:
        res = self.kb.query(query_texts=[query], n_results=k)
        return [
            KBHit(chunk_id=cid, document_id=m["document_id"], title=m["title"],
                  heading=m["heading"], text=doc, score=1 - dist)
            for cid, doc, m, dist in zip(
                res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
            )
        ]
```
</details>

### M8, part 1: similar-ticket search
**Goal:** when an agent opens a ticket, show the 5 most similar past tickets (and how they were
categorized). This helps with consistency, and spotting duplicates and incidents ("20 tickets about checkout
errors in the last hour").

**Spec:**
- `VectorStore.add_ticket(ticket_id: int, text: str, metadata: dict) -> None` stores `subject + body`
  in the `tickets` collection with metadata `ticket_id`, `category`, `status`, `created_at` (ISO string).
- Call it at the end of `triage_ticket` (so `category` is known). Update the metadata (upsert) when an agent corrects labels.
- `GET /tickets/{id}/similar?k=5` (agent/admin) returns `[{ticket_id, subject, category, score}]`, **excluding the ticket itself**
  (ask for `k + 1` and filter).
- Optional: `?category=billing` maps to a `where` filter.

**Acceptance criteria:**
- [ ] two near-duplicate tickets ("charged twice for March" / "double charge on my March invoice") find each other first
- [ ] the ticket itself is never in its own results
- [ ] tests use the fake embedding function

Chapter 23 adds M8 part 2, the eval script. Next: [chapter 22, RAG](22-rag.md).
