Installation
************

Install from PyPI
=================

.. code-block:: shell

   pip install anystructure

The finite-element GUI requires ``ANYsolver>=0.3,<0.4`` together with
``ANYmaterial``, ``ANYmesher>=0.2.3,<0.3``, and ``ANYfileio``. The new ecosystem packages
are installed from their source repositories until their first compatible PyPI
releases are available.

For coordinated local development, install the siblings before the ANYstructure
checkout:

.. code-block:: powershell

   python -m pip install --upgrade -e "C:\Github\ANY3dView[gpu]" -e "C:\Github\ANYmaterial" -e "C:\Github\ANYgeometry" -e "C:\Github\ANYsolver\.compat_anymesher_023" -e "C:\Github\ANYio[semantics]" -e "C:\Github\ANYsolver" -e "C:\Github\ANYbuckling" -e "C:\Github\ANYtk3D" -e "C:\Github\ANYstructure"

``run_gui.py`` accepts ``C:\Github\ANYmesh`` only when that checkout declares
exactly ANYmesher 0.2.3. Otherwise it uses
``C:\Github\ANYsolver\.compat_anymesher_023``. Set
``ANYSTRUCTURE_ANYMESHER_ROOT`` to another exact 0.2.3 checkout when needed;
the launcher rejects an invalid override before importing Tk.

The desktop installs ``ANY3dView[gpu]>=0.5,<0.6`` and
``ANYtk3D>=0.5,<0.6``. Maintained 3D views expose an Automatic/GPU/Tk selector;
Automatic prefers ModernGL and reports any software fallback.

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
