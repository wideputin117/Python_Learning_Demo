# 23 · Evaluating AI features

## Concept

### Why "it looked fine when I tried it" isn't enough
With normal code, `assert add(2, 2) == 4` passes or fails, forever. With LLM features:
- outputs vary between runs,
- a prompt tweak that fixes one ticket silently breaks three others,
- a model upgrade changes behaviour across the board,
- "looks good" on 5 hand-picked examples says nothing about the 6th category you didn't try.

An **eval** is a test suite for AI behaviour: a fixed dataset of inputs with expected outputs, a script
that runs your *real* pipeline over it, and **metrics** you track over time. Unit tests (with fakes) check
that your *code* is correct. Evals check that your *AI* is good. You need both.

```
data/sample_tickets.json ──► run real triage / RAG ──► compare to expected ──► metrics ──► reports/2026-…json
       (labeled)                 (costs money)                                    │
                                                                       compare with last run
```

### Building the dataset
- **Start small and real:** 40–100 tickets that look like production traffic (typos, rambling, multiple issues, other languages).
- **Cover every class**, including the rare ones (`feature_request`, `other`) and the **confusing
  boundaries** (failed payment: billing or technical?).
- **Label carefully.** If two humans disagree on a label, the model can't be "right" either. Write labeling guidelines (your prompt's category definitions are a good start).
- **Split it:** a **dev** set you look at while tuning prompts, and a **test** set you only run to report
  results. If you tune on the test set, you're grading your own homework.
- Later, real agent corrections (`triage_corrected=True` from M6) become new eval examples for free.

### Classification metrics, by hand
Suppose 10 tickets, looking only at the `billing` class:

```
                 predicted billing   predicted not-billing
actual billing        TP = 4               FN = 1          ← 5 real billing tickets
actual not-billing    FP = 2               TN = 3
```
- **Accuracy** (over *all* classes) = correct / total. It's easy to read, but it hides problems in rare classes.
- **Precision** (billing) = TP / (TP + FP) = 4 / 6 = **0.67**. "When we say billing, how often are we right?"
- **Recall** (billing) = TP / (TP + FN) = 4 / 5 = **0.80**. "Of the real billing tickets, how many did we catch?"
- **F1** = 2·P·R / (P + R) = **0.73**, a single number balancing both.

Which matters more depends on the cost of each mistake: for `priority=urgent`, **recall** matters most
(missing a security incident is worse than a false alarm).

### Confusion matrix
Rows = actual, columns = predicted. The off-diagonal cells tell you *which* mistakes happen:
```
actual \ pred   billing  technical  account  shipping  feature  other
billing            18        3         0        0         0       0
technical           1       15         2        0         0       1
account             0        2        11        0         0       0
...
```
"billing → technical: 3" points straight at your prompt's category definitions for payment errors.

### Confidence calibration
In ch20 we routed low-confidence tickets to review. Check that it's justified: group results by
confidence bucket and compute accuracy per bucket.
```
confidence   n    accuracy
0.9–1.0     52     0.96     ← trust these
0.6–0.9     18     0.78
< 0.6        6     0.50     ← review threshold looks right
```

### Evaluating RAG
RAG has two stages, so evaluate them separately:
1. **Retrieval (cheap, no LLM):** for each ticket with a known relevant KB document, is it in the
   top-k? That's **recall@k** (hit rate). Run this every time you change chunking or k.
2. **Generation (needs judgment):** is the draft *faithful* (only claims supported by the context), *relevant*
   (addresses the ticket), and does it decline correctly when unanswerable?

For generation there's no exact string to compare against. The common approach is **LLM-as-judge**:
a second LLM call grades the draft against a rubric, returning a structured verdict.
Rules for judges:
- Give the judge the **context chunks**, the ticket and the draft, and ask specific yes/no questions,
  not "rate 1–10".
- Ask for a short reason too, so you can spot-check that the judge itself is sane.
- **Validate the judge:** grade ~20 drafts yourself and check agreement. A judge you haven't checked is just another unknown.

### Track cost and latency too
A prompt that's 2% more accurate but 3× slower or 5× pricier may be a bad trade. Every eval report includes:
p50/p95 latency, total input/output tokens and estimated $ cost.

