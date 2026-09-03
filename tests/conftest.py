import gc
import inspect
import os
from pathlib import Path
from uuid import uuid4

import pytest


_RUN_GUI_TESTS = os.environ.get("ANYSTRUCTURE_RUN_GUI_TESTS", "").casefold() in {
    "1",
    "true",
    "yes",
}


def pytest_configure(config):
    if getattr(config.option, "basetemp", None) is None:
        root = Path(__file__).resolve().parents[1]
        config.option.basetemp = str(root / f".pytest_tmp_{uuid4().hex}")


def pytest_collection_modifyitems(items):
    """Keep real Tk sessions out of ordinary compatibility qualification."""

    if _RUN_GUI_TESTS:
        return
    marker = pytest.mark.skip(
        reason="real Tk GUI test is opt-in; set ANYSTRUCTURE_RUN_GUI_TESTS=1"
    )
    for item in items:
        if item.get_closest_marker("gui") is not None:
            item.add_marker(marker)
            continue
        try:
            source = inspect.getsource(item.obj)
        except (OSError, TypeError):
            source = ""
        if any(name.endswith("root") for name in item.fixturenames) or any(
            token in source for token in ("tk.Tk(", "tkinter.Tk(")
        ):
            item.add_marker("gui")
            item.add_marker(marker)


@pytest.fixture(autouse=True)
def _finalize_tk_garbage_on_main_thread(request):
    '''Collect GUI garbage on the main thread after real Tk tests.

    Several GUI tests create Tk roots and canvases; Tcl objects that
    survive in reference cycles crash the interpreter with an access
    violation when the garbage collector later finalizes them on a
    worker thread. The collection hook marks every real Tk test ``gui``,
    so ordinary unit and source-contract tests do not need this relatively
    expensive full collection.
    '''
    yield
    if request.node.get_closest_marker("gui") is not None:
        gc.collect()
