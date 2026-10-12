"""Chapter 04 checks: modules & packages.

Run:   uv run python -m exercises.ch04_modules.main
Solution: exercises/solutions/ch04_modules/
Running this file directly (python .../main.py) fails on purpose. See the chapter.
"""

from . import triage

if __name__ == "__main__":
    assert hasattr(triage, "classify"), "TODO: re-export classify in triage/__init__.py"
    assert triage.__all__ == ["classify"]

    assert triage.classify("I was CHARGED twice, need a refund!") == "billing"
    assert triage.classify("Can't login after password reset") == "auth"
    assert triage.classify("Love the new dashboard") == "other"

    assert __name__ == "__main__"
    assert triage.__name__.endswith("ch04_modules.triage")

    print("All ch 04 exercises passed")
