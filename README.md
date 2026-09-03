![ANYstructure logo](https://github.com/audunarn/ANYstructure/blob/master/anystruct/images/ANYstructure_logo.jpg)

# ANYstructure

ANYstructure is a desktop steel-structure design application for plate fields
and cylinders. It combines DNV-based rule calculations with structural
modelling, load definition, reporting, and weight, weld, and cost optimization.

## Core structural design

The original ANYstructure workflow remains the primary way to model and assess
a structure. It supports:

- minimum plate thickness, stiffener section modulus, and shear-area checks
  based on DNV-OS-C101;
- plate buckling based on DNV-RP-C201 and shell buckling based on DNV-RP-C202;
- fatigue assessment of plate and stiffener connections based on DNV-RP-C203;
- semi-analytical buckling through ANYbuckling and machine-learning buckling
  predictions based on PULS data;
- automatic compartment and tank-pressure generation, plus equation-defined
  external pressures;
- single and multiple plate/stiffener-field optimization, cylinder
  optimization, and double-bottom geometry optimization; and
- weight, weld, cost, report, spreadsheet, and 3D shell-model workflows.

Projects can be created and edited graphically, saved for later work, and used
to compare structural alternatives. The example below can be opened from
`anystruct/ship_section_example.txt`.

![ANYstructure structural model](https://github.com/audunarn/ANYstructure/blob/master/anystruct/images/ANYstructure%20screenshot.png)

Documentation: https://anystructure.readthedocs.io/en/latest/

Tutorials: https://www.youtube.com/@ANYopenSoft

## Current release: 6.4.0

Version 6.4.0 keeps the established structural calculation and optimization
workflow at the front of the application while adding the integrated finite-
element workflow described below. The coordinated release uses ANYfileio 0.3,
ANYmaterial 0.2, and ANYmesher 0.4 without artificial package downgrades.

Project-owned source code is distributed under the Mozilla Public License 2.0
starting with this release. Earlier releases retain the license terms that
accompanied them.

## Finite-element integration

The optional FE workflow requires `ANYsolver>=0.4.1,<0.5`. Axial force,
bending moment, shear force, torsional moment, pressure, and supported
collision controls are mapped directly to the external solver runtime.
Current-area follower pressure is available for nonlinear static and
arc-length runs on the Static only or Nonlinear static path. Incompatible
analysis paths are disabled in the GUI and rejected by the solver.

Arc-length runs retain the selected von Karman or corotational kinematics, and
nonlinear prestress/buckling recovery retains committed-state provenance.
Solver errors and unsupported configurations remain visible; the GUI does not
replace them with a lightweight estimate. Analysis choices are normalized by
ANYsolver's public `resolve_runtime_analysis()` contract.

ANYsolver 0.4.1 repairs qualified-Q4 final-state replay after plastic
increments. ANYstructure preserves the qualified Q4 formulation throughout
material-nonlinear runs; explicit legacy selection remains available to users.

Model, mesh, and result views support live Automatic, ModernGL GPU, and Tk
software renderer selection. The current scene and camera are retained during
a renderer change, and a failed explicit GPU switch leaves the working viewer
intact. Raised horizontal and vertical dividers allow the input, model, result
text, and visualization panes to be resized.

Material controls are backed by ANYmaterial. The Interfaces menu opens
ANYmesher and the ANYfileio inspector in the existing Tk event loop.
Orthotropic selections are rejected until the legacy scalar material controls
can represent their directional properties without loss.

## Install and run

Install the published package and start the desktop application:

```powershell
python -m pip install --upgrade ANYstructure
ANYstructure
```

From a source checkout, use the active Python environment:

```powershell
python run_gui.py
```

The default install includes Excel and machine-learning dependencies for
backwards compatibility. Focused dependency groups are available as the
`core`, `excel`, `ml`, `dev`, and `all` extras, and as requirement files:

```powershell
python -m pip install -r requirements-core.txt
python -m pip install -r requirements-ml.txt
python -m pip install -r requirements-excel.txt
```

Excel project import requires a local Excel installation and is not exercised
by basic automated tests. The external Excel-sheet DNV PULS calculation
workflow has been removed; ML-CL remains available.

## Coordinated development setup

ANYstructure is published as the Python package `anystruct`. For a sibling
checkout layout, install each editable project into one environment in
dependency order:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --upgrade --no-deps -e "C:\Github\ANY3dView[gpu]" -e "C:\Github\ANYmaterial" -e "C:\Github\ANYgeometry" -e "C:\Github\ANYmesh" -e "C:\Github\ANYfileIO[semantics]" -e "C:\Github\ANYsolver" -e "C:\Github\ANYbuckling" -e "C:\Github\ANYtk3D" -e "C:\Github\ANYstructure"
python -m pip install -r requirements-dev.txt
python -m pytest
```

The default command runs the fast compatibility suite. Run the focused tiers
explicitly when changing their owning code:

```powershell
python -m pytest -m "fem_integration and not slow"
python -m pytest -m release_authority
python -m pytest -m slow
```

The slow tier contains nonlinear, collision, transient, mode-imperfection, and
large external-format qualification and is intentionally opt-in during
ordinary development.

`--no-deps` refreshes editable metadata without forcing pip to resolve stale
transitive upper bounds from older sibling releases. `run_gui.py` reports the
exact repair command for its active interpreter when selected source and
installed metadata do not agree.

The coordinated compatibility ranges are:

- `ANY3dView>=0.5.5,<0.6` (`ANYstructure[gpu]` adds ModernGL)
- `ANYbuckling>=0.1.1,<0.2`
- `ANYfileio[semantics]>=0.3.1,<0.4`
- `ANYgeometry>=0.4.2,<0.5`
- `ANYmaterial>=0.2.0,<0.3`
- `ANYmesher>=0.4.0,<0.5`
- `ANYsolver>=0.4.1,<0.5`
- `ANYtk3D>=0.5.5,<0.6`

To select a particular checkout, set the corresponding
`ANYSTRUCTURE_ANY3DVIEW_ROOT`, `ANYSTRUCTURE_ANYTK3D_ROOT`,
`ANYSTRUCTURE_ANYBUCKLING_ROOT`, `ANYSTRUCTURE_ANYFILEIO_ROOT`,
`ANYSTRUCTURE_ANYGEOMETRY_ROOT`, `ANYSTRUCTURE_ANYMATERIAL_ROOT`,
`ANYSTRUCTURE_ANYMESHER_ROOT`, or `ANYSTRUCTURE_ANYSOLVER_ROOT` environment
variable. Invalid explicit roots fail before application imports.

ANYgeometry owns neutral surface geometry. New geometry code should call
`anygeometry.generators` directly. The `anystruct.geometry_generators` and
`anystruct.representation_geometry` modules retain adapters for established
ANYstructure integrations. Structural properties, loads, mesh controls, and
solver state remain in their owning packages.

## License and contributions

Project-owned source code in release 6.4.0 and later is licensed under the
[Mozilla Public License 2.0](https://github.com/audunarn/ANYstructure/blob/master/LICENSE).
Original project documentation is licensed under
[CC BY 4.0](https://github.com/audunarn/ANYstructure/blob/master/docs/LICENSE.md).
Third-party software, models, figures, standards material, and other
attributed content retain their own terms; see the
[third-party notices](https://github.com/audunarn/ANYstructure/blob/master/THIRD_PARTY_NOTICES.md).
Project branding is covered by the
[trademark policy](https://github.com/audunarn/ANYstructure/blob/master/TRADEMARKS.md).

Contributions and bug reports are welcome through GitHub. General feedback can
also be sent to audunarn@gmail.com.
