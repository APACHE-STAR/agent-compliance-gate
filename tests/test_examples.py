"""The examples run as shipped. No network: the LLM example must reject without a key."""
import importlib.util
import pathlib
import runpy

EXAMPLES = pathlib.Path(__file__).parents[1] / "examples"


def test_quickstart_runs(capsys):
    runpy.run_path(str(EXAMPLES / "quickstart.py"))
    out = capsys.readouterr().out
    assert "BAD : REJECTED" in out and "GOOD: APPROVED" in out


def test_llm_example_rejects_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    spec = importlib.util.spec_from_file_location("llm_example", EXAMPLES / "llm_reviewer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    v = mod.gate(mod.draft, mod.policy, reviewers=[mod.reviewer])
    assert v.verdict == "REJECTED"
    assert any("ANTHROPIC_API_KEY not set" in r for r in v.reasons)


def test_readme_quickstart_is_approved(capsys):
    import re
    readme = (EXAMPLES.parent / "README.md").read_text()
    code = re.search(r"```python\n(.*?)```", readme, re.S).group(1)
    exec(compile(code, "README.md", "exec"), {})
    assert capsys.readouterr().out.splitlines()[:2] == ["APPROVED", "[]"]
