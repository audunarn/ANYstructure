#!/usr/bin/env python
"""Run the ANYstructure desktop application from this checkout."""

from __future__ import annotations

import sys
import os
from importlib import util as importlib_util
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


_ROOT = Path(__file__).resolve().parent
ANYMESHER_SOURCE_ROOT_ENV = "ANYSTRUCTURE_ANYMESHER_ROOT"
ANYMESHER_REQUIRED_SOURCE_VERSION = "0.2.5"
_SHARED_ANYMESHER_ROOT = _ROOT.parent / "ANYmesh"
_SAFE_ANYMESHER_ROOT = _ROOT.parent / "ANYsolver" / ".compat_anymesher_025"
ANYTK3D_SOURCE_ROOT_ENV = "ANYSTRUCTURE_ANYTK3D_ROOT"
ANYTK3D_REQUIRED_SOURCE_VERSION = "0.5.1"
_SHARED_ANYTK3D_ROOT = _ROOT.parent / "ANYtk3D"
_SAFE_ANYTK3D_ROOT = _ROOT.parent / "ANYsolver" / ".compat_anytk3d_050"
ANY3DVIEW_SOURCE_ROOT_ENV = "ANYSTRUCTURE_ANY3DVIEW_ROOT"
ANY3DVIEW_REQUIRED_SOURCE_VERSION = "0.5.1"
_SHARED_ANY3DVIEW_ROOT = _ROOT.parent / "ANY3dView"
_SAFE_ANY3DVIEW_ROOT = _ROOT.parent / "ANYsolver" / ".compat_any3dview_050"


def _source_project_identity(root: Path) -> tuple[str | None, str | None]:
    """Read static project name/version fields without importing the package."""

    import re

    pyproject = root / "pyproject.toml"
    try:
        contents = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None, None
    in_project = False
    values: dict[str, str] = {}
    for raw_line in contents.splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            in_project = line == "[project]"
            continue
        if not in_project:
            continue
        match = re.fullmatch(
            r"(name|version)\s*=\s*(['\"])([^'\"]+)\2(?:\s*#.*)?",
            line,
        )
        if match:
            values[match.group(1)] = match.group(3).strip()
    return values.get("name"), values.get("version")


def _numeric_version(value: object) -> tuple[int, int, int]:
    """Return the first three numeric release components."""

    import re

    parts = [int(item) for item in re.findall(r"\d+", str(value or ""))[:3]]
    return tuple((parts + [0, 0, 0])[:3])


def _anytk3d_source_problem(root: Path) -> str | None:
    name, version = _source_project_identity(root)
    if name != "ANYtk3D":
        return f"{root / 'pyproject.toml'} does not declare project name ANYtk3D"
    if _numeric_version(version) < _numeric_version(ANYTK3D_REQUIRED_SOURCE_VERSION):
        shown = version if version is not None else "no static version"
        return (
            f"{root / 'pyproject.toml'} declares {shown}; "
            f"at least {ANYTK3D_REQUIRED_SOURCE_VERSION} is required"
        )
    package = root / "src" / "anytk3d" / "__init__.py"
    if not package.is_file():
        return f"qualified package source is missing: {package}"
    return None


def _any3dview_source_problem(root: Path) -> str | None:
    name, version = _source_project_identity(root)
    if name != "ANY3dView":
        return f"{root / 'pyproject.toml'} does not declare project name ANY3dView"
    if _numeric_version(version) < _numeric_version(ANY3DVIEW_REQUIRED_SOURCE_VERSION):
        shown = version if version is not None else "no static version"
        return (
            f"{root / 'pyproject.toml'} declares {shown}; "
            f"at least {ANY3DVIEW_REQUIRED_SOURCE_VERSION} is required"
        )
    package = root / "src" / "any3dview" / "__init__.py"
    if not package.is_file():
        return f"qualified package source is missing: {package}"
    return None


