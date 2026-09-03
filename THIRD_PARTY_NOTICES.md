# Third-party notices

ANYstructure's project-owned source is licensed under MPL-2.0 starting with
version 6.4.0. Dependencies and bundled third-party works remain subject to
their upstream terms.

## Bundled software

| Component | Purpose | Upstream | License | Bundled form |
| --- | --- | --- | --- | --- |
| IfcOpenShell IfcConvert 0.8.5-1c5b825 (OCC 7.8.1) | IFC geometry conversion | https://ifcopenshell.org/ | LGPL-3.0-or-later and applicable bundled component licenses | `anystruct/IfcConvert.exe` |

IfcConvert is a separate executable invoked by ANYstructure. Its inclusion
does not change its copyright or license terms. The IfcOpenShell source and
license information are available from
https://github.com/IfcOpenShell/IfcOpenShell.

## Separately installed dependencies

Python package dependencies declared in `setup.py` are installed separately;
their source and object code are not copied into the ANYstructure wheel except
where a package manager independently bundles them. They retain the licenses
published by their respective projects. This includes the ANYopenSoft
ecosystem packages, Matplotlib, meshio, NumPy, numpy-stl, Pillow, ReportLab,
SciPy, scikit-learn, and xlwings.

The directly used ANYopenSoft packages currently declare these licenses:

| Package | ANYstructure range | Upstream license |
| --- | --- | --- |
| ANY3dView | `>=0.5.4,<0.6` | MPL-2.0 |
| ANYbuckling | `>=0.1.1,<0.2` | GPL-3.0-or-later |
| ANYfileio | `>=0.2.1,<0.4` | MPL-2.0 for the current 0.3 line; earlier releases retain their accompanying terms |
| ANYgeometry | `>=0.4.1,<0.5` | MPL-2.0 |
| ANYmaterial | `>=0.1.1,<0.3` | MPL-2.0 for the current 0.2 line; earlier releases retain their accompanying terms |
| ANYmesher | `>=0.3.1,<0.5` | Refer to the installed release; the 0.4 alpha line declares MPL-2.0 |
| ANYsolver | `>=0.4.0,<0.5` | MPL-2.0 |
| ANYtk3D | `>=0.5.3,<0.6` | MPL-2.0 |

The bundled machine-learning model files and engineering images are not
third-party Python dependencies and are not covered by the documentation
license. Attributed source material retains its original terms.
