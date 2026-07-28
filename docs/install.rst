Installation
************

Install from PyPI
=================

.. code-block:: shell

   pip install anystructure

The finite-element GUI requires ``ANYsolver>=0.1.3,<0.2``. A normal PyPI
install resolves that dependency automatically.

For coordinated local development, install the solver sibling before the
ANYstructure checkout:

.. code-block:: powershell

   python -m pip install -e C:\Github\ANYsolver
   python -m pip install -e .

Use the API
===========

.. code-block:: python

   from anystruct import api

   flat = api.FlatStru("Flat plate, stiffened")
   cylinder = api.CylStru("Orthogonally Stiffened shell")

Start the GUI
=============

.. code-block:: python

   from anystruct import gui

   gui.main()

After installation, the ``ANYstructure`` console command is also available from
the Python environment's scripts directory.
