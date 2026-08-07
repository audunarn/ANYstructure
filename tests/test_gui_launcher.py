"""The repository GUI launcher must stay usable from an IDE or shell."""

from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_gui_exposes_and_calls_main() -> None:
    script = ROOT / "run_gui.py"
    namespace = runpy.run_path(str(script), run_name="launcher_test")
    source = script.read_text(encoding="utf-8")

    assert callable(namespace["main"])
    assert 'if __name__ == "__main__":\n    main()' in source