### Evals cost real money
Unlike unit tests, an eval run calls the real API. 100 tickets × Haiku triage is fractions of a cent, and
100 Sonnet drafts + 100 judge calls is roughly $2–3. Have the script **print an estimate and ask for confirmation** (or require `--yes`).

## In Node you'd…
| Node | Python |
|---|---|
| a custom `scripts/eval.ts` with `Promise.all` + `p-limit` | `scripts/eval_triage.py` with `asyncio.gather` + `asyncio.Semaphore` |
| `console.table(results)` | f-string formatted tables (or `rich`, optional) |
| writing JSON with `fs.writeFileSync` | `pathlib.Path(...).write_text(json.dumps(..., indent=2))` |
| `commander`/`yargs` for CLI args | `argparse` (stdlib) |

There's also a whole Python data ecosystem (pandas, scikit-learn's `classification_report`) that makes
this easier. Writing the metrics yourself once (below) is the better exercise. You'll meet those libraries
when you get to fine-tuning (ROADMAP R4, **not implemented**).

## Examples

### 1. Dataset format: `data/sample_tickets.json`
```json
[
  {
    "id": "t001",
    "split": "dev",
    "subject": "Charged twice",
    "body": "Hi, I see two charges of $49 for my March order #A-1043. Please fix!",
    "expected_category": "billing",
    "expected_priority": "high",
    "expected_doc": "refunds.md",
    "answerable": true
  },
  {
    "id": "t002",
    "split": "test",
    "subject": "gift cards?",
    "body": "do u sell gift cards",
    "expected_category": "other",
    "expected_priority": "low",
    "expected_doc": null,
    "answerable": false
  }
]
```

### 2. Metrics without libraries
```python
from collections import Counter

def classification_report(pairs: list[tuple[str, str]], labels: list[str]) -> dict:
    """pairs = [(actual, predicted), ...]"""
    confusion = Counter(pairs)                       # (actual, predicted) -> count
    report = {"accuracy": sum(a == p for a, p in pairs) / len(pairs), "per_class": {}}
    for label in labels:
        tp = confusion[(label, label)]
        fp = sum(n for (a, p), n in confusion.items() if p == label and a != label)
        fn = sum(n for (a, p), n in confusion.items() if a == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        report["per_class"][label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    report["confusion"] = {f"{a}->{p}": n for (a, p), n in confusion.items() if a != p}
    return report
```

### 3. Running many LLM calls concurrently, but politely
```python
import asyncio

async def run_all(items, worker, concurrency: int = 5):
    sem = asyncio.Semaphore(concurrency)              # at most 5 in flight (rate limits!)

    async def guarded(item):
        async with sem:
            return await worker(item)

    return await asyncio.gather(*(guarded(i) for i in items), return_exceptions=True)
```
`return_exceptions=True` means one failed ticket doesn't kill the run. Count failures as their own metric.

### 4. Latency percentiles and cost
```python
import statistics

latencies = sorted(r.usage.latency_ms for r in results)
p50 = statistics.median(latencies)
p95 = latencies[int(0.95 * (len(latencies) - 1))]

PRICES = {  # USD per 1M tokens (input, output). Check the current pricing page before trusting.
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}

def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = PRICES[model]
    return input_tokens * inp / 1e6 + output_tokens * out / 1e6
```

### 5. An LLM-as-judge for drafts
```python
class DraftJudgement(BaseModel):
    faithful: bool = Field(description="Every factual claim in the draft is supported by the context")
    addresses_ticket: bool = Field(description="The draft responds to the customer's actual problem")
    correct_decline: bool = Field(description="If the context lacks the answer, the draft declines instead of inventing")
    reason: str = Field(description="One or two sentences explaining any 'false'")

JUDGE_SYSTEM_PROMPT = """You are a strict reviewer of customer-support reply drafts.
You are given the knowledge-base context the drafter saw, the ticket, and the draft.
Judge only against the context. Outside knowledge does not count as support."""

judgement, usage = await llm.parse(
    system=JUDGE_SYSTEM_PROMPT,
    user=f"<context>\n{context}\n</context>\n<ticket>\n{ticket}\n</ticket>\n<draft>\n{draft}\n</draft>",
    output_format=DraftJudgement,
    model=settings.judge_model,          # claude-sonnet-5-5
    effort="medium",
    server_fallback=True,
)
```

