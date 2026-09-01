#!/usr/bin/env python3
"""Exact local Smith tools for affine Hjelmslev--Radon incidence.

This module is an independent research companion written for the depth-three
exceptional-prime replay.  It uses only exact integer arithmetic modulo p^h.  It does
not infer an all-prime theorem from finite cases.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


def is_prime(p: int) -> bool:
    if isinstance(p, bool) or not isinstance(p, int) or p < 2:
        return False
    if p % 2 == 0:
        return p == 2
    d = 3
    while d * d <= p:
        if p % d == 0:
            return False
        d += 2
    return True


def validate_prime(p: int) -> None:
    if not is_prime(p):
        raise ValueError("p must be prime")


def projective_directions(p: int, n: int) -> list[tuple[int, int]]:
    validate_prime(p)
    if n < 1:
        raise ValueError("n must be positive")
    q = p**n
    return [(1, t) for t in range(q)] + [
        (p * s, 1) for s in range(p ** (n - 1))
    ]


def incidence_matrix(p: int, n: int) -> np.ndarray:
    """Return B_n^T: point rows, affine-line columns, with canonical charts."""
    q = p**n
    directions = projective_directions(p, n)
    xs = np.repeat(np.arange(q, dtype=np.int64), q)
    ys = np.tile(np.arange(q, dtype=np.int64), q)
    matrix = np.zeros((q * q, len(directions) * q), dtype=np.int64)
    point_index = np.arange(q * q)
    for direction_index, (a, b) in enumerate(directions):
        offsets = (a * xs + b * ys) % q
        matrix[point_index, direction_index * q + offsets] = 1
    return matrix


def canonical_matrix_sha256(matrix: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(matrix, dtype=np.int64))
    header = json.dumps(
        {"shape": list(a.shape), "dtype": "int64"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(header + b"\n" + a.tobytes(order="C")).hexdigest()


def profile_dict(values: Iterable[int]) -> dict[int, int]:
    return dict(sorted(Counter(int(v) for v in values).items()))


def index_curve(profile: dict[int, int] | Counter[int], height: int) -> int:
    return sum(
        max(height - int(exponent), 0) * int(multiplicity)
        for exponent, multiplicity in profile.items()
    )


def weighted_order(profile: dict[int, int] | Counter[int]) -> int:
    return sum(int(e) * int(m) for e, m in profile.items())


def theoretical_order_exponent(p: int, n: int) -> int:
    validate_prime(p)
    numerator = n * p ** (2 * n) * (p * p - 1) - p * (p ** (2 * n) - 1)
    denominator = 2 * (p * p - 1)
    if numerator % denominator:
        raise ArithmeticError("order formula failed integrality")
    return numerator // denominator


def _vp_mod_scalar(value: int, p: int, cutoff: int) -> int:
    value %= p**cutoff
    if value == 0:
        return cutoff
    valuation = 0
    while value % p == 0:
        value //= p
        valuation += 1
    return valuation


def _hash_state(hasher: "hashlib._Hash", *items: object) -> None:
    hasher.update(json.dumps(items, separators=(",", ":"), sort_keys=False).encode("ascii"))
    hasher.update(b"\n")


@dataclass(frozen=True)
class SmithRun:
    valuations: tuple[int, ...]
    transcript_sha256: str
    cutoff: int
    algorithm: str

    @property
    def profile(self) -> dict[int, int]:
        return profile_dict(self.valuations)


def local_smith_minpivot(
    matrix: Sequence[Sequence[int]] | np.ndarray,
    p: int,
    cutoff: int,
    *,
    reverse_ties: bool = False,
) -> SmithRun:
    """Exact local Smith elimination over Z/p^cutoff Z.

    Each pivot has minimal p-valuation in the unresolved submatrix.  Row and
    column operations are invertible modulo p^cutoff.  A cutoff is resolving
    only when all min(m,n) pivots are found below it.
    """
    validate_prime(p)
    if cutoff < 1:
        raise ValueError("cutoff must be positive")
    modulus = p**cutoff
    a = np.asarray(matrix, dtype=np.int64).copy() % modulus
    if a.ndim != 2 or not a.shape[0] or not a.shape[1]:
        raise ValueError("nonempty rectangular matrix required")
    rows, cols = a.shape
    diagonal = min(rows, cols)
    vals: list[int] = []
    transcript = hashlib.sha256()
    _hash_state(transcript, "minpivot-v2", p, cutoff, rows, cols, reverse_ties)

    for k in range(diagonal):
        sub = a[k:, k:]
        pivot: tuple[int, int, int] | None = None
        for valuation in range(cutoff):
            pv = p**valuation
            mask = (sub % (pv * p) != 0)
            if valuation:
                mask &= (sub % pv == 0)
            locations = np.argwhere(mask)
            if locations.size:
                loc = locations[-1] if reverse_ties else locations[0]
                pivot = (valuation, k + int(loc[0]), k + int(loc[1]))
                break
        if pivot is None:
            break
        valuation, pivot_row, pivot_col = pivot
        if pivot_row != k:
            a[[k, pivot_row], :] = a[[pivot_row, k], :]
        if pivot_col != k:
            a[:, [k, pivot_col]] = a[:, [pivot_col, k]]

        pivot_power = p**valuation
        unit = (int(a[k, k]) // pivot_power) % modulus
        a[k, :] = (a[k, :] * pow(unit, -1, modulus)) % modulus

        if k + 1 < rows:
            entries = a[k + 1 :, k]
            if np.any(entries % pivot_power):
                raise AssertionError("minimal pivot failed column divisibility")
            factors = (entries // pivot_power) % modulus
            if np.any(factors):
                a[k + 1 :, :] = (
                    a[k + 1 :, :] - factors[:, None] * a[k, :]
                ) % modulus

        if k + 1 < cols:
            entries = a[k, k + 1 :]
            if np.any(entries % pivot_power):
                raise AssertionError("minimal pivot failed row divisibility")
            factors = (entries // pivot_power) % modulus
            if np.any(factors):
                a[:, k + 1 :] = (
                    a[:, k + 1 :] - a[:, k, None] * factors[None, :]
                ) % modulus

        vals.append(valuation)
        _hash_state(
            transcript,
            k,
            valuation,
            pivot_row,
            pivot_col,
            int(np.sum(a[k:, k:] % modulus) % modulus),
        )

    if len(vals) != diagonal:
        raise AssertionError(
            f"cutoff {cutoff} did not resolve all {diagonal} local factors; got {len(vals)}"
        )
    if vals != sorted(vals):
        raise AssertionError("local valuations are not ordered")
    return SmithRun(tuple(vals), transcript.hexdigest(), cutoff, "minpivot-v2")


def _find_unit(a: np.ndarray, p: int, reverse: bool) -> tuple[int, int] | None:
    locations = np.argwhere(a % p != 0)
    if not locations.size:
        return None
    loc = locations[-1] if reverse else locations[0]
    return int(loc[0]), int(loc[1])


def bockstein_layer_peeling(
    matrix: Sequence[Sequence[int]] | np.ndarray,
    p: int,
    cutoff: int,
    *,
    reverse_units: bool = True,
) -> SmithRun:
    """Independent exact algorithm: peel unit pivots one Bockstein layer at a time."""
    validate_prime(p)
    if cutoff < 1:
        raise ValueError("cutoff must be positive")
    original = np.asarray(matrix, dtype=np.int64)
    if original.ndim != 2 or not original.shape[0] or not original.shape[1]:
        raise ValueError("nonempty rectangular matrix required")
    target = min(original.shape)
    current = original.copy() % (p**cutoff)
    valuations: list[int] = []
    transcript = hashlib.sha256()
    _hash_state(
        transcript,
        "bockstein-peeling-v2",
        p,
        cutoff,
        *original.shape,
        reverse_units,
    )

    for level in range(cutoff):
        remaining = cutoff - level
        modulus = p**remaining
        current %= modulus
        pivot_count = 0
        while pivot_count < min(current.shape):
            sub = current[pivot_count:, pivot_count:]
            loc = _find_unit(sub, p, reverse_units)
            if loc is None:
                break
            i = pivot_count + loc[0]
            j = pivot_count + loc[1]
            if i != pivot_count:
                current[[pivot_count, i], :] = current[[i, pivot_count], :]
            if j != pivot_count:
                current[:, [pivot_count, j]] = current[:, [j, pivot_count]]
            unit = int(current[pivot_count, pivot_count]) % modulus
            current[pivot_count, :] = (
                current[pivot_count, :] * pow(unit, -1, modulus)
            ) % modulus

            if pivot_count + 1 < current.shape[0]:
                factors = current[pivot_count + 1 :, pivot_count].copy() % modulus
                if np.any(factors):
                    current[pivot_count + 1 :, :] = (
                        current[pivot_count + 1 :, :]
                        - factors[:, None] * current[pivot_count, :]
                    ) % modulus
            if pivot_count + 1 < current.shape[1]:
                factors = current[pivot_count, pivot_count + 1 :].copy() % modulus
                if np.any(factors):
                    current[:, pivot_count + 1 :] = (
                        current[:, pivot_count + 1 :]
                        - current[:, pivot_count, None] * factors[None, :]
                    ) % modulus
            pivot_count += 1

        valuations.extend([level] * pivot_count)
        residual = current[pivot_count:, pivot_count:]
        _hash_state(
            transcript,
            level,
            pivot_count,
            *residual.shape,
            int(np.sum(residual % modulus) % modulus),
        )
        if len(valuations) == target:
            break
        if residual.size == 0:
            break
        if np.any(residual % p):
            raise AssertionError("unit layer was not exhausted")
        current = residual // p

    if len(valuations) != target:
        raise AssertionError(
            f"cutoff {cutoff} did not resolve all {target} factors; got {len(valuations)}"
        )
    if valuations != sorted(valuations):
        raise AssertionError("peeled valuations are not ordered")
    return SmithRun(
        tuple(valuations),
        transcript.hexdigest(),
        cutoff,
        "bockstein-peeling-v2",
    )


def relation_matrix_z(p: int, n: int) -> np.ndarray:
    """Exact top-shell relation matrix Z_{p,n} from clipped-line coordinates."""
    validate_prime(p)
    if n < 1:
        raise ValueError("n must be positive")
    q = p**n
    q0 = p ** (n - 1)
    degree = q - q0
    directions = projective_directions(p, n)
    labels = [(a, b, offset) for a, b in directions for offset in range(degree)]
    rank = (q + q0) * degree
    z = np.zeros((rank, rank), dtype=np.int64)
    aa = np.array([a for a, _, _ in labels], dtype=np.int64)
    bb = np.array([b for _, b, _ in labels], dtype=np.int64)
    oo = np.array([o for _, _, o in labels], dtype=np.int64)
    row = 0
    for i in range(degree):
        high_i = degree + (i % q0)
        for y in range(q):
            z[row, :] = (
                ((aa * i + bb * y) % q == oo).astype(np.int64)
                - ((aa * high_i + bb * y) % q == oo).astype(np.int64)
            )
            row += 1
    for r in range(q0):
        high_r = degree + r
        for i in range(degree):
            high_i = degree + (i % q0)
            z[row, :] = (
                ((aa * high_r + bb * i) % q == oo).astype(np.int64)
                - ((aa * high_r + bb * high_i) % q == oo).astype(np.int64)
            )
            row += 1
    if row != rank:
        raise AssertionError("relation-matrix shape drift")
    return z


def beta_digit_sum(p: int, n: int, j: int) -> int:
    """Weber--Kuenzer valuation beta_p(j), specialized to p-power level."""
    if not 0 <= j < p**n:
        raise ValueError("j outside p-power range")
    digits: list[int] = []
    value = j
    for _ in range(n):
        digits.append(value % p)
        value //= p
    digits.append(0)
    return sum((digits[k] - digits[k + 1]) * (k + 1) * p**k for k in range(n))


def ideal_profile(alpha: int, ramification: int) -> Counter[int]:
    quotient, remainder = divmod(alpha, ramification)
    profile: Counter[int] = Counter()
    profile[quotient] += ramification - remainder
    if remainder:
        profile[quotient + 1] += remainder
    return profile


def cyclic_first_chart_profile(p: int, n: int) -> dict[int, int]:
    """Profile of V_{p^n}^{(n)} from the cited cyclic diagonal formula."""
    validate_prime(p)
    e = (p - 1) * p ** (n - 1)
    out: Counter[int] = Counter()
    for j in range(p**n):
        out.update(ideal_profile(beta_digit_sum(p, n, j), e))
    return dict(sorted(out.items()))


def cyclic_second_chart_profile(p: int, n: int) -> dict[int, int]:
    """Profile of p V_{p^(n-1)}^(n), including ramification and scalar p."""
    validate_prime(p)
    if n < 2:
        raise ValueError("second chart starts at depth two")
    q0 = p ** (n - 1)
    e_top = (p - 1) * p ** (n - 1)
    e_low = (p - 1) * p ** (n - 2)
    out: Counter[int] = Counter()
    # At top ramification, a low-level (1-zeta) valuation is multiplied by p;
    # the scalar p adds e_top.  Convert each top ideal to p-Smith exponents.
    for j in range(q0):
        alpha_top = p * beta_digit_sum(p, n - 1, j) + e_top
        out.update(ideal_profile(alpha_top, e_top))
    expected_rank = q0 * e_top
    if sum(out.values()) != expected_rank:
        raise AssertionError(("second-chart rank drift", p, n, out))
    return dict(sorted(out.items()))


def complement_profile(profile_z: dict[int, int], scale_exponent: int) -> dict[int, int]:
    """If T Z = p^n I, convert Z exponents into T exponents."""
    out: Counter[int] = Counter()
    for exponent, multiplicity in profile_z.items():
        if not 0 <= exponent <= scale_exponent:
            raise ValueError("relation exponent outside scaled-inverse range")
        out[scale_exponent - exponent] += multiplicity
    return dict(sorted(out.items()))


def obstruction_curve_from_profiles(
    total: dict[int, int],
    first: dict[int, int],
    second: dict[int, int],
    bound: int,
) -> tuple[int, ...]:
    return tuple(
        index_curve(total, r) - index_curve(first, r) - index_curve(second, r)
        for r in range(1, bound + 1)
    )


def carry_curve_from_profiles(
    total: dict[int, int],
    previous: dict[int, int],
    relation: dict[int, int],
    bound: int,
) -> tuple[int, ...]:
    return tuple(
        index_curve(total, r) - index_curve(previous, r) - index_curve(relation, r)
        for r in range(1, bound + 1)
    )


def depth_two_formula(p: int) -> dict[int, int]:
    validate_prime(p)
    return {
        0: p * p * (p + 1) * (p + 1) // 4,
        1: p**3 * (p - 1) // 2,
        2: p * (p - 1) ** 2 * (p + 2) // 4,
        3: p * (p - 1) // 2,
    }


def high_tail_expected(previous: dict[int, int], n: int) -> dict[int, int]:
    return {
        n + h: previous.get(n - 2 + h, 0)
        for h in range(1, n)
    }


def depth3_profile_from_M_H(p: int, M: int, H: int) -> dict[int, int]:
    """Depth-three reduction using the proved high-tail transfer."""
    validate_prime(p)
    N = p**6
    s = theoretical_order_exponent(p, 3)
    b = p * (p - 1) ** 2 * (p + 2) // 4
    c = p * (p - 1) // 2
    m5 = c
    m4 = b
    m3 = H - b - c
    m2 = s - N + M - 2 * H - b - 2 * c
    m1 = 2 * N - 2 * M + H + b + 2 * c - s
    out = {0: M, 1: m1, 2: m2, 3: m3, 4: m4, 5: m5}
    if any(v < 0 for v in out.values()) or sum(out.values()) != N:
        raise ValueError(("inadmissible M,H", p, M, H, out))
    if weighted_order(out) != s:
        raise AssertionError("depth-three reduction order drift")
    return out


def permute_matrix(matrix: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rows = rng.permutation(matrix.shape[0])
    cols = rng.permutation(matrix.shape[1])
    return np.asarray(matrix)[rows][:, cols]
