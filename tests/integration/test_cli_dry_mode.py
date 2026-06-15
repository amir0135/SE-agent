"""CLI dry-mode integration test.

Runs the CLI as a subprocess with an empty SEAGENT_* environment and asserts it produces
a useful answer without any credentials. Network access is not mocked because dry mode
must not attempt any.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _run(args, prompt_env=None):
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("SEAGENT_")
    }
    env["PYTHONPATH"] = str(SRC)
    if prompt_env:
        env.update(prompt_env)
    return subprocess.run(
        [sys.executable, "-m", "se_agent.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )


def test_cli_dry_mode_pipeline():
    proc = _run(["--json", "Open opportunities for Contoso and total pipeline"])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["dry_run"] is True
    assert payload["tool_trace"][0]["tool"] == "msx"
    assert payload["tool_trace"][0]["ok"] is True
    assert "460,000" in payload["answer"]


def test_cli_list_tools_shows_msx_available_in_dry_mode():
    proc = _run(["--list-tools"])
    assert proc.returncode == 0, proc.stderr
    tools = json.loads(proc.stdout)
    by_name = {t["name"]: t for t in tools}
    assert "msx" in by_name
    # In dry mode the CRM is a FakeCrmClient, so msx is available.
    assert by_name["msx"]["available"] is True
