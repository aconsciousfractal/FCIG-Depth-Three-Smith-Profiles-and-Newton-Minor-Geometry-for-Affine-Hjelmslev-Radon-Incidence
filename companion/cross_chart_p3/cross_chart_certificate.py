#!/usr/bin/env python3
"""Independent p=3 cross-chart Newton and divided-carry certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


P = 3
N = 27
N0 = 9
E = 18
LIFT_MODULUS = 9


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def v3(value: int) -> int:
    exponent = 0
    while value and value % P == 0:
        value //= P
        exponent += 1
    return exponent


def beta3(index: int) -> int:
    return sum(P ** v3(value) for value in range(1, index + 1))


def threshold(index: int) -> int:
    return max(E - beta3(index), 0)


def reduced_monomial(exponent: int) -> tuple[tuple[int, int], ...]:
    residue = exponent % N
    if residue < E:
        return ((residue, 1),)
    return ((residue - E, -1), (residue - N0, -1))


def add_term(
    polynomial: dict[tuple[int, int], int],
    key: tuple[int, int],
    value: int,
    modulus: int,
) -> None:
    updated = (polynomial.get(key, 0) + value) % modulus
    if updated:
        polynomial[key] = updated
    else:
        polynomial.pop(key, None)


def multiply_y_minus_xa(
    polynomial: dict[tuple[int, int], int], exponent: int, modulus: int,
) -> dict[tuple[int, int], int]:
    result: dict[tuple[int, int], int] = {}
    for (x_degree, y_degree), coefficient in polynomial.items():
        add_term(result, (x_degree, y_degree + 1), coefficient, modulus)
        for reduced_degree, sign in reduced_monomial(x_degree + exponent):
            add_term(result, (reduced_degree, y_degree), -coefficient * sign, modulus)
    return result


def multiply_x_minus_one(
    polynomial: dict[tuple[int, int], int], modulus: int,
) -> dict[tuple[int, int], int]:
    result: dict[tuple[int, int], int] = {}
    for (x_degree, y_degree), coefficient in polynomial.items():
        for reduced_degree, sign in reduced_monomial(x_degree + 1):
            add_term(result, (reduced_degree, y_degree), coefficient * sign, modulus)
        add_term(result, (x_degree, y_degree), -coefficient, modulus)
    return result


def source_polynomials(
    modulus: int,
) -> dict[tuple[int, int], dict[tuple[int, int], int]]:
    sources: dict[tuple[int, int], dict[tuple[int, int], int]] = {}
    base: dict[tuple[int, int], int] = {(0, 0): 1}
    for index in range(N):
        with_x_power = dict(base)
        for power in range(E):
            if power >= threshold(index):
                sources[(index, power)] = dict(with_x_power)
            with_x_power = multiply_x_minus_one(with_x_power, modulus)
        base = multiply_y_minus_xa(base, index, modulus)
    return sources


def evaluate_source(
    polynomial: dict[tuple[int, int], int],
    x_multiplier: int,
    y_multiplier: int,
    modulus: int,
) -> list[int]:
    result = [0] * E
    for (x_degree, y_degree), coefficient in polynomial.items():
        exponent = x_multiplier * x_degree + y_multiplier * y_degree
        for reduced_degree, sign in reduced_monomial(exponent):
            result[reduced_degree] = (
                result[reduced_degree] + coefficient * sign
            ) % modulus
    return result


def first_chart(
    polynomial: dict[tuple[int, int], int], modulus: int,
) -> list[list[int]]:
    return [evaluate_source(polynomial, 1, slope, modulus) for slope in range(N)]


def cross_chart(
    polynomial: dict[tuple[int, int], int], modulus: int,
) -> list[list[int]]:
    return [evaluate_source(polynomial, P * slope, 1, modulus) for slope in range(N0)]


def rref(matrix: list[list[int]], prime: int) -> tuple[list[list[int]], list[int]]:
    work = [[entry % prime for entry in row] for row in matrix]
    if not work:
        return work, []
    row_count = len(work)
    column_count = len(work[0])
    pivot_row = 0
    pivots: list[int] = []
    for column in range(column_count):
        selected = next(
            (row for row in range(pivot_row, row_count) if work[row][column]),
            None,
        )
        if selected is None:
            continue
        work[pivot_row], work[selected] = work[selected], work[pivot_row]
        inverse = pow(work[pivot_row][column], -1, prime)
        work[pivot_row] = [entry * inverse % prime for entry in work[pivot_row]]
        for row in range(row_count):
            if row == pivot_row:
                continue
            factor = work[row][column]
            if factor:
                work[row] = [
                    (left - factor * right) % prime
                    for left, right in zip(work[row], work[pivot_row])
                ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == row_count:
            break
    return work, pivots


def rank(matrix: list[list[int]], prime: int) -> int:
    return len(rref(matrix, prime)[1])


def row_basis(matrix: list[list[int]], prime: int) -> list[list[int]]:
    reduced, pivots = rref(matrix, prime)
    return reduced[: len(pivots)]


def row_space_contains(basis: list[list[int]], vector: list[int], prime: int) -> bool:
    if not basis:
        return not any(entry % prime for entry in vector)
    return rank(basis + [[entry % prime for entry in vector]], prime) == len(basis)


def line_rows(*, transposed: bool = False) -> list[list[int]]:
    rows: list[list[int]] = []
    for lift in range(P):
        normal_first, normal_second = ((1, P * lift) if transposed else (P * lift, 1))
        for constant in range(N0):
            rows.append([
                int((normal_first * first + normal_second * second - constant) % N0 == 0)
                for first in range(N0)
                for second in range(N0)
            ])
    return rows


def annihilator_membership(point_vector: list[int]) -> bool:
    binomial = ((1,), (1, 1), (1, 2, 1), (1, 3, 3, 1))

    def value(first: int, second: int) -> int:
        return point_vector[(first % N0) * N0 + (second % N0)] % P

    for split in range(P + 1):
        horizontal = P - split
        vertical = split
        for base_first in range(N0):
            for base_second in range(N0):
                total = 0
                for left, choose_left in enumerate(binomial[horizontal]):
                    sign_left = -1 if (horizontal - left) % 2 else 1
                    for right, choose_right in enumerate(binomial[vertical]):
                        sign_right = -1 if (vertical - right) % 2 else 1
                        total += (
                            sign_left * choose_left * sign_right * choose_right
                            * value(base_first + left, base_second + P * right)
                        )
                if total % P:
                    return False
    return True


def divided_cross_carry(cross_mod9: list[list[int]]) -> list[int]:
    require(
        not any(coefficient % P for row in cross_mod9 for coefficient in row),
        "cross evaluation is not divisible by three",
    )
    quotients = [[coefficient // P for coefficient in row] for row in cross_mod9]
    point_vector: list[int] = []
    for first in range(N0):
        for second in range(N0):
            total = 0
            for slope in range(N0):
                offset = (P * slope * (E + first) + E + second) % N
                if offset < E:
                    total += quotients[slope][offset]
            point_vector.append(total % P)
    return point_vector


def matrix_from_columns(columns: list[list[int]]) -> list[list[int]]:
    return [[column[row] for column in columns] for row in range(len(columns[0]))]


def certificate() -> dict[str, object]:
    sources = source_polynomials(LIFT_MODULUS)
    labels = sorted(sources)
    zero_labels: list[tuple[int, int]] = []
    candidates: list[tuple[int, int]] = []
    candidate_columns: list[list[int]] = []
    cross_mod9: dict[tuple[int, int], list[list[int]]] = {}
    label_records: list[list[object]] = []

    for label in labels:
        index, power = label
        polynomial = sources[label]
        first_zero = not any(entry for row in first_chart(polynomial, P) for entry in row)
        cross_mod3 = cross_chart(polynomial, P)
        cross_zero = not any(entry for row in cross_mod3 for entry in row)
        predicted = index + P * power >= E
        label_records.append([index, power, threshold(index), first_zero, cross_zero, predicted])
        if cross_zero:
            zero_labels.append(label)
            cross_mod9[label] = cross_chart(polynomial, LIFT_MODULUS)
        else:
            candidates.append(label)
            candidate_columns.append([entry for row in cross_mod3 for entry in row])

    candidate_matrix = matrix_from_columns(candidate_columns)
    candidate_reduced, pivots = rref(candidate_matrix, P)
    correct_basis = row_basis(line_rows(), P)
    wrong_basis = row_basis(line_rows(transposed=True), P)
    membership_records: list[list[object]] = []
    correct_count = 0
    annihilator_count = 0
    transpose_rejection_count = 0
    for index, power in zero_labels:
        point_vector = divided_cross_carry(cross_mod9[(index, power)])
        correct = row_space_contains(correct_basis, point_vector, P)
        annihilator = annihilator_membership(point_vector)
        wrong = row_space_contains(wrong_basis, point_vector, P)
        correct_count += int(correct)
        annihilator_count += int(annihilator)
        transpose_rejection_count += int(not wrong)
        membership_records.append([
            index,
            power,
            correct,
            annihilator,
            compact_sha256(point_vector),
        ])

    acceptance = {
        "all_first_chart_zero": all(bool(row[3]) for row in label_records),
        "candidate_count_18": len(candidates) == 18,
        "candidate_rank_18": len(pivots) == 18,
        "cross_support_predicate_exact": all(bool(row[4]) == bool(row[5]) for row in label_records),
        "cross_zero_count_360": len(zero_labels) == 360,
        "dual_membership_oracles_agree": correct_count == annihilator_count == 360,
        "label_count_378": len(labels) == 378,
        "transpose_hostile_rejected": transpose_rejection_count > 0,
    }
    require(all(acceptance.values()), "p=3 cross-chart certificate failed")
    return {
        "acceptance": acceptance,
        "candidate_matrix": {
            "labels": [[index, power] for index, power in candidates],
            "matrix_sha256": compact_sha256(candidate_matrix),
            "pivot_columns": pivots,
            "rank": len(pivots),
            "rref_sha256": compact_sha256(candidate_reduced),
            "shape": [len(candidate_matrix), len(candidate_matrix[0])],
        },
        "divided_cross_carry": {
            "annihilator_membership_count": annihilator_count,
            "case_count": len(membership_records),
            "membership_digest": compact_sha256(membership_records),
            "row_space_membership_count": correct_count,
            "target_bundle": "normals (3a,1), a in F_3, constants modulo 9",
            "transpose_hostile_rejection_count": transpose_rejection_count,
        },
        "labels": {
            "candidate_count": len(candidates),
            "digest": compact_sha256(label_records),
            "first_chart_zero_count": sum(int(bool(row[3])) for row in label_records),
            "total": len(labels),
            "zero_cross_count": len(zero_labels),
        },
        "parameters": {"e": E, "p": P, "q": N, "q0": N0},
        "role": "bounded p=3 cross-chart and divided-carry check; no prime interpolation",
        "schema": "fcig.depth3.cross-chart-p3-result.v1",
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = canonical_bytes(certificate())
    if args.output is not None:
        args.output.write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
