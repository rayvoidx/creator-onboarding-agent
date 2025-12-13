import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.rag_eval


def test_rag_eval_script_runs():
    # Just verify the script runs and returns 0 with provided golden set
    root = Path(__file__).resolve().parents[3]
    golden = Path(__file__).resolve().parents[1] / "eval" / "golden.jsonl"
    assert golden.exists()

    # Pass PYTHONPATH so the subprocess can find 'src'
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)

    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "rag_eval.py"),
            "--golden",
            str(golden),
            "--min-score",
            "0.0",
        ],
        capture_output=True,
        env=env,
        cwd=str(root),
    )
    if proc.returncode != 0:
        print("STDOUT:", proc.stdout.decode())
        print("STDERR:", proc.stderr.decode())
    assert proc.returncode == 0