## Gotchas
- **Don't tune on the test split.** Iterate on `dev`, report on `test`.
- **Small datasets are noisy.** On 50 tickets, one ticket = 2 percentage points. Don't celebrate +2%.
- **Run twice before trusting a difference.** LLM outputs vary, and a real improvement survives a rerun.
- **Change one thing at a time** (prompt *or* model *or* k), or you won't know what helped.
- **Accuracy alone lies** when classes are imbalanced. Always read per-class recall and the confusion matrix.
- **Never run evals in the normal test suite.** `pytest` stays fast, free and offline. The eval is a separate script.
- **Save every report** with timestamp, git commit, models and settings, so you can compare runs later.
- **Rate limits:** cap concurrency. The SDK retries 429s, but a semaphore avoids hitting them in the first place.

## Exercises
1. By hand: 8 tickets, actual = `[b, b, t, t, t, a, a, b]`, predicted = `[b, t, t, t, b, a, t, b]`
   (b=billing, t=technical, a=account). Compute accuracy, then precision and recall for `technical`.
2. Write a unit test for `classification_report` using the data from exercise 1.
3. Why is recall more important than precision for `priority=urgent`? Give an example where the reverse is true.
4. Design 5 eval tickets that probe the billing/technical boundary.

<details><summary>Answers</summary>

1. Correct: positions 0, 2, 3, 5, 7 → **accuracy 5/8 = 0.625**. For `technical`: predicted t at 1, 2, 3, 6;
   actual t at 2, 3, 4. TP = 2 (2, 3), FP = 2 (1, 6), FN = 1 (4). **Precision 2/4 = 0.5, recall 2/3 ≈ 0.67.**
2. `assert report["accuracy"] == 0.625`, `assert report["per_class"]["technical"]["precision"] == 0.5`,
   `assert round(report["per_class"]["technical"]["recall"], 2) == 0.67`.
3. A missed urgent ticket (false negative) can mean an unhandled security incident, while a false alarm costs an
   agent a minute. The reverse case is auto-closing tickets as spam: a false positive hides a real customer's
   problem, so precision matters more there.
4. e.g. "card declined with error 'gateway timeout'", "charged but app shows payment failed",
   "can't download my invoice PDF (404)", "promo code not applied at checkout", "subscription renewal email but
   app says expired". Then decide and *document* the correct label for each.
</details>

## Apply to TriageDesk: M8, part 2 (eval script)
**Prerequisites:** M6 (triage), M7 (RAG), and M8 part 1 from chapter 21. `rag.py` and `triage.py` must be callable
without FastAPI (plain functions taking an `LLMClient` / `VectorStore`). If they aren't, refactor first.

**Goal:** one command that tells you, with numbers, how good triage and drafting are, what they cost, and how
fast they are. Then use it to make **one measured improvement**.

**Files to create:**
```
data/sample_tickets.json       # ≥ 40 labeled tickets, dev/test split, every category covered
scripts/eval_triage.py         # the eval CLI
app/ai/evals.py                # pure metric functions (classification_report, percentiles, cost)
app/core/config.py             # + judge_model = "claude-sonnet-5-5"
reports/                       # output folder (add to .gitignore, or commit selected reports)
tests/ai/test_evals.py         # unit tests for the metric functions (no network)
```

**CLI spec:**
```bash
uv run --env-file .env python scripts/eval_triage.py --split dev                 # triage only
uv run --env-file .env python scripts/eval_triage.py --split test --rag --judge  # + retrieval + drafts + judge
uv run --env-file .env python scripts/eval_triage.py --split dev --retrieval-only  # no LLM calls at all
```
- Flags: `--split {dev,test,all}`, `--rag`, `--judge`, `--retrieval-only`, `--concurrency 5`, `--yes`
  (skip the cost-confirmation prompt), `--limit N`.
