#!/usr/bin/env python3
"""Replay and authenticate the exact epsilon_1(2,3) certificate."""

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
    path = ROOT / "epsilon1_p2_certificate.py"
    spec = importlib.util.spec_from_file_location("fcig_d3_epsilon1_p2", path)
    require(spec is not None and spec.loader is not None, "cannot load certificate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    engine = load_engine()
    result_path = ROOT / "RESULT.json"
    observed = engine.canonical_bytes(engine.certificate())
    require(result_path.read_bytes() == observed, "p=2 epsilon result drift")

    result = json.loads(observed.decode("utf-8"))
    require(result.get("schema") == "fcig.depth3.epsilon1-p2-result.v1", "result schema")
    require(result.get("status") == "PASS", "result status")
    require(result.get("epsilon_1") == 1, "epsilon_1(2,3)")
    ranks = result.get("rank_lanes", {}).get("rref", {})
    require(ranks.get("first_chart") == 8, "first-chart rank")
    require(ranks.get("two_chart") == 9, "two-chart rank")

    receipt = json.loads(
        (ROOT / "VERIFICATION_RECEIPT.json").read_text(encoding="utf-8")
    )
    require(
        receipt.get("schema") == "fcig.depth3.epsilon1-p2-receipt.v1",
        "receipt schema",
    )
    require(receipt.get("status") == "PASS", "receipt status")
    artifacts = receipt.get("artifacts")
    require(isinstance(artifacts, dict), "receipt artifacts")
    require(
        set(artifacts)
        == {"README.md", "RESULT.json", "epsilon1_p2_certificate.py",
            "verify_epsilon1_p2.py"},
        "artifact census",
    )
    for name, identity in artifacts.items():
        require(Path(name).name == name, f"unsafe artifact name: {name}")
        path = ROOT / name
        require(path.is_file(), f"missing artifact: {name}")
        require(path.stat().st_size == identity.get("bytes"), f"artifact size: {name}")
        require(sha256(path) == identity.get("sha256"), f"artifact digest: {name}")

    result_sha = sha256(result_path)
    executions = receipt.get("executions")
    require(isinstance(executions, dict), "execution receipt")
    require(set(executions) == {"normal", "optimized"}, "execution census")
    require(
        all(
            executions[lane].get("result_sha256") == result_sha
            for lane in ("normal", "optimized")
        ),
        "normal/optimized result identity",
    )
    print(json.dumps({"result_sha256": result_sha, "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