def _anymesher_source_problem(root: Path) -> str | None:
    name, version = _source_project_identity(root)
    if name != "ANYmesher":
        return f"{root / 'pyproject.toml'} does not declare project name ANYmesher"
    if _numeric_version(version) < _numeric_version(ANYMESHER_REQUIRED_SOURCE_VERSION):
        shown = version if version is not None else "no static version"
        return (
            f"{root / 'pyproject.toml'} declares {shown}; "
            f"at least {ANYMESHER_REQUIRED_SOURCE_VERSION} is required"
        )
    package = root / "src" / "anymesher" / "__init__.py"
    if not package.is_file():
        return f"qualified package source is missing: {package}"
    return None


def select_anymesher_source_root(
    environ: Mapping[str, str] | None = None,
    *,
    shared_root: Path | None = None,
    safe_root: Path | None = None,
) -> Path:
    """Select a supported ANYmesher source checkout without importing it."""

    environment = os.environ if environ is None else environ
    override = str(environment.get(ANYMESHER_SOURCE_ROOT_ENV, "")).strip()
    if override:
        candidate = Path(override).expanduser()
        problem = _anymesher_source_problem(candidate)
        if problem:
            raise RuntimeError(
                f"Invalid {ANYMESHER_SOURCE_ROOT_ENV} override: {problem}"
            )
        return candidate.resolve()

    shared = _SHARED_ANYMESHER_ROOT if shared_root is None else Path(shared_root)
    safe = _SAFE_ANYMESHER_ROOT if safe_root is None else Path(safe_root)
    rejected: list[str] = []
    for label, candidate in (("shared", shared), ("qualified fallback", safe)):
        problem = _anymesher_source_problem(candidate)
        if problem is None:
            return candidate.resolve()
        rejected.append(f"{label}: {problem}")
    raise RuntimeError(
        "ANYstructure 6.3.1 needs an ANYmesher source checkout at version 0.2.5 or newer. "
        f"Set {ANYMESHER_SOURCE_ROOT_ENV} to one. Checked:\n- "
        + "\n- ".join(rejected)
    )


def select_anytk3d_source_root(
    environ: Mapping[str, str] | None = None,
    *,
    shared_root: Path | None = None,
    safe_root: Path | None = None,
) -> Path:
    """Select a supported ANYtk3D source checkout without importing it."""

    environment = os.environ if environ is None else environ
    override = str(environment.get(ANYTK3D_SOURCE_ROOT_ENV, "")).strip()
    if override:
        candidate = Path(override).expanduser()
        problem = _anytk3d_source_problem(candidate)
        if problem:
            raise RuntimeError(
                f"Invalid {ANYTK3D_SOURCE_ROOT_ENV} override: {problem}"
            )
        return candidate.resolve()

    shared = _SHARED_ANYTK3D_ROOT if shared_root is None else Path(shared_root)
    safe = _SAFE_ANYTK3D_ROOT if safe_root is None else Path(safe_root)
    rejected: list[str] = []
    for label, candidate in (("shared", shared), ("qualified fallback", safe)):
        problem = _anytk3d_source_problem(candidate)
        if problem is None:
            return candidate.resolve()
        rejected.append(f"{label}: {problem}")
    raise RuntimeError(
        "ANYstructure 6.3.1 needs an ANYtk3D source checkout at version 0.5.1 or newer. "
        f"Set {ANYTK3D_SOURCE_ROOT_ENV} to one. Checked:\n- "
        + "\n- ".join(rejected)
    )


