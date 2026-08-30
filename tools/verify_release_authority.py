#!/usr/bin/env python3
"""Verify a ledger-authorized, prebuilt Python release bundle.

The release ledger is deliberately created only after the artifact-source
commit and exact distributions have been frozen.  It must be the sole file
added by the tagged commit whose only parent is that artifact source.
"""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile


SCHEMA = "anyecosystem.release-ledger-v1"
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9A-F]{64}")


def _fail(message: str) -> "NoReturn":
    raise SystemExit(message)


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    forbidden = {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_ATTR_SOURCE",
        "GIT_COMMON_DIR",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
        "GIT_DIFF_OPTS",
        "GIT_DIR",
        "GIT_EXTERNAL_DIFF",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PAGER",
        "GIT_SHALLOW_FILE",
        "GIT_WORK_TREE",
    }
    for key in tuple(environment):
        if (
            key in forbidden
            or key.startswith("GIT_CONFIG_KEY_")
            or key.startswith("GIT_CONFIG_VALUE_")
        ):
            environment.pop(key, None)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_ATTR_NOSYSTEM"] = "1"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _git_run(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            "git",
            "-c",
            "core.attributesFile=",
            "-c",
            "diff.external=",
            "-c",
            "core.pager=cat",
            *arguments,
        ],
        cwd=root,
        env=_git_environment(),
        check=False,
        capture_output=True,
    )


def _git(root: Path, *arguments: str, check: bool = True) -> bytes:
    completed = _git_run(root, *arguments)
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        _fail(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate ledger key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"nonfinite ledger value: {value}")


def _reject_float(value: str) -> object:
    raise ValueError(f"floating ledger value is forbidden: {value}")


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        _fail(f"{label} keys differ")
    return value


def _canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _metadata_matches(raw: bytes, distribution: str, version: str, label: str) -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(raw)
    if _canonical_name(str(metadata.get("Name", ""))) != _canonical_name(distribution):
        _fail(f"{label} distribution metadata differs")
    if str(metadata.get("Version", "")) != version:
        _fail(f"{label} version metadata differs")


def _verify_wheel(path: Path, distribution: str, version: str) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or any(not _safe_archive_name(name) for name in names):
                _fail("wheel contains duplicate or unsafe members")
            for info in infos:
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    _fail("wheel contains a symbolic link")
            metadata = [info for info in infos if info.filename.endswith(".dist-info/METADATA")]
            if len(metadata) != 1 or metadata[0].is_dir():
                _fail("wheel must contain exactly one regular METADATA member")
            _metadata_matches(archive.read(metadata[0]), distribution, version, "wheel")
    except (OSError, zipfile.BadZipFile) as exc:
        _fail(f"wheel is malformed: {exc}")


def _verify_sdist(path: Path, distribution: str, version: str) -> None:
    try:
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            if len(names) != len(set(names)) or any(not _safe_archive_name(name) for name in names):
                _fail("sdist contains duplicate or unsafe members")
            if any(not (member.isdir() or member.isreg()) for member in members):
                _fail("sdist contains a link or special member")
            metadata = [
                member
                for member in members
                if member.isreg()
                and len(PurePosixPath(member.name).parts) == 2
                and PurePosixPath(member.name).name == "PKG-INFO"
            ]
            if len(metadata) != 1:
                _fail("sdist must contain exactly one top-level PKG-INFO member")
            stream = archive.extractfile(metadata[0])
            if stream is None:
                _fail("sdist PKG-INFO is unreadable")
            _metadata_matches(stream.read(), distribution, version, "sdist")
    except (OSError, tarfile.TarError) as exc:
        _fail(f"sdist is malformed: {exc}")


