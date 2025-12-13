import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.rag_eval


def test_rag_eval_script_runs():
    # Just verify the script runs and returns 0 with provided golden set
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    golden = Path(__file__).resolve().parents[1] / "eval" / "golden.jsonl"
    assert golden.exists()
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
    )
    assert proc.returncode == 0