def select_any3dview_source_root(
    environ: Mapping[str, str] | None = None,
    *,
    shared_root: Path | None = None,
    safe_root: Path | None = None,
) -> Path:
    """Select a supported ANY3dView source checkout without importing it."""

    environment = os.environ if environ is None else environ
    override = str(environment.get(ANY3DVIEW_SOURCE_ROOT_ENV, "")).strip()
    if override:
        candidate = Path(override).expanduser()
        problem = _any3dview_source_problem(candidate)
        if problem:
            raise RuntimeError(
                f"Invalid {ANY3DVIEW_SOURCE_ROOT_ENV} override: {problem}"
            )
        return candidate.resolve()

    shared = _SHARED_ANY3DVIEW_ROOT if shared_root is None else Path(shared_root)
    safe = _SAFE_ANY3DVIEW_ROOT if safe_root is None else Path(safe_root)
    rejected: list[str] = []
    for label, candidate in (("shared", shared), ("qualified fallback", safe)):
        problem = _any3dview_source_problem(candidate)
        if problem is None:
            return candidate.resolve()
        rejected.append(f"{label}: {problem}")
    raise RuntimeError(
        "ANYstructure 6.3.1 needs an ANY3dView source checkout at version 0.5.1 or newer. "
        f"Set {ANY3DVIEW_SOURCE_ROOT_ENV} to one. Checked:\n- "
        + "\n- ".join(rejected)
    )


_ANYMESHER_ROOT = select_anymesher_source_root()
_ANY3DVIEW_ROOT = select_any3dview_source_root()
_ANYTK3D_ROOT = select_anytk3d_source_root()
_SOURCE_TREES = (
    _ANY3DVIEW_ROOT / "src",
    _ROOT.parent / "ANYgeometry" / "src",
    _ROOT.parent / "ANYsolver" / "src",
    _ROOT.parent / "ANYmaterial" / "src",
    _ANYMESHER_ROOT / "src",
    _ROOT.parent / "ANYio" / "src",
    _ROOT.parent / "ANYbuckling" / "src",
    _ANYTK3D_ROOT / "src",
)
for _source in reversed(_SOURCE_TREES):
    if _source.is_dir() and str(_source) not in sys.path:
        sys.path.insert(0, str(_source))


# Distribution metadata is checked before importing the GUI.  The launcher
# deliberately exposes sibling source trees above, and an old editable install
# can therefore provide stale metadata while newer Python modules are imported.
# That split state is particularly unsafe for schema/semantics integrations.
ECOSYSTEM_REQUIREMENTS = (
    ("ANY3dView", "ANY3dView[gpu]>=0.5", "0.5.1"),
    ("ANYbuckling", "ANYbuckling>=0.1", "0.1.1"),
    ("ANYfileio", "ANYfileio[semantics]>=0.2", "0.2.1"),
    ("ANYgeometry", "ANYgeometry>=0.2.4", "0.2.4"),
    ("ANYmaterial", "ANYmaterial>=0.1", "0.1.1"),
    ("ANYmesher", "ANYmesher>=0.2.5", "0.2.5"),
    ("ANYsolver", "ANYsolver>=0.3", "0.3.0"),
    ("ANYtk3D", "ANYtk3D>=0.5", "0.5.1"),
)

# Import names and the sibling source roots they must resolve from.  This is
# intentionally separate from distribution metadata: a current dist-info next
# to a stale wheel (or vice versa) must not make a checkout launch appear safe.
ECOSYSTEM_SOURCES = (
    ("ANY3dView", "any3dview", _ANY3DVIEW_ROOT / "src"),
    ("ANYbuckling", "anybuckling", _ROOT.parent / "ANYbuckling" / "src"),
    ("ANYfileio", "anyfileio", _ROOT.parent / "ANYio" / "src"),
    ("ANYgeometry", "anygeometry", _ROOT.parent / "ANYgeometry" / "src"),
    ("ANYmaterial", "anymaterial", _ROOT.parent / "ANYmaterial" / "src"),
    ("ANYmesher", "anymesher", _ANYMESHER_ROOT / "src"),
    ("ANYsolver", "anysolver", _ROOT.parent / "ANYsolver" / "src"),
    ("ANYtk3D", "anytk3d", _ANYTK3D_ROOT / "src"),
)

