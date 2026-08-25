![picture](https://github.com/audunarn/ANYstructure/blob/master/anystruct/images/ANYstructure_logo.jpg)

# ANYstructure

ANYstructure is a desktop steel-structure design application for plate fields
and cylinders, including weight, weld, and cost optimization. Calculations are
based on DNV standards and recommended practices.

## Current release: 6.3.1

- Adds live Automatic, ModernGL GPU, and Tk software renderer selection to the
  maintained 3D model, mesh, and result views.
- Preserves the current scene and camera when a renderer is replaced; a failed
  explicit GPU switch keeps the working viewer intact.
- Uses the shared ANY3dView 0.5 contract while retaining the historical
  ANYtk3D compatibility module.

Earlier release history remains available in Git tags and release notes rather
than being duplicated in this README.

## Finite-element GUI integration

The FE GUI requires `ANYsolver>=0.3`. Axial force, bending moment,
shear force, torsional moment, pressure, and the supported collision controls
are mapped directly to the external solver runtime. Current-area follower
pressure is available for nonlinear static and arc-length runs on the Static
only or Nonlinear static runtime path; incompatible analysis paths are disabled
in the GUI and rejected by the solver. Arc-length runs retain the selected von
Karman or corotational kinematics, and nonlinear prestress/buckling recovery
retains committed-state provenance.

The main FE sections use raised, contrasting horizontal dividers, and the
result text and visualization have a vertical divider. Drag either divider to
resize its panes. Solver errors and unsupported configurations remain visible;
the GUI does not replace them with a lightweight estimate.

The GUI reflects solver-normalized analysis choices through ANYsolver's public
`resolve_runtime_analysis()` contract; it does not depend on private solver
helpers.

The material dropdowns are backed by ANYmaterial and include a
**Choose/edit material** button. The Interfaces menu opens ANYmesher and the
ANYfileio inspector inside the existing Tk event loop. Orthotropic selections
are refused explicitly until the legacy scalar material controls can represent
them without losing directional properties.

------------------------------------------------------------------------

For documentation:

https://anystructure.readthedocs.io/en/latest/

For tutorials:

https://www.youtube.com/@ANYopenSoft

## Development setup ##

ANYstructure is currently maintained as a Python package named `anystruct`. The GUI can still be launched through the `ANYstructure` console command after an editable install.

Recommended local setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --upgrade -e "C:\Github\ANY3dView[gpu]" -e "C:\Github\ANYmaterial" -e "C:\Github\ANYgeometry" -e "C:\Github\ANYmesh" -e "C:\Github\ANYio[semantics]" -e "C:\Github\ANYsolver" -e "C:\Github\ANYbuckling" -e "C:\Github\ANYtk3D" -e "C:\Github\ANYstructure"
python -m pip install -r requirements-dev.txt
python -m pytest
```

The editable bootstrap is intentionally ordered by dependency: viewer core,
material and geometry, meshing, semantic file I/O, solver, independent
buckling and Tk rendering, then ANYstructure. `run_gui.py` prints the same
graph with the exact active Python executable if metadata or an import origin
is stale.

ANYstructure 6.3.1 supports ANY3dView and ANYtk3D source checkouts at version
0.5.1 or newer. The launcher accepts shared checkouts whose `pyproject.toml`
files meet that minimum. To select different qualified checkouts explicitly, set
`$env:ANYSTRUCTURE_ANY3DVIEW_ROOT = "C:\path\to\ANY3dView-0.5.1"` and/or
`$env:ANYSTRUCTURE_ANYTK3D_ROOT = "C:\path\to\ANYtk3D-0.5.1"` before running
`run_gui.py`. Invalid overrides block startup instead of falling back silently.

ANYmesher is selected with the same fail-closed rule. The shared
`C:\Github\ANYmesh` checkout is used only while its `pyproject.toml` declares
version 0.2.5 or newer. Otherwise the launcher and its repair command use the
qualified checkout at `C:\Github\ANYsolver\.compat_anymesher_025`. Set
`$env:ANYSTRUCTURE_ANYMESHER_ROOT = "C:\path\to\ANYmesher-0.2.5"` to select a
different compatible checkout; an invalid override blocks startup.

`ANYsolver>=0.3`, `ANYgeometry>=0.2.4`, `ANYmaterial>=0.1`,
`ANYmesher>=0.2.5`, `ANYfileio[semantics]>=0.2`,
`ANYbuckling>=0.1`, `ANY3dView[gpu]>=0.5`, and
`ANYtk3D>=0.5` are required runtime dependencies. These minimum-only
constraints allow newer coordinated ecosystem releases. Install the editable sibling checkouts above until compatible
releases are available from PyPI. ANYgeometry is the shared neutral surface-geometry
authority; materials, structural properties, loads, mesh controls, and solver
state remain in their owning packages.

New geometry code should call `anygeometry.generators` directly. The
`anystruct.geometry_generators` module provides thin plate, stiffened-panel,
cylinder, and cone adapters for existing ANYstructure integrations, while
`anystruct.representation_geometry` temporarily preserves the historical
station-layout import path.

The central runtime/FEM and mesh-preview path now establishes one lazy, cached
`GeometryModel` through those adapters. Existing ANYsolver and GUI consumers
receive a geometry-backed dictionary projection with unchanged keys and values;
the owner model is built once only when a geometry-aware consumer requests it.
Semantic groups remain available out-of-band, while thicknesses, sections,
materials, loads, and analysis settings remain external. ANYsolver's legacy
runtime currently still builds its FE mesh from the dictionary projection; that
transitional payload conversion remains until ANYsolver accepts the neutral
model directly.

Launch the desktop app after installation:

```powershell
ANYstructure
```

From a source checkout, the same GUI can be launched with:

```powershell
python run_gui.py
```

Dependency groups are also available for focused installs:

```powershell
python -m pip install -r requirements-core.txt
python -m pip install -r requirements-ml.txt
python -m pip install -r requirements-excel.txt
```

Equivalent package extras are exposed as `core`, `ml`, `excel`, `dev`, and `all`. The default package install still includes Excel and ML dependencies for backwards compatibility.

Excel project import requires a local Excel installation and is not expected to run in basic automated tests.
The external Excel-sheet DNV PULS calculation workflow has been removed from this release; ML-CL remains available.

## Calculation scope

- Minimum plate thickness (DNV-OS-C101)
- Minimum section modulus of stiffener/plate (DNVGL-OS-C101)
- Minimum shear area (DNVGL-OS-C101)
- Plate buckling (DNVGL-RP-C201)
- Shell buckling (DNV-RP-C202)
- Machine-learning buckling predictions based on PULS data
- Semi-analytical buckling through ANYbuckling
- Fatigue for plate/stiffener connections (DNVGL-RP-C203)


Compartments (tank pressures) are created automatically.

Pressures on external hull (or any other generic location) is defined by specifying equations.

You can optimize cylinders, single plate/stiffener field or multiple. Geometry of double bottom can be optimized.

Contributions and bug reports are welcome through GitHub. General feedback can
also be sent to audunarn@gmail.com.

Screenshot (this example can be loaded from file "ship_section_example.txt"):

![picture](https://github.com/audunarn/ANYstructure/blob/master/anystruct/images/ANYstructure%20screenshot.png)
