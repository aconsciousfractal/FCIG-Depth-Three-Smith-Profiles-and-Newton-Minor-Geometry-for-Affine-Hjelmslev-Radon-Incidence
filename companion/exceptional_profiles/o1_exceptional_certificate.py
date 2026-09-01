#!/usr/bin/env python3
"""Exact finite first-transfer certificates for p=2 and p=3.

The first transfer congruence is equivalent to one depth-two point-fibre
indicator belonging to the depth-three modular affine-line code.  Translation
invariance then handles every fibre.  The two lanes below construct a line
combination and independently test orthogonality to the full dual nullspace.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def load_incidence_engine():
    path = ROOT / "depth3_smith.py"
    spec = importlib.util.spec_from_file_location("fcig_d3_o1_engine", path)
    require(spec is not None and spec.loader is not None, "cannot load incidence engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def canonical_array_sha256(array: np.ndarray, prime: int) -> str:
    reduced = np.ascontiguousarray(np.asarray(array, dtype=np.int64) % prime)
    header = json.dumps(
        {"dtype": "int64", "modulus": prime, "shape": list(reduced.shape)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(header + b"\n" + reduced.tobytes(order="C")).hexdigest().upper()


def modular_rref(matrix: np.ndarray, prime: int) -> tuple[np.ndarray, tuple[int, ...]]:
    work = (np.asarray(matrix, dtype=np.int64) % prime).copy()
    require(work.ndim == 2, "matrix required")
    rows, columns = work.shape
    pivot_row = 0
    pivots: list[int] = []
    for column in range(columns):
        candidates = np.flatnonzero(work[pivot_row:, column])
        if not candidates.size:
            continue
        selected = pivot_row + int(candidates[0])
        if selected != pivot_row:
            work[[pivot_row, selected], :] = work[[selected, pivot_row], :]
        inverse = pow(int(work[pivot_row, column]), -1, prime)
        work[pivot_row, :] = work[pivot_row, :] * inverse % prime
        other_rows = np.flatnonzero(work[:, column])
        other_rows = other_rows[other_rows != pivot_row]
        if other_rows.size:
            factors = work[other_rows, column].copy()
            work[other_rows, :] = (
                work[other_rows, :] - factors[:, None] * work[pivot_row, :]
            ) % prime
        pivots.append(column)
        pivot_row += 1
        if pivot_row == rows:
            break
    return work, tuple(pivots)


def solve(matrix: np.ndarray, target: np.ndarray, prime: int) -> tuple[np.ndarray, dict[str, object]]:
    rows, columns = matrix.shape
    require(target.shape == (rows,), "target shape mismatch")
    augmented = np.concatenate((matrix % prime, (target % prime)[:, None]), axis=1)
    reduced, all_pivots = modular_rref(augmented, prime)
    pivots = tuple(column for column in all_pivots if column < columns)
    inconsistent = np.all(reduced[:, :columns] == 0, axis=1) & (reduced[:, columns] != 0)
    require(not np.any(inconsistent), "line-code system is inconsistent")
    solution = np.zeros(columns, dtype=np.int64)
    for row, pivot in enumerate(pivots):
        solution[pivot] = reduced[row, columns] % prime
    residual = (matrix @ solution - target) % prime
    require(not np.any(residual), "line-code solution does not verify")
    return solution, {
        "augmented_rref_sha256": canonical_array_sha256(reduced, prime),
        "rank": len(pivots),
    }


def nullspace(matrix: np.ndarray, prime: int) -> tuple[np.ndarray, dict[str, object]]:
    reduced, pivots = modular_rref(matrix, prime)
    column_count = matrix.shape[1]
    pivot_set = set(pivots)
    free = tuple(column for column in range(column_count) if column not in pivot_set)
    basis = np.zeros((column_count, len(free)), dtype=np.int64)
    pivot_array = np.asarray(pivots, dtype=np.int64)
    for index, free_column in enumerate(free):
        basis[free_column, index] = 1
        if pivots:
            basis[pivot_array, index] = (-reduced[: len(pivots), free_column]) % prime
    require(not np.any((matrix @ basis) % prime), "dual nullspace construction failed")
    return basis, {
        "basis_sha256": canonical_array_sha256(basis, prime),
        "nullity": len(free),
        "rank": len(pivots),
        "rref_sha256": canonical_array_sha256(reduced, prime),
    }


def zero_fibre_indicator(prime: int) -> np.ndarray:
    modulus = prime**3
    coarse = prime**2
    first = np.repeat(np.arange(modulus, dtype=np.int64), modulus)
    second = np.tile(np.arange(modulus, dtype=np.int64), modulus)
    return ((first % coarse == 0) & (second % coarse == 0)).astype(np.int64)


def case_certificate(prime: int) -> dict[str, object]:
    require(prime in {2, 3}, "certificate scope is exactly p=2,3")
    engine = load_incidence_engine()
    matrix = engine.incidence_matrix(prime, 3)
    target = zero_fibre_indicator(prime)
    solution, primal = solve(matrix, target, prime)

    dual_basis, dual = nullspace(matrix.T, prime)
    pairings = target @ dual_basis % prime
    require(not np.any(pairings), "target fails dual nullspace orthogonality")

    nonzero_columns = np.flatnonzero(solution % prime)
    require(bool(nonzero_columns.size), "empty primal certificate")
    deleted = solution.copy()
    deleted_column = int(nonzero_columns[0])
    deleted[deleted_column] = 0
    deletion_residual = (matrix @ deleted - target) % prime
    require(bool(np.any(deletion_residual)), "deleted-line mutation escaped")

    outside_point = int(np.flatnonzero(target == 0)[0])
    changed_target = target.copy()
    changed_target[outside_point] = (changed_target[outside_point] + 1) % prime
    changed_pairings = changed_target @ dual_basis % prime
    require(bool(np.any(changed_pairings)), "changed-target mutation escaped")

    return {
        "dual_lane": {
            **dual,
            "nonzero_pairings": int(np.count_nonzero(pairings)),
            "pairing_sha256": canonical_array_sha256(pairings, prime),
        },
        "hostile_mutations": {
            "deleted_line": {
                "column": deleted_column,
                "residual_hamming_weight": int(np.count_nonzero(deletion_residual)),
                "residual_sha256": canonical_array_sha256(deletion_residual, prime),
            },
            "flipped_point": {
                "nonzero_dual_pairings": int(np.count_nonzero(changed_pairings)),
                "pairing_sha256": canonical_array_sha256(changed_pairings, prime),
                "point": outside_point,
            },
        },
        "matrix": {
            "rank": primal["rank"],
            "sha256": canonical_array_sha256(matrix, prime),
            "shape": list(matrix.shape),
        },
        "prime": prime,
        "primal_lane": {
            **primal,
            "residual_hamming_weight": 0,
            "solution_sha256": canonical_array_sha256(solution, prime),
            "support_size": int(nonzero_columns.size),
        },
        "status": "PASS",
        "target": {
            "point_count": int(np.count_nonzero(target)),
            "sha256": canonical_array_sha256(target, prime),
        },
    }


def certificate() -> dict[str, object]:
    return {
        "cases": {str(prime): case_certificate(prime) for prime in (2, 3)},
        "claim": "one point-fibre indicator belongs to the depth-three modular line code",
        "scope": "exact exceptional first-transfer congruence for p=2,3 only",
        "schema": "fcig.depth3.o1-exceptional-result.v1",
        "status": "PASS",
        "translation": "all point fibres follow from affine translation invariance",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = canonical_bytes(certificate())
    if args.output is not None:
        args.output.write_bytes(payload)
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
