"""Chapter 11 solutions: async Python."""

import asyncio
import time

IN_FLIGHT = {"now": 0, "max": 0}


async def fake_llm(text: str, delay: float = 0.2) -> str:
    """Pretend LLM call: ~0.2s of network wait. Raises if the text contains "error"."""
    IN_FLIGHT["now"] += 1
    IN_FLIGHT["max"] = max(IN_FLIGHT["max"], IN_FLIGHT["now"])
    try:
        await asyncio.sleep(delay)
        if "error" in text:
            raise ConnectionError(f"LLM failed on {text!r}")
        return "billing" if "refund" in text else "general"
    finally:
        IN_FLIGHT["now"] -= 1


async def classify_all(texts: list[str]) -> list[str]:
    return list(await asyncio.gather(*(fake_llm(t) for t in texts)))


async def classify_limited(texts: list[str], limit: int) -> list[str]:
    sem = asyncio.Semaphore(limit)

    async def one(text: str) -> str:
        async with sem:
            return await fake_llm(text)

    return list(await asyncio.gather(*(one(t) for t in texts)))


async def classify_with_timeout(text: str, seconds: float) -> str:
    try:
        async with asyncio.timeout(seconds):
            return await fake_llm(text)
    except TimeoutError:
        return "timeout"


async def safe_classify_all(texts: list[str]) -> list[str]:
    results = await asyncio.gather(*(fake_llm(t) for t in texts), return_exceptions=True)
    return ["failed" if isinstance(r, BaseException) else r for r in results]


async def main() -> None:
    texts = ["refund please", "login broken", "refund again", "app slow", "refund?"]

    start = time.perf_counter()
    results = await classify_all(texts)
    elapsed = time.perf_counter() - start
    assert results == ["billing", "general", "billing", "general", "billing"]
    assert elapsed < 0.5, f"took {elapsed:.2f}s: calls should run concurrently, not one by one"

    IN_FLIGHT["max"] = 0
    start = time.perf_counter()
    results = await classify_limited(texts, limit=2)
    elapsed = time.perf_counter() - start
    assert results == ["billing", "general", "billing", "general", "billing"]
    assert IN_FLIGHT["max"] <= 2, f"max in flight was {IN_FLIGHT['max']}, limit is 2"
    assert elapsed < 0.9, f"took {elapsed:.2f}s: should still run 2 at a time"

    assert await classify_with_timeout("refund", seconds=1) == "billing"
    assert await classify_with_timeout("refund", seconds=0.05) == "timeout"

    results = await safe_classify_all(["refund", "error here", "hello"])
    assert results == ["billing", "failed", "general"]

    print("All ch 11 exercises passed")


if __name__ == "__main__":
    asyncio.run(main())
