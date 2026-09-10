"""Entry point and headless integrity check for the PyInstaller bundle."""

from __future__ import annotations

from importlib import import_module
from importlib import metadata
from importlib import resources
import sys


_ECOSYSTEM = (
    ("ANYstructure", "anystruct"),
    ("ANY3dView", "any3dview"),
    ("ANYbuckling", "anybuckling"),
    ("ANYfileio", "anyfileio"),
    ("ANYgeometry", "anygeometry"),
    ("ANYmaterial", "anymaterial"),
    ("ANYmesher", "anymesher"),
    ("ANYsolver", "anysolver"),
    ("ANYtk3D", "anytk3d"),
)
_REQUIRED_DATA = (
    "ANYstructure_documentation.pdf",
    "sections.csv",
    "ship_section_example.txt",
    "bulb_anglebar_tbar_flatbar.csv",
    "excel_input_example.xlsx",
)


def _self_test() -> int:
    """Validate frozen imports, metadata, and application data without Tk."""

    versions: list[str] = []
    for distribution, module_name in _ECOSYSTEM:
        import_module(module_name)
        versions.append(f"{distribution}={metadata.version(distribution)}")

    # Exercise the lazily imported desktop integrations as well as the package
    # roots.  This catches missing hidden imports without opening a GUI.
    for module_name in (
        "anystruct.main_application",
        "anystruct.fem_integration",
        "any3dview.gpu",
        "anymaterial.gui",
        "anymesher.gui",
        "anyfileio.gui",
        "anymesher._native",
    ):
        import_module(module_name)

    package_root = resources.files("anystruct")
    missing = [name for name in _REQUIRED_DATA if not package_root.joinpath(name).is_file()]
    if missing:
        raise RuntimeError("missing packaged ANYstructure data: " + ", ".join(missing))

    print("ANYstructure packaged self-test OK")
    print("; ".join(versions))
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return _self_test()

    from anystruct.__main__ import main as application_main

    application_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