def _load_ledger(root: Path, relative: Path) -> tuple[dict[str, object], bytes]:
    if relative.is_absolute() or ".." in relative.parts:
        _fail("ledger path is unsafe")
    path = root / relative
    if not path.is_file() or path.is_symlink():
        _fail("release ledger must be a regular non-symlink file")
    raw = path.read_bytes()
    if _git(root, "show", f"HEAD:{relative.as_posix()}") != raw:
        _fail("working release ledger differs from tag HEAD")
    try:
        text = raw.decode("utf-8")
        ledger = json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        _fail(f"release ledger is not strict UTF-8 JSON: {exc}")
    canonical = (json.dumps(ledger, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if raw != canonical:
        _fail("release ledger is not canonical JSON")
    return ledger, raw


def verify(arguments: argparse.Namespace) -> None:
    root = Path(arguments.repository_root).resolve()
    ledger_path = Path(arguments.ledger)
    ledger, _raw = _load_ledger(root, ledger_path)
    ledger = _exact_keys(
        ledger,
        {
            "artifact_source",
            "artifacts",
            "distribution",
            "publication_authorized",
            "qualification",
            "schema",
            "tag",
            "version",
        },
        "release ledger",
    )
    if ledger["schema"] != SCHEMA:
        _fail("release ledger schema differs")
    if ledger["distribution"] != arguments.distribution or ledger["version"] != arguments.version:
        _fail("release ledger package identity differs")
    if ledger["tag"] != arguments.tag or ledger["publication_authorized"] is not True:
        _fail("release tag or publication authority differs")

    if (
        arguments.tag != f"v{arguments.version}"
        or re.fullmatch(
            r"v(?:0|[1-9][0-9]*)\."
            r"(?:0|[1-9][0-9]*)\."
            r"(?:0|[1-9][0-9]*)",
            arguments.tag,
        )
        is None
    ):
        _fail("release tag is not canonical")
    tag_ref = f"refs/tags/{arguments.tag}"
    if (
        _git_run(root, "check-ref-format", "--allow-onelevel", tag_ref).returncode
        != 0
    ):
        _fail("release tag ref is malformed")
    tag_result = _git_run(
        root,
        "rev-parse",
        "--verify",
        f"{tag_ref}^{{commit}}",
    )
    if tag_result.returncode != 0:
        _fail("release tag ref does not resolve to a commit")
    tag_commit = tag_result.stdout.decode().strip()
    head_commit = _git(
        root,
        "rev-parse",
        "--verify",
        "HEAD^{commit}",
    ).decode().strip()
    if (
        COMMIT_RE.fullmatch(tag_commit) is None
        or COMMIT_RE.fullmatch(head_commit) is None
        or tag_commit != head_commit
    ):
        _fail("release tag ref does not identify the ledger HEAD")

    qualification = _exact_keys(
        ledger["qualification"],
        {
            "accepted_terminal",
            "evidence_sha256",
            "independent_review_sha256",
        },
        "qualification",
    )
    accepted_terminal = qualification["accepted_terminal"]
    evidence_sha = qualification["evidence_sha256"]
    review_sha = qualification["independent_review_sha256"]
    if (
        type(accepted_terminal) is not str
        or accepted_terminal != arguments.expected_terminal
        or re.fullmatch(r"[A-Z][A-Z0-9_]+", accepted_terminal) is None
        or any(
            token in accepted_terminal
            for token in ("PLACEHOLDER", "TO_BE_REBOUND", "REBIND_FINAL")
        )
    ):
        _fail("accepted qualification terminal differs")
    if (
        type(evidence_sha) is not str
        or SHA256_RE.fullmatch(evidence_sha) is None
        or evidence_sha == "0" * 64
    ):
        _fail("qualification evidence SHA-256 is malformed")
    if (
        type(review_sha) is not str
        or SHA256_RE.fullmatch(review_sha) is None
        or review_sha == "0" * 64
        or review_sha == evidence_sha
    ):
        _fail("independent review SHA-256 is malformed or non-independent")

    source = _exact_keys(ledger["artifact_source"], {"commit", "tree"}, "artifact source")
    source_commit = source["commit"]
    source_tree = source["tree"]
    if type(source_commit) is not str or COMMIT_RE.fullmatch(source_commit) is None:
        _fail("artifact-source commit is malformed")
    if type(source_tree) is not str or COMMIT_RE.fullmatch(source_tree) is None:
        _fail("artifact-source tree is malformed")

    if _git(root, "for-each-ref", "--format=%(refname)", "refs/replace").strip():
        _fail("Git replacement objects are forbidden")
    graft_path = Path(_git(root, "rev-parse", "--git-path", "info/grafts").decode().strip())
    if not graft_path.is_absolute():
        graft_path = root / graft_path
    if graft_path.exists() and graft_path.stat().st_size:
        _fail("Git grafts are forbidden")
    attributes_path = Path(
        _git(root, "rev-parse", "--git-path", "info/attributes").decode().strip()
    )
    if not attributes_path.is_absolute():
        attributes_path = root / attributes_path
    if attributes_path.exists() and attributes_path.stat().st_size:
        _fail("Git info attributes are forbidden")
    protected_ref = arguments.protected_ref
    if (
        re.fullmatch(r"refs/remotes/origin/[A-Za-z0-9][A-Za-z0-9._/-]*", protected_ref)
        is None
        or ".." in protected_ref
    ):
        _fail("protected default ref is malformed")
    protected_commit = _git(
        root,
        "rev-parse",
        "--verify",
        f"{protected_ref}^{{commit}}",
    ).decode().strip()
    if COMMIT_RE.fullmatch(protected_commit) is None:
        _fail("protected default ref does not resolve to a commit")
    if _git_run(root, "merge-base", "--is-ancestor", "HEAD", protected_ref).returncode != 0:
        _fail("tagged release-ledger commit is not reachable from the protected default ref")
    parents = _git(root, "rev-list", "--parents", "-n", "1", "HEAD").decode().split()
    if len(parents) != 2 or parents[1] != source_commit:
        _fail("tagged release ledger must be the sole child of its artifact source")
    observed_tree = _git(root, "rev-parse", f"{source_commit}^{{tree}}").decode().strip()
    if observed_tree != source_tree:
        _fail("artifact-source tree differs")
    changed = _git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--name-status",
        "--no-renames",
        source_commit,
        "HEAD",
        "--",
    ).decode().splitlines()
    if changed != [f"A\t{ledger_path.as_posix()}"]:
        _fail("release-ledger commit must add exactly the ledger path")
    tree_row = _git(root, "ls-tree", "HEAD", "--", ledger_path.as_posix()).decode().split()
    if len(tree_row) < 4 or tree_row[0] != "100644" or tree_row[1] != "blob":
        _fail("release ledger must be a regular Git blob")

    expected_names = list(arguments.artifact)
    if len(expected_names) != 2 or len(set(expected_names)) != 2:
        _fail("exactly two distinct expected artifacts are required")
    rows = ledger["artifacts"]
    if type(rows) is not list or len(rows) != len(expected_names):
        _fail("release artifact rows differ")
    artifacts: dict[str, tuple[int, str]] = {}
    for index, value in enumerate(rows):
        row = _exact_keys(value, {"bytes", "filename", "sha256"}, f"artifact row {index}")
        filename = row["filename"]
        byte_count = row["bytes"]
        digest = row["sha256"]
        if type(filename) is not str or Path(filename).name != filename:
            _fail("artifact filename is unsafe")
        if type(byte_count) is not int or type(byte_count) is bool or byte_count <= 0:
            _fail("artifact byte count is invalid")
        if type(digest) is not str or SHA256_RE.fullmatch(digest) is None:
            _fail("artifact SHA-256 is malformed")
        if filename in artifacts:
            _fail("artifact filename is duplicated")
        artifacts[filename] = (byte_count, digest)
    if list(artifacts) != sorted(artifacts) or set(artifacts) != set(expected_names):
        _fail("release ledger does not bind the exact ordered artifact set")

    assets = Path(arguments.assets).resolve()
    if not assets.is_dir() or assets.is_symlink():
        _fail("release asset directory is invalid")
    entries = list(assets.iterdir())
    if any(not path.is_file() or path.is_symlink() for path in entries):
        _fail("release assets must be regular non-symlink files")
    if {path.name for path in entries} != set(artifacts) | {arguments.checksum_name}:
        _fail("downloaded release artifact set is not closed")
    for filename, (byte_count, digest) in artifacts.items():
        path = assets / filename
        raw = path.read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest().upper() != digest:
            _fail(f"release artifact differs from committed authority: {filename}")

    expected_checksums = "".join(
        f"{artifacts[name][1].lower()}  {name}\n" for name in sorted(artifacts)
    ).encode("ascii")
    checksum = assets / arguments.checksum_name
    if checksum.read_bytes() != expected_checksums:
        _fail("SHA256SUMS differs from the committed release ledger")

    wheel_names = [name for name in artifacts if name.endswith(".whl")]
    sdist_names = [name for name in artifacts if name.endswith(".tar.gz")]
    if len(wheel_names) != 1 or len(sdist_names) != 1:
        _fail("release must contain exactly one wheel and one sdist")
    _verify_wheel(assets / wheel_names[0], arguments.distribution, arguments.version)
    _verify_sdist(assets / sdist_names[0], arguments.distribution, arguments.version)

    output = Path(arguments.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    for filename in sorted(artifacts):
        target = output / filename
        with target.open("xb") as stream:
            stream.write((assets / filename).read_bytes())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--protected-ref", required=True)
    parser.add_argument("--expected-terminal", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifact", action="append", required=True)
    parser.add_argument("--checksum-name", default="SHA256SUMS")
    return parser


def main(argv: list[str] | None = None) -> int:
    verify(_parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