- Uses the **real** `LLMClient` and a `VectorStore` over the seeded `chroma_data/` (run `seed_kb.py` first).
- Prints an estimated cost before any LLM call and asks `Continue? [y/N]` unless `--yes`.

**Report contents** (printed as tables + saved to `reports/eval-YYYYmmdd-HHMMSS.json`):
- run metadata: timestamp, `git rev-parse --short HEAD`, split, models, `rag_top_k`, `rag_min_score`, chunk size
- **triage:** accuracy, per-class precision/recall/F1 for category; accuracy + **urgent recall** for priority;
  confusion pairs; accuracy by confidence bucket; failure count (fallbacks)
- **retrieval:** recall@k for tickets with `expected_doc`
- **drafts (with `--judge`):** % faithful, % addresses ticket, % correct decline (on `answerable=false` tickets)
- **ops:** p50/p95 latency per stage, total tokens, estimated $ per stage and per ticket

**Acceptance criteria:**
- [ ] `--retrieval-only` runs with no API key set
- [ ] metric functions have unit tests (the exercise 1 numbers), and `uv run pytest` stays offline
- [ ] one failing ticket (simulate with a bad input) is counted, not fatal
- [ ] a report JSON is written and contains everything listed above
- [ ] **the improvement loop:** make one change (prompt wording, few-shot examples, chunk size, k, or
      query-building), rerun on `dev`, keep it only if metrics improve, then report the final `test`
      numbers. Write a 3-line summary of before/after in `CLAUDE.md` under the M8 notes.

**Hints:**
- Reuse `run_all` (semaphore + gather) from the examples.
- Ticket-shaped inputs: the eval doesn't need the DB. Call `triage`/`draft_reply` with plain strings.
  That's why ch20/ch22 asked you to keep those functions FastAPI-free.
- `subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()`
- Keep the judge's `reason` in the report, and read the failures. That's where the next improvement comes from.

<details><summary>Reference sketch (peek only after trying)</summary>

```python
# scripts/eval_triage.py (skeleton)
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.ai.evals import classification_report, cost_usd, percentile
from app.ai.llm import LLMClient
from app.ai.triage import classify_text          # FastAPI-free core of triage_ticket
from app.core.config import get_settings

CATEGORIES = ["billing", "technical", "account", "shipping", "feature_request", "other"]


def load(split: str, limit: int | None) -> list[dict]:
    items = json.loads(Path("data/sample_tickets.json").read_text())
    if split != "all":
        items = [t for t in items if t["split"] == split]
    return items[:limit] if limit else items


async def eval_triage(items: list[dict], llm: LLMClient, concurrency: int) -> dict:
    sem = asyncio.Semaphore(concurrency)

    async def one(t: dict):
        async with sem:
            result, usage = await classify_text(llm, t["subject"], t["body"])
            return t, result, usage

    outcomes = await asyncio.gather(*(one(t) for t in items), return_exceptions=True)
    ok = [o for o in outcomes if not isinstance(o, Exception)]
    pairs = [(t["expected_category"], r.category) for t, r, _ in ok]
    return {
        "failures": len(outcomes) - len(ok),
        "category": classification_report(pairs, CATEGORIES),
        "latency_p50_ms": percentile([u.latency_ms for *_, u in ok], 50),
        "cost_usd": sum(cost_usd(u.model, u.input_tokens, u.output_tokens) for *_, u in ok),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    items = load(args.split, args.limit)
    if not args.yes and input(f"Run triage eval on {len(items)} tickets? [y/N] ").lower() != "y":
        return
    report = {"run_at": datetime.now().isoformat(), "split": args.split,
              "triage_model": get_settings().triage_model,
              "triage": asyncio.run(eval_triage(items, LLMClient(), args.concurrency))}
    out = Path("reports") / f"eval-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["triage"]["category"]["per_class"], indent=2))
    print(f"saved → {out}")


if __name__ == "__main__":
    main()
```
</details>

When M8 is done, the core track is complete 🎉. Flip M8 in `CLAUDE.md`. Next: [chapter 24](24-production-basics.md),
then choose a direction from `docs/ROADMAP.md`.
