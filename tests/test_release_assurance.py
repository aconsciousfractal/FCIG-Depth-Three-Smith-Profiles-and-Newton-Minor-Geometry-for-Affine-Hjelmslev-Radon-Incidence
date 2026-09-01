from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

import pytest
from pypdf import PdfReader

from test_depth3_smith_profiles import (
    PDF,
    ROOT,
    _copy_candidate,
    _public_git_environment,
)


SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from check_release import (  # noqa: E402
    _check_terminal_pdf_bytes,
    _check_tex_source,
    _scan_python_source,
)


def _git_executable() -> str:
    executable = shutil.which("git")
    assert executable is not None
    return str(Path(executable).resolve(strict=True))


def _clean_git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(_public_git_environment())
    return environment


def _run_target(
    root: Path,
    target: str,
    arguments: list[str] | None = None,
    *,
    injected_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if injected_environment:
        environment.update(injected_environment)
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(root / "scripts" / "runtime_bootstrap.py"),
        "--git-executable",
        _git_executable(),
        "--target",
        str(root / target),
        "--",
        *(arguments or []),
    ]
    return subprocess.run(
        command,
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _git(root: Path, *arguments: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        [_git_executable(), *arguments],
        cwd=root,
        env=_clean_git_environment(),
        input=input_text,
        stdin=None if input_text is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _make_lure(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    (path / "lure.txt").write_text("not the candidate\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-m", "Publish paper and reproducibility companion")
    return path


def test_release_checker_accepts_a_clean_checkout(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RELEASE PASS" in result.stdout


def test_release_checker_accepts_remotes_and_tags(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    _git(candidate, "remote", "add", "origin", "https://example.com/repository")
    _git(candidate, "tag", "v1.0.0")
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_release_checker_accepts_a_linear_successor(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    tree = _git(candidate, "rev-parse", "HEAD^{tree}")
    successor = _git(
        candidate,
        "commit-tree",
        tree,
        "-p",
        "HEAD",
        "-m",
        "Synthetic linear successor",
    )
    _git(candidate, "reset", "--hard", successor)
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_release_checker_accepts_a_merge_commit(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    tree = _git(candidate, "rev-parse", "HEAD^{tree}")
    root = _git(candidate, "rev-parse", "HEAD")
    side = _git(
        candidate,
        "commit-tree",
        tree,
        "-p",
        root,
        "-m",
        "Independent documentation follow-up",
    )
    main = _git(
        candidate,
        "commit-tree",
        tree,
        "-p",
        root,
        "-m",
        "Main documentation follow-up",
    )
    merged = _git(
        candidate,
        "commit-tree",
        tree,
        "-p",
        main,
        "-p",
        side,
        "-m",
        "Merge documentation follow-up",
    )
    _git(candidate, "reset", "--hard", merged)
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_all_ambient_git_redirections_are_neutralized(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path / "expected")
    lure = _make_lure(tmp_path / "lure")
    assert _git(candidate, "rev-parse", "HEAD") != _git(lure, "rev-parse", "HEAD")
    injected = {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(lure / ".git" / "objects"),
        "GIT_COMMON_DIR": str(lure / ".git"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.bare",
        "GIT_CONFIG_PARAMETERS": "'core.bare=true'",
        "GIT_CONFIG_VALUE_0": "true",
        "GIT_DIR": str(lure / ".git"),
        "GIT_INDEX_FILE": str(lure / ".git" / "index"),
        "GIT_NAMESPACE": "refs/namespaces/lure",
        "GIT_OBJECT_DIRECTORY": str(lure / ".git" / "objects"),
        "GIT_REPLACE_REF_BASE": "refs/lure-replacements",
        "GIT_WORK_TREE": str(lure),
    }
    result = _run_target(
        candidate,
        "scripts/check_release.py",
        injected_environment=injected,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RELEASE PASS" in result.stdout


def test_local_replace_ref_is_rejected(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    tree = _git(candidate, "rev-parse", "HEAD^{tree}")
    replacement = _git(
        candidate, "commit-tree", tree, "-m", "Synthetic replacement",
    )
    _git(candidate, "replace", "HEAD", replacement)
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode != 0
    assert "replacement refs are forbidden" in result.stderr


@pytest.mark.parametrize("administrative_path", ["grafts", "alternates"])
def test_local_git_administrative_redirect_is_rejected(
    tmp_path: Path, administrative_path: str,
) -> None:
    candidate = _copy_candidate(tmp_path)
    if administrative_path == "grafts":
        path = candidate / ".git" / "info" / "grafts"
        payload = _git(candidate, "rev-parse", "HEAD") + "\n"
    else:
        lure = _make_lure(tmp_path / "lure")
        path = candidate / ".git" / "objects" / "info" / "alternates"
        payload = str(lure / ".git" / "objects") + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode != 0
    assert administrative_path in result.stderr


def _last_startxref(payload: bytes) -> int:
    rows = re.findall(rb"startxref\s+([0-9]+)\s+%%EOF", payload)
    assert len(rows) == 1
    return int(rows[0])


def _xref_entry(kind: int, field_two: int, field_three: int) -> bytes:
    return (
        bytes([kind])
        + field_two.to_bytes(4, "big")
        + field_three.to_bytes(2, "big")
    )


def _xref_stream_object(
    identifier: int,
    *,
    first_identifier: int,
    entries: bytes,
    size: int,
    previous: int,
    root_identifier: int,
    root_generation: int,
    count: int,
) -> bytes:
    header = (
        f"{identifier} 0 obj\n"
        f"<< /Type /XRef /Size {size} "
        f"/Root {root_identifier} {root_generation} R "
        f"/Prev {previous} /W [1 4 2] "
        f"/Index [{first_identifier} {count}] /Length {len(entries)} >>\n"
        "stream\n"
    ).encode("ascii")
    return header + entries + b"\nendstream\nendobj\n"


def _write_incremental_xref_stream(path: Path, *, object_stream: bool) -> None:
    original = path.read_bytes()
    previous = _last_startxref(original)
    reader = PdfReader(str(path), strict=True)
    size = int(reader.trailer["/Size"])
    root = reader.trailer.raw_get("/Root")
    assert hasattr(root, "idnum") and hasattr(root, "generation")
    base = original.replace(b"%%EOF", b"     ", 1)

    hidden_identifier = size
    first_offset = len(base)
    if object_stream:
        object_stream_identifier = size + 1
        xref_identifier = size + 2
        object_header = f"{hidden_identifier} 0 ".encode("ascii")
        hidden_object = b"<< /Type /Filespec /F (detached.bin) >>"
        compressed = zlib.compress(object_header + hidden_object)
        object_stream_bytes = (
            f"{object_stream_identifier} 0 obj\n"
            f"<< /Type /ObjStm /N 1 /First {len(object_header)} "
            f"/Length {len(compressed)} /Filter /FlateDecode >>\n"
            "stream\n"
        ).encode("ascii") + compressed + b"\nendstream\nendobj\n"
        xref_offset = first_offset + len(object_stream_bytes)
        entries = b"".join(
            (
                _xref_entry(2, object_stream_identifier, 0),
                _xref_entry(1, first_offset, 0),
                _xref_entry(1, xref_offset, 0),
            )
        )
        xref = _xref_stream_object(
            xref_identifier,
            first_identifier=hidden_identifier,
            entries=entries,
            size=xref_identifier + 1,
            previous=previous,
            root_identifier=root.idnum,
            root_generation=root.generation,
            count=3,
        )
        appendix = object_stream_bytes + xref
    else:
        xref_identifier = size + 1
        hidden_payload = (
            b"synthetic absolute path "
            + bytes([88, 58, 92])
            + b"Example\\Repository\\payload.bin"
        )
        compressed = zlib.compress(hidden_payload)
        hidden = (
            f"{hidden_identifier} 0 obj\n"
            f"<< /Length {len(compressed)} /Filter /FlateDecode >>\n"
            "stream\n"
        ).encode("ascii") + compressed + b"\nendstream\nendobj\n"
        xref_offset = first_offset + len(hidden)
        entries = b"".join(
            (
                _xref_entry(1, first_offset, 0),
                _xref_entry(1, xref_offset, 0),
            )
        )
        xref = _xref_stream_object(
            xref_identifier,
            first_identifier=hidden_identifier,
            entries=entries,
            size=xref_identifier + 1,
            previous=previous,
            root_identifier=root.idnum,
            root_generation=root.generation,
            count=2,
        )
        appendix = hidden + xref
    final = (
        base
        + appendix
        + f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(final)


def test_non_whitespace_after_terminal_eof_is_rejected(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    pdf = candidate / PDF.relative_to(ROOT)
    pdf.write_bytes(
        pdf.read_bytes()
        + bytes([88, 58, 92])
        + b"Example\\Repository\\payload.bin"
    )
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode != 0
    assert "non-whitespace bytes after terminal EOF" in result.stderr


def test_printable_run_in_compressed_raw_bytes_is_not_treated_as_text() -> None:
    payload = (
        b"%PDF-1.7\n1 0 obj\n<< /Length 9 >>\nstream\n"
        b".mYXT\\U9#\nendstream\nendobj\n%%EOF\n"
    )
    _check_terminal_pdf_bytes(payload)


def test_unreachable_xref_stream_object_is_scanned(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    pdf = candidate / PDF.relative_to(ROOT)
    _write_incremental_xref_stream(pdf, object_stream=False)
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode != 0
    assert "decoded PDF stream" in result.stderr


def test_compressed_object_stream_member_is_scanned(tmp_path: Path) -> None:
    candidate = _copy_candidate(tmp_path)
    pdf = candidate / PDF.relative_to(ROOT)
    _write_incremental_xref_stream(pdf, object_stream=True)
    result = _run_target(candidate, "scripts/check_release.py")
    assert result.returncode != 0
    assert any(
        token in result.stderr
        for token in ("forbidden PDF object type", "forbidden PDF raw marker")
    ), result.stderr


@pytest.mark.parametrize(
    ("source", "primitive"),
    [
        ("value = bytes.fromhex('50313233')", "fromhex"),
        ("value = data.decode('ascii')", "decode"),
        ("value = base64.b64decode('UDEyMw==')", "b64decode"),
        ("value = chr(80)", "chr"),
        ("value = eval('1')", "eval"),
        ("exec('value=1')", "exec"),
        ("value = compile('1', 'x', 'eval')", "compile"),
    ],
)
def test_restricted_verifier_language_rejects_dynamic_reconstruction(
    source: str, primitive: str,
) -> None:
    with pytest.raises(AssertionError, match=primitive):
        _scan_python_source(
            source, "scripts/synthetic_verifier.py", restricted_language=True,
        )


def test_restricted_verifier_language_folds_concatenated_token() -> None:
    for source in ("value = 'P' + '123'", "value = f'P{123}'"):
        with pytest.raises(AssertionError, match="private workspace code"):
            _scan_python_source(
                source, "scripts/synthetic_verifier.py", restricted_language=True,
            )


@pytest.mark.parametrize(
    ("phrase", "error"),
    [
        ("an answer-blind theorem consequence", "answer-blind provenance"),
        ("a separately frozen certificate", "separately-frozen provenance"),
        (
            "the remaining five factorizations are listed in the verification receipt",
            "factorization receipt claim",
        ),
    ],
)
def test_unverifiable_manuscript_provenance_is_rejected(
    tmp_path: Path, phrase: str, error: str,
) -> None:
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(phrase + "\n", encoding="utf-8")
    with pytest.raises(AssertionError, match=error):
        _check_tex_source(tmp_path)
