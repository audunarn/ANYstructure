# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller definition for the Windows ANYstructure desktop bundle."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata


ROOT = Path(SPECPATH)

datas = []
binaries = []
hiddenimports = []

# Collect runtime data and native extensions without recursively forcing every
# optional or developer-only submodule into the application.
for package in (
    "anystruct",
    "any3dview",
    "anybuckling",
    "anyfileio",
    "anygeometry",
    "anymaterial",
    "anymesher",
    "anysolver",
    "anytk3d",
):
    datas += collect_data_files(package, include_py_files=False)
    binaries += collect_dynamic_libs(package)

# These imports are intentionally discovered at runtime by their owning
# packages and therefore need explicit frozen-module entries.
hiddenimports += [
    "anymaterial",
    "anymesher",
    "anymesher._native",
]

# ANYstructure reports ecosystem versions through importlib.metadata.  Editable
# development installs do not otherwise guarantee that their dist-info is
# discovered by PyInstaller.
for distribution in (
    "ANYstructure",
    "ANY3dView",
    "ANYbuckling",
    "ANYfileio",
    "ANYgeometry",
    "ANYmaterial",
    "ANYmesher",
    "ANYsolver",
    "ANYtk3D",
):
    datas += copy_metadata(distribution)

datas += [
    (str(ROOT / "matplotlibrc"), "."),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "NOTICE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    (str(ROOT / "TRADEMARKS.md"), "."),
]

a = Analysis(
    [str(ROOT / "tools" / "pyinstaller_entry.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": ["TkAgg"]}},
    runtime_hooks=[str(ROOT / "tools" / "pyinstaller_runtime.py")],
    excludes=[
        "IPython",
        "boto3",
        "botocore",
        "cupy",
        "dask",
        "h5py",
        "jupyter",
        "netCDF4",
        "notebook",
        "plotly",
        "pandas",
        "pyarrow",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "pytest",
        "sphinx",
        "torch",
        "xarray",
        "zarr",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ANYstructure",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "ANYicon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ANYstructure",
)
