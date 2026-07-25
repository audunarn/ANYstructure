import gc

import pytest


@pytest.fixture(autouse=True)
def _finalize_tk_garbage_on_main_thread():
    '''Collect garbage on the main thread after every test.

    Several GUI tests create Tk roots and canvases; Tcl objects that
    survive in reference cycles crash the interpreter with an access
    violation when the garbage collector later finalizes them on a
    worker thread (for example the multiprocessing pool result-handler
    thread inside the optimizer tests). Collecting after each test keeps
    Tcl finalization on the main thread.
    '''
    yield
    gc.collect()
