#!/usr/bin/env python3
"""Exact full-matrix certificate for epsilon_1(2,3).

This bounded calculation implements Definition 4.1 of the paper at p=2.
It constructs the first-chart matrix A and the swapped-chart matrix AS from
the cyclotomic relation Phi_8(Z)=Z^4+1.  No Smith-profile multiplicity is an
input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


P = 2
N = 8
N0 = 4
E = 4
SOURCE_DIMENSION = E * N


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest().upper()


def closed_cyclotomic_remainder(exponent: int) -> list[int]:
    """Coefficient vector of Z^exponent modulo (Z^4+1, 2)."""

    require(isinstance(exponent, int) and exponent >= 0, "nonnegative exponent")
    quotient, residue = divmod(exponent, E)
    vector = [0] * E
    vector[residue] = (-1 if quotient % 2 else 1) % P
    return vector


def division_cyclotomic_remainder(exponent: int) -> list[int]:
    """Independent long-division oracle for Z^exponent modulo Z^4+1."""

    require(isinstance(exponent, int) and exponent >= 0, "nonnegative exponent")
    coefficients = [0] * max(exponent + 1, E)
    coefficients[exponent] = 1
    for degree in range(exponent, E - 1, -1):
        leading = coefficients[degree]
        if leading:
            coefficients[degree] -= leading
            coefficients[degree - E] -= leading
    return [coefficients[degree] % P for degree in range(E)]


def remainder(exponent: int, checked: set[int]) -> list[int]:
    closed = closed_cyclotomic_remainder(exponent)
    divided = division_cyclotomic_remainder(exponent)
    require(closed == divided, f"cyclotomic remainder mismatch at {exponent}")
    checked.add(exponent)
    return closed


def build_chart_matrices() -> tuple[list[list[int]], list[list[int]], set[int]]:
    """Build A and AS in the power bases used in the manuscript.

    Columns are X^i Y^j with 0 <= i < e and 0 <= j < N.  Rows are
    (slope, cyclotomic coefficient).  Evaluation gives

        A:  Z^(i+t*j),       AS: Z^(t*i+j).

    Truncation in S is invisible after evaluation at Z because
    (Z-1)^e=0 in the target.
    """

    checked: set[int] = set()
    first_chart: list[list[int]] = []
    swapped_chart: list[list[int]] = []
    for slope in range(N):
        for basis in range(E):
            first_chart.append(
                [
                    remainder(index + slope * power, checked)[basis]
                    for index in range(E)
                    for power in range(N)
                ]
            )
            swapped_chart.append(
                [
                    remainder(slope * index + power, checked)[basis]
                    for index in range(E)
                    for power in range(N)
                ]
            )
    return first_chart, swapped_chart, checked


def rref(matrix: list[list[int]]) -> tuple[list[list[int]], list[int]]:
    require(bool(matrix), "nonempty matrix")
    column_count = len(matrix[0])
    require(column_count > 0, "positive column count")
    require(all(len(row) == column_count for row in matrix), "rectangular matrix")
    work = [[entry % P for entry in row] for row in matrix]
    pivot_row = 0
    pivots: list[int] = []
    for column in range(column_count):
        selected = next(
            (row for row in range(pivot_row, len(work)) if work[row][column]),
            None,
        )
        if selected is None:
            continue
        work[pivot_row], work[selected] = work[selected], work[pivot_row]
        for row in range(len(work)):
            if row != pivot_row and work[row][column]:
                work[row] = [
                    left ^ right for left, right in zip(work[row], work[pivot_row])
                ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(work):
            break
    return work, pivots


def rank_rref(matrix: list[list[int]]) -> int:
    return len(rref(matrix)[1])


def row_mask(row: list[int]) -> int:
    mask = 0
    for column, entry in enumerate(row):
        require(entry in {0, 1}, "binary matrix entry")
        mask |= entry << column
    return mask


def rank_bitset(matrix: list[list[int]]) -> tuple[int, str]:
    """Independent F_2 elimination using integer bitsets."""

    require(bool(matrix), "nonempty bitset matrix")
    basis: dict[int, int] = {}
    transcript: list[list[int]] = []
    for row_index, row in enumerate(matrix):
        value = row_mask(row)
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                transcript.append([row_index, pivot, value])
                break
    return len(basis), compact_sha256(transcript)


def nullspace_basis(matrix: list[list[int]]) -> list[list[int]]:
    reduced, pivots = rref(matrix)
    free_columns = [
        column for column in range(len(matrix[0])) if column not in set(pivots)
    ]
    basis: list[list[int]] = []
    for free in free_columns:
        vector = [0] * len(matrix[0])
        vector[free] = 1
        for row, pivot in enumerate(pivots):
            vector[pivot] = reduced[row][free]
        basis.append(vector)
    for vector in basis:
        require(
            all(sum(left * right for left, right in zip(row, vector)) % P == 0
                for row in matrix),
            "nullspace residual",
        )
    return basis


def restrict_to_kernel(
    matrix: list[list[int]], kernel: list[list[int]],
) -> list[list[int]]:
    return [
        [sum(left * right for left, right in zip(row, vector)) % P
         for vector in kernel]
        for row in matrix
    ]


def independent_row_indices(matrix: list[list[int]]) -> list[int]:
    selected: list[list[int]] = []
    indices: list[int] = []
    current_rank = 0
    for index, row in enumerate(matrix):
        candidate_rank = rank_rref(selected + [row])
        if candidate_rank > current_rank:
            selected.append(row)
            indices.append(index)
            current_rank = candidate_rank
    return indices


def certificate() -> dict[str, object]:
    first_chart, swapped_chart, checked = build_chart_matrices()
    require(len(first_chart) == N * E, "first-chart row count")
    require(len(swapped_chart) == N * E, "swapped-chart row count")
    require(all(len(row) == SOURCE_DIMENSION for row in first_chart), "A shape")
    require(all(len(row) == SOURCE_DIMENSION for row in swapped_chart), "AS shape")

    nonunit_rows = [
        swapped_chart[slope * E + basis]
        for slope in range(0, N, P)
        for basis in range(E)
    ]
    unit_rows = [
        swapped_chart[slope * E + basis]
        for slope in range(1, N, P)
        for basis in range(E)
    ]
    stacked = first_chart + swapped_chart

    rref_ranks = {
        "first_chart": rank_rref(first_chart),
        "first_plus_nonunit_rows": rank_rref(first_chart + nonunit_rows),
        "first_plus_unit_rows": rank_rref(first_chart + unit_rows),
        "swapped_chart": rank_rref(swapped_chart),
        "two_chart": rank_rref(stacked),
    }
    bitset_first_rank, bitset_first_transcript = rank_bitset(first_chart)
    bitset_two_rank, bitset_two_transcript = rank_bitset(stacked)
    bitset_ranks = {
        "first_chart": bitset_first_rank,
        "two_chart": bitset_two_rank,
    }

    kernel = nullspace_basis(first_chart)
    swapped_on_kernel = restrict_to_kernel(swapped_chart, kernel)
    nonunit_on_kernel = restrict_to_kernel(nonunit_rows, kernel)
    unit_on_kernel = restrict_to_kernel(unit_rows, kernel)
    restriction_ranks = {
        "AS_on_kernel_A": rank_rref(swapped_on_kernel),
        "nonunit_AS_on_kernel_A": rank_rref(nonunit_on_kernel),
        "unit_AS_on_kernel_A": rank_rref(unit_on_kernel),
    }

    first_witness_indices = independent_row_indices(first_chart)
    first_witness = [first_chart[index] for index in first_witness_indices]
    cross_witness_index = next(
        index
        for index, row in enumerate(swapped_chart)
        if rank_rref(first_witness + [row]) == len(first_witness) + 1
    )
    two_chart_witness = first_witness + [swapped_chart[cross_witness_index]]
    witness_pivots = rref(two_chart_witness)[1]
    witness_minor = [
        [row[column] for column in witness_pivots] for row in two_chart_witness
    ]
    witness_minor_rank = rank_rref(witness_minor)

    epsilon_rank_difference = rref_ranks["two_chart"] - rref_ranks["first_chart"]
    acceptance = {
        "cyclotomic_oracles_agree": bool(checked),
        "first_chart_rank_8": rref_ranks["first_chart"] == 8,
        "independent_rank_lanes_agree": rref_ranks["first_chart"]
        == bitset_ranks["first_chart"]
        and rref_ranks["two_chart"] == bitset_ranks["two_chart"],
        "kernel_dimension_24": len(kernel) == SOURCE_DIMENSION - 8,
        "nonunit_rows_capture_increment": rref_ranks["first_plus_nonunit_rows"] == 9,
        "rank_difference_1": epsilon_rank_difference == 1,
        "restriction_identity": restriction_ranks["AS_on_kernel_A"]
        == epsilon_rank_difference,
        "two_chart_rank_9": rref_ranks["two_chart"] == 9,
        "unit_rows_add_no_rank": rref_ranks["first_plus_unit_rows"] == 8,
        "witness_minor_is_invertible": witness_minor_rank == 9,
    }
    require(all(acceptance.values()), "epsilon_1(2,3) certificate failed")

    return {
        "acceptance": acceptance,
        "definition": "epsilon_1(2,3)=rank_F2([A;AS])-rank_F2(A)",
        "epsilon_1": epsilon_rank_difference,
        "matrices": {
            "AS": {
                "formula": "[Z^b] Z^(t*i+j)",
                "sha256": compact_sha256(swapped_chart),
                "shape": [len(swapped_chart), SOURCE_DIMENSION],
            },
            "A": {
                "formula": "[Z^b] Z^(i+t*j)",
                "sha256": compact_sha256(first_chart),
                "shape": [len(first_chart), SOURCE_DIMENSION],
            },
            "nonunit_AS_rows": {
                "sha256": compact_sha256(nonunit_rows),
                "shape": [len(nonunit_rows), SOURCE_DIMENSION],
            },
            "stacked": {
                "sha256": compact_sha256(stacked),
                "shape": [len(stacked), SOURCE_DIMENSION],
            },
        },
        "parameters": {
            "cyclotomic_relation": "Phi_8(Z)=Z^4+1",
            "e": E,
            "n": 3,
            "p": P,
            "q": N,
            "q0": N0,
            "source_dimension": SOURCE_DIMENSION,
        },
        "rank_lanes": {
            "bitset": {
                **bitset_ranks,
                "first_transcript_sha256": bitset_first_transcript,
                "two_chart_transcript_sha256": bitset_two_transcript,
            },
            "rref": rref_ranks,
        },
        "remainder_oracles": {
            "exponents_checked": len(checked),
            "maximum_exponent": max(checked),
            "sha256": compact_sha256(sorted(checked)),
        },
        "restriction_to_kernel": {
            "kernel_basis_sha256": compact_sha256(kernel),
            "kernel_dimension": len(kernel),
            "ranks": restriction_ranks,
            "restricted_matrix_sha256": compact_sha256(swapped_on_kernel),
        },
        "role": "bounded exact p=2 obstruction certificate; no prime interpolation",
        "schema": "fcig.depth3.epsilon1-p2-result.v1",
        "status": "PASS",
        "witness": {
            "cross_row_index": cross_witness_index,
            "first_chart_row_indices": first_witness_indices,
            "minor_rank": witness_minor_rank,
            "minor_sha256": compact_sha256(witness_minor),
            "pivot_columns": witness_pivots,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = canonical_bytes(certificate())
    if args.output is not None:
        args.output.write_bytes(payload)
    # Binary stdout avoids Windows' text-mode LF -> CRLF translation, so the
    # emitted certificate is byte-identical to RESULT.json on every platform.
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
