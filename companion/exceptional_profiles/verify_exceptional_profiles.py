#!/usr/bin/env python3
"""Replay the exact exceptional p=2,3 depth-three Smith certificates."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    require(isinstance(value, dict), f"JSON object required: {path.name}")
    return value


def load_engine():
    path = ROOT / "depth3_smith.py"
    spec = importlib.util.spec_from_file_location("fcig_d3_exceptional_engine", path)
    require(spec is not None and spec.loader is not None, "cannot load Smith engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def run() -> dict[str, object]:
    controls = load_json(ROOT / "INPUT.json")
    expected = load_json(ROOT / "EXPECTED.json")
    require(controls.get("schema") == "fcig.depth3.exceptional-input.v1", "input schema")
    require(expected.get("schema") == "fcig.depth3.exceptional-expected.v1", "expected schema")
    require(
        controls.get("algorithms")
        == ["local_smith_minpivot", "bockstein_layer_peeling"],
        "algorithm inventory",
    )
    engine = load_engine()
    observed: dict[str, object] = {}
    cases = controls.get("cases")
    require(isinstance(cases, list) and len(cases) == 2, "case inventory")
    expected_cases = expected.get("cases")
    require(isinstance(expected_cases, dict), "expected cases")

    for case in cases:
        require(isinstance(case, dict), "case object")
        p = int(case["prime"])
        depth = int(case["depth"])
        cutoff = int(case["cutoff"])
        require((p, depth, cutoff) in {(2, 3, 7), (3, 3, 7)}, "undeclared case")
        matrix = engine.incidence_matrix(p, depth)
        minimum = engine.local_smith_minpivot(matrix, p, cutoff)
        layered = engine.bockstein_layer_peeling(matrix, p, cutoff)
        require(minimum.valuations == layered.valuations, f"lane disagreement p={p}")
        profile = {str(k): int(v) for k, v in minimum.profile.items()}
        weighted = sum(int(k) * int(v) for k, v in profile.items())
        require(sum(profile.values()) == p ** (2 * depth), f"rank identity p={p}")
        require(
            weighted == engine.theoretical_order_exponent(p, depth),
            f"weighted order p={p}",
        )
        row = {
            "bockstein_transcript_sha256": layered.transcript_sha256.upper(),
            "matrix_sha256": engine.canonical_matrix_sha256(matrix).upper(),
            "minpivot_transcript_sha256": minimum.transcript_sha256.upper(),
            "profile": profile,
            "shape": [int(x) for x in matrix.shape],
            "weighted_order_exponent": weighted,
        }
        require(row == expected_cases.get(str(p)), f"expected certificate p={p}")
        observed[str(p)] = row

    result = {
        "cases": observed,
        "claim_boundary": "bounded exact certificates for p=2,3 only",
        "schema": "fcig.depth3.exceptional-result.v1",
        "status": "PASS",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    payload = canonical_bytes(result)
    if args.output is not None:
        args.output.write_bytes(payload)
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
