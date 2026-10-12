# Roadmap: future work (NOT implemented)

> ⚠️ **Everything on this page is a plan, not code.** None of it exists in `app/`. Before treating any
> item as real, check the milestone tracker in `CLAUDE.md`. Once an item is built, move it there and
> delete it from this page. This page exists so future sessions don't "remember" features that
> were never built.

The core track (M0–M8) ends with a working triage + RAG backend. These are the natural next steps,
roughly in the recommended order.

---

## R1. LangChain: the same features, built with a framework
**Why:** After building RAG by hand in M5–M7, you'll understand what LangChain abstracts away
(loaders, splitters, retrievers, prompt templates, output parsers). It's best learned *after* the manual version.
- **Prerequisites:** M7 done, chapters 20–22.
- **Touches:** a new `app/ai/lc/` package that implements the same interface as `app/ai/rag.py`, so the
  two can be compared side by side with the M8 eval script.
- **Packages (expected):** `langchain`, `langchain-anthropic`, `langchain-chroma`.
- **Learning goal:** know when a framework helps and when it hides too much.

## R2. LangGraph agents with tools
**Why:** Turn the triage flow into an agent that can *act*: look up order status, search similar
tickets, escalate to a human, ask the customer a clarifying question.
- **Prerequisites:** R1, comfort with Claude tool use (chapter 20).
- **Touches:** `app/ai/agents/`, new tool functions that wrap existing services, plus a human-in-the-loop
  approval step before any action is sent to a customer.
- **Learning goal:** state machines and graphs, tool calling, guardrails, agent evals.

## R3. Better retrieval
- **Hybrid search:** BM25 keyword + vector search, merged (e.g. reciprocal rank fusion).
- **Reranking:** retrieve top-20, then rerank to top-5.
- **pgvector:** move from SQLite + Chroma to Postgres + pgvector (one DB, real transactions).
- **Prerequisites:** M8 eval script, so every change can be measured.

## R4. Fine-tuning
**Why it fits this project:** every ticket that an agent triages and corrects becomes a **labeled
training example** (ticket text → category/priority). After a few hundred of these, you have a dataset.
- **Path:** (1) export labeled tickets to JSONL → (2) baseline: a classic ML classifier
  (scikit-learn TF-IDF + logistic regression) → (3) fine-tune a small open model
  (e.g. via Hugging Face `transformers` / `peft` LoRA) → (4) compare with Claude on the M8 eval set for
  accuracy, latency and cost.
- **Prerequisites:** M8, plus enough labeled data. Learn the pandas/numpy basics first.
- **Touches:** a new `ml/` folder (training code kept separate from the API), with model loading in
  `app/ai/classifier.py` behind the same interface as the Claude triage.
- **Learning goal:** datasets, train/test splits, overfitting, and when fine-tuning beats prompting (and when it doesn't).

## R5. Production hardening
- Real task queue (arq or Celery + Redis ≈ BullMQ) instead of `BackgroundTasks`
- Docker + docker-compose (API, Postgres, Redis)
- Streaming responses (SSE) for drafting replies
- Observability: structured logs, OpenTelemetry tracing, LLM call tracing / cost dashboards
- Rate limiting, prompt-injection defenses for customer-submitted text

---

### Status log
| Date | Change |
|---|---|
| 2026-10-12 | Roadmap created. Nothing implemented. |
