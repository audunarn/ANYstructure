Installation
************

Install from PyPI
=================

.. code-block:: shell

   pip install anystructure

The finite-element GUI uses the coordinated ranges
``ANYsolver>=0.4.1,<0.5``, ``ANYgeometry>=0.4.2,<0.5``,
``ANYmaterial>=0.2.0,<0.3``, ``ANYmesher>=0.4.0,<0.5``,
``ANYfileio[semantics]>=0.3.1,<0.4``, ``ANYbuckling>=0.1.1,<0.2``,
``ANY3dView>=0.5.5,<0.6``, and ``ANYtk3D>=0.5.5,<0.6``. Install
``ANYstructure[gpu]`` to add the optional ModernGL backend.
Install the exact coordinated source candidates below until those releases are
available from PyPI.

For coordinated local development, install the siblings before the ANYstructure
checkout:

.. code-block:: powershell

   python -m pip install --upgrade --no-deps -e "C:\Github\ANY3dView[gpu]" -e "C:\Github\ANYmaterial" -e "C:\Github\ANYgeometry" -e "C:\Github\ANYmesh" -e "C:\Github\ANYfileIO[semantics]" -e "C:\Github\ANYsolver" -e "C:\Github\ANYbuckling" -e "C:\Github\ANYtk3D" -e "C:\Github\ANYstructure"

``--no-deps`` is intentional for this coordinated source checkout: it refreshes
the editable distributions without asking pip to resolve legacy transitive
upper bounds from older sibling releases.

``run_gui.py`` accepts ``C:\Github\ANYmesh`` when that checkout declares
ANYmesher in ``>=0.4.0,<0.5``. Set ``ANYSTRUCTURE_ANYMESHER_ROOT`` to another
compatible checkout when needed; the launcher rejects an invalid override
before importing Tk.

The desktop installs ``ANY3dView>=0.5.5,<0.6`` and
``ANYtk3D>=0.5.5,<0.6``. Maintained 3D views expose an Automatic/GPU/Tk
selector; Automatic prefers ModernGL and reports any software fallback. Exact
qualification roots may be supplied through ``ANYSTRUCTURE_ANY3DVIEW_ROOT``,
``ANYSTRUCTURE_ANYTK3D_ROOT``, ``ANYSTRUCTURE_ANYBUCKLING_ROOT``,
``ANYSTRUCTURE_ANYFILEIO_ROOT``, ``ANYSTRUCTURE_ANYGEOMETRY_ROOT``,
``ANYSTRUCTURE_ANYMATERIAL_ROOT``, and ``ANYSTRUCTURE_ANYSOLVER_ROOT``. Each
explicit root is validated before application imports.

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
