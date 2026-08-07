Installation
************

Install from PyPI
=================

.. code-block:: shell

   pip install anystructure

The finite-element GUI requires ``ANYsolver>=0.2,<0.3`` together with
``ANYmaterial``, ``ANYmesher``, and ``ANYfileio``. The new ecosystem packages
are installed from their source repositories until their first compatible PyPI
releases are available.

For coordinated local development, install the siblings before the ANYstructure
checkout:

.. code-block:: powershell

   python -m pip install --no-deps -e C:\Github\ANYmaterial
   python -m pip install --no-deps -e C:\Github\ANYmesh
   python -m pip install --no-deps -e C:\Github\ANYio
   python -m pip install --no-deps -e C:\Github\ANYsolver
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
