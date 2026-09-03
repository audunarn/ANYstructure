tests package
=============

The test suite is not part of the public runtime API. Run tests from the
repository root with:

.. code-block:: shell

   python -m pytest

This default command runs the fast compatibility suite. The focused suites are
selected explicitly:

.. code-block:: shell

   python -m pytest -m "fem_integration and not slow"
   python -m pytest -m release_authority
   python -m pytest -m slow

The slow tier covers nonlinear, collision, transient, mode-imperfection, and
large external-format qualification and is run manually when those paths
change.
