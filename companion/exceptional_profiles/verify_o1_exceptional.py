#!/usr/bin/env python3
"""Replay and authenticate the exceptional first-transfer certificate."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_engine():
    path = ROOT / "o1_exceptional_certificate.py"
    spec = importlib.util.spec_from_file_location("fcig_d3_o1_certificate", path)
    require(spec is not None and spec.loader is not None, "cannot load certificate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    engine = load_engine()
    result_path = ROOT / "O1_RESULT.json"
    observed = engine.canonical_bytes(engine.certificate())
    require(result_path.read_bytes() == observed, "exceptional first-transfer result drift")
    receipt = json.loads((ROOT / "O1_VERIFICATION_RECEIPT.json").read_text(encoding="utf-8"))
    require(receipt.get("schema") == "fcig.depth3.o1-exceptional-receipt.v1", "receipt schema")
    require(receipt.get("status") == "PASS", "receipt status")
    artifacts = receipt.get("artifacts")
    require(isinstance(artifacts, dict), "receipt artifacts")
    for name, identity in artifacts.items():
        path = ROOT / name
        require(path.is_file(), f"missing artifact: {name}")
        require(path.stat().st_size == identity.get("bytes"), f"artifact size: {name}")
        require(sha256(path) == identity.get("sha256"), f"artifact digest: {name}")
    result_sha = sha256(result_path)
    executions = receipt.get("executions")
    require(isinstance(executions, dict), "execution receipt")
    require(
        executions.get("normal", {}).get("result_sha256") == result_sha
        and executions.get("optimized", {}).get("result_sha256") == result_sha,
        "normal/optimized result identity",
    )
    print(json.dumps({"result_sha256": result_sha, "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
