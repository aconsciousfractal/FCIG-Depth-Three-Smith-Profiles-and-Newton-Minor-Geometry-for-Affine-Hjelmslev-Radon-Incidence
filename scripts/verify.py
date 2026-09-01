#!/usr/bin/env python3
"""One-command integrity and exact-arithmetic verification entry point."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from check_manifest import ROOT, check_manifest
from check_release import check_release


COMPANION = ROOT / "companion" / "affine_hjelmslev_radon_depth3.py"
EXPECTED_RECEIPT_SHA256 = (
    "2A84A972EF704F0F56124AACB4E40C69CBAD802B7876A133AB81EC7C5ABF94A7"
)


def _load_companion():
    spec = importlib.util.spec_from_file_location("affine_incidence_companion", COMPANION)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load standalone companion")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _check_bounded_receipt(
    relative: str, *, expected_schema: str, result_name: str,
) -> str:
    receipt_path = ROOT / "companion" / relative
    directory = receipt_path.parent
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != expected_schema or receipt.get("status") != "PASS":
        raise AssertionError(f"bounded receipt header drift: {relative}")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict) or result_name not in artifacts:
        raise AssertionError(f"bounded artifact census drift: {relative}")
    for name, identity in artifacts.items():
        if Path(name).name != name or not isinstance(identity, dict):
            raise AssertionError(f"unsafe bounded artifact name: {name}")
        path = directory / name
        if not path.is_file():
            raise AssertionError(f"missing bounded artifact: {name}")
        if path.stat().st_size != identity.get("bytes"):
            raise AssertionError(f"bounded artifact size drift: {name}")
        if _sha256(path) != identity.get("sha256"):
            raise AssertionError(f"bounded artifact digest drift: {name}")
    result_hash = artifacts[result_name]["sha256"]
    executions = receipt.get("executions")
    if not isinstance(executions, dict) or set(executions) != {"normal", "optimized"}:
        raise AssertionError(f"bounded execution census drift: {relative}")
    if any(
        executions[lane].get("result_sha256") != result_hash
        for lane in ("normal", "optimized")
    ):
        raise AssertionError(f"bounded execution identity drift: {relative}")
    return result_hash


def main() -> int:
    manifest = check_manifest()
    release = check_release()
    bounded_hashes = {
        "cross_chart_p3": _check_bounded_receipt(
            "cross_chart_p3/VERIFICATION_RECEIPT.json",
            expected_schema="fcig.depth3.cross-chart-p3-receipt.v1",
            result_name="RESULT.json",
        ),
        "epsilon1_p2": _check_bounded_receipt(
            "epsilon1_p2/VERIFICATION_RECEIPT.json",
            expected_schema="fcig.depth3.epsilon1-p2-receipt.v1",
            result_name="RESULT.json",
        ),
        "o1_exceptional": _check_bounded_receipt(
            "exceptional_profiles/O1_VERIFICATION_RECEIPT.json",
            expected_schema="fcig.depth3.o1-exceptional-receipt.v1",
            result_name="O1_RESULT.json",
        ),
    }
    receipt = _load_companion().verify()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
    if digest != EXPECTED_RECEIPT_SHA256:
        raise AssertionError(f"companion receipt drift: {digest}")
    if manifest["source_files"] != release["source_files"]:
        raise AssertionError("manifest/release source count drift")
    print(canonical)
    print(f"receipt_sha256={digest}")
    print("bounded_receipts=" + json.dumps(bounded_hashes, sort_keys=True))
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