EDITABLE_BOOTSTRAP_PROJECTS = (
    str(_ANY3DVIEW_ROOT) + "[gpu]",
    str(_ROOT.parent / "ANYmaterial"),
    str(_ROOT.parent / "ANYgeometry"),
    str(_ANYMESHER_ROOT),
    str(_ROOT.parent / "ANYio") + "[semantics]",
    str(_ROOT.parent / "ANYsolver"),
    str(_ROOT.parent / "ANYbuckling"),
    str(_ANYTK3D_ROOT),
    str(_ROOT),
)


def ecosystem_compatibility_problems(
    version_reader: Callable[[str], str] | None = None,
) -> tuple[str, ...]:
    """Describe missing or stale ecosystem distribution metadata."""

    read_version = metadata.version if version_reader is None else version_reader
    problems: list[str] = []
    for distribution, requirement, minimum in ECOSYSTEM_REQUIREMENTS:
        try:
            installed = str(read_version(distribution))
        except metadata.PackageNotFoundError:
            problems.append(f"{requirement}: distribution metadata is missing")
            continue
        numeric = _numeric_version(installed)
        if numeric < _numeric_version(minimum):
            problems.append(f"{requirement}: installed metadata reports {installed}")
    return tuple(problems)


def _path_is_within(path: Path, root: Path) -> bool:
    """Compare resolved paths robustly on case-insensitive Windows drives."""

    try:
        common = os.path.commonpath(
            (os.path.normcase(str(path.resolve())), os.path.normcase(str(root.resolve())))
        )
    except (OSError, ValueError):
        return False
    return common == os.path.normcase(str(root.resolve()))


def ecosystem_source_problems(
    spec_finder: Callable[[str], Any] | None = None,
) -> tuple[str, ...]:
    """Verify package origins without importing any ecosystem or GUI module."""

    find_spec = importlib_util.find_spec if spec_finder is None else spec_finder
    problems: list[str] = []
    for distribution, module_name, expected_root in ECOSYSTEM_SOURCES:
        if not expected_root.is_dir():
            problems.append(
                f"{distribution}: expected sibling source tree is missing: {expected_root}"
            )
            continue
        try:
            spec = find_spec(module_name)
        except (AttributeError, ImportError, ValueError) as error:
            problems.append(f"{distribution}: cannot resolve {module_name}: {error}")
            continue
        if spec is None:
            problems.append(f"{distribution}: cannot resolve import {module_name}")
            continue
        candidates: list[Path] = []
        origin = getattr(spec, "origin", None)
        if origin and origin not in {"built-in", "frozen"}:
            candidates.append(Path(origin))
        locations = getattr(spec, "submodule_search_locations", None) or ()
        candidates.extend(Path(value) for value in locations)
        if not candidates or not any(
            _path_is_within(candidate, expected_root) for candidate in candidates
        ):
            shown = ", ".join(str(value) for value in candidates) or "unknown origin"
            problems.append(
                f"{distribution}: {module_name} resolves from {shown}; "
                f"expected {expected_root}"
            )
    return tuple(problems)


def editable_repair_command() -> str:
    """Return a copy/paste repair command for this sibling-checkout layout."""

    editables = " ".join(f'-e "{project}"' for project in EDITABLE_BOOTSTRAP_PROJECTS)
    return f'"{sys.executable}" -m pip install --upgrade {editables}'


def require_compatible_ecosystem(
    version_reader: Callable[[str], str] | None = None,
    spec_finder: Callable[[str], Any] | None = None,
) -> None:
    """Fail before Tk startup when editable metadata is not release-compatible."""

    problems = (
        ecosystem_compatibility_problems(version_reader)
        + ecosystem_source_problems(spec_finder)
    )
    if problems:
        raise RuntimeError(
            "ANYstructure 6.3.1 cannot start with this mixed ecosystem:\n- "
            + "\n- ".join(problems)
            + "\nRepair the sibling editable installs, then restart:\n"
            + editable_repair_command()
        )


def main(args: Sequence[str] | None = None) -> None:
    """Launch the GUI using the package's maintained entry point."""

    require_compatible_ecosystem()
    from anystruct.__main__ import main as gui_main

    gui_main(args)


if __name__ == "__main__":
    main()
