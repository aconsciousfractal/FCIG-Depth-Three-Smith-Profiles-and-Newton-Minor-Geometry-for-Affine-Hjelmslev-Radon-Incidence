#!/usr/bin/env python3
"""Exact-arithmetic companion for the all-prime depth-three Smith profile.

The module validates the structured formula object, proves its two polynomial
rank and weighted-order identities symbolically over the rationals, evaluates
the profile only for prime inputs, reconstructs the Newton threshold counts,
and emits a deterministic receipt.  These checks support the paper; they do
not replace its all-prime proofs.
"""

from __future__ import annotations

from bisect import bisect_left
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FORMULAS = ROOT / "formulas.json"
SCHEMA = "fcig.depth3.formulas.v1"
BRANCHES = ("mod6_1", "mod6_5")
SYMBOLS = tuple(f"m_{index}" for index in range(6))


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def load_contract(path: Path) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    data = json.loads(payload.decode("utf-8"))
    require(isinstance(data, dict), "formula root object")
    validate_structure(data)
    return data, payload


def _validate_condition(condition: object, branch: str) -> None:
    require(isinstance(condition, dict), f"condition object: {branch}")
    expected = {
        "minimum_prime": 5,
        "modulus": 6,
        "residue": 1 if branch == "mod6_1" else 5,
    }
    require(condition == expected, f"condition: {branch}")


def _validate_expression(expression: object, label: str) -> None:
    require(isinstance(expression, dict), f"expression object: {label}")
    require(set(expression) == {"denominator", "factors"}, f"expression keys: {label}")
    denominator = expression["denominator"]
    require(type(denominator) is int and denominator > 0, f"positive denominator: {label}")
    factors = expression["factors"]
    require(isinstance(factors, list) and factors, f"nonempty factors: {label}")
    for index, factor in enumerate(factors):
        require(isinstance(factor, dict), f"factor object: {label}:{index}")
        require(set(factor) == {"coefficients", "power"}, f"factor keys: {label}:{index}")
        coefficients = factor["coefficients"]
        require(isinstance(coefficients, list) and coefficients, f"coefficients: {label}:{index}")
        require(all(type(value) is int for value in coefficients), f"integer coefficients: {label}:{index}")
        require(coefficients[-1] != 0, f"nonzero leading coefficient: {label}:{index}")
        power = factor["power"]
        require(type(power) is int and power > 0, f"positive power: {label}:{index}")


def validate_structure(data: dict[str, Any]) -> None:
    require(data.get("schema") == SCHEMA, "formula schema")
    require(data.get("representation") == {
        "coefficient_order": "ascending powers of p",
        "expression": "product of polynomial factors divided by a positive integer denominator",
        "variable": "p",
    }, "formula representation")
    authority = data.get("authority")
    require(isinstance(authority, dict), "authority object")
    require(authority == {
        "proof_source": "paper/main.tex",
        "scope": (
            "structured rendering and exact-arithmetic verification; "
            "the written proof is authoritative"
        ),
    }, "authority boundary")

    epsilon = data.get("epsilon_1")
    require(isinstance(epsilon, dict), "epsilon object")
    require(set(epsilon) == {"branches", "exceptional", "symbol"}, "epsilon keys")
    require(epsilon["symbol"] == "epsilon_1(p,3)", "epsilon symbol")
    require(epsilon["exceptional"] == {"2": 1, "3": 18}, "epsilon exceptional values")
    require(tuple(epsilon["branches"]) == BRANCHES, "epsilon branch order")
    for branch in BRANCHES:
        row = epsilon["branches"][branch]
        require(isinstance(row, dict) and set(row) == {"condition", "expression"}, f"epsilon branch keys: {branch}")
        _validate_condition(row["condition"], branch)
        _validate_expression(row["expression"], f"epsilon:{branch}")

    profile = data.get("smith_profile")
    require(isinstance(profile, dict), "profile object")
    require(set(profile) == {"branches", "exceptional", "symbols"}, "profile keys")
    require(tuple(profile["symbols"]) == SYMBOLS, "profile symbols")
    require(profile["exceptional"] == {
        "2": [30, 6, 19, 6, 2, 1],
        "3": [240, 168, 195, 108, 15, 3],
    }, "profile exceptional values")
    require(tuple(profile["branches"]) == BRANCHES, "profile branch order")
    for branch in BRANCHES:
        row = profile["branches"][branch]
        require(isinstance(row, dict) and set(row) == {"condition", "multiplicities"}, f"profile branch keys: {branch}")
        _validate_condition(row["condition"], branch)
        multiplicities = row["multiplicities"]
        require(isinstance(multiplicities, list) and len(multiplicities) == 6, f"six multiplicities: {branch}")
        require(tuple(item.get("symbol") for item in multiplicities) == SYMBOLS, f"multiplicity order: {branch}")
        for item in multiplicities:
            require(isinstance(item, dict) and set(item) == {"expression", "symbol"}, f"multiplicity keys: {branch}")
            _validate_expression(item["expression"], f"{branch}:{item['symbol']}")


def poly_trim(poly: list[Fraction]) -> tuple[Fraction, ...]:
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    return tuple(poly)


def poly_mul(left: tuple[Fraction, ...], right: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    result = [Fraction(0) for _ in range(len(left) + len(right) - 1)]
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] += a * b
    return poly_trim(result)


def poly_add(left: tuple[Fraction, ...], right: tuple[Fraction, ...], scale: int = 1) -> tuple[Fraction, ...]:
    result = [Fraction(0) for _ in range(max(len(left), len(right)))]
    for index, value in enumerate(left):
        result[index] += value
    for index, value in enumerate(right):
        result[index] += scale * value
    return poly_trim(result)


def expression_polynomial(expression: dict[str, Any]) -> tuple[Fraction, ...]:
    result = (Fraction(1),)
    for factor in expression["factors"]:
        base = tuple(Fraction(value) for value in factor["coefficients"])
        for _ in range(factor["power"]):
            result = poly_mul(result, base)
    denominator = expression["denominator"]
    return poly_trim([value / denominator for value in result])


def poly_affine_substitute(
    polynomial: tuple[Fraction, ...], scale: int, shift: int,
) -> tuple[Fraction, ...]:
    """Return P(scale*h+shift) in ascending powers of h."""

    result = (Fraction(0),)
    power = (Fraction(1),)
    affine = (Fraction(shift), Fraction(scale))
    for coefficient in polynomial:
        result = poly_add(
            result, tuple(coefficient * value for value in power)
        )
        power = poly_mul(power, affine)
    return result


def branch_h_coefficients(data: dict[str, Any]) -> dict[str, list[list[int]]]:
    """Expand every profile row after p=6h+r and prove coefficient positivity."""

    controls: dict[str, list[list[int]]] = {}
    for branch in BRANCHES:
        residue = 1 if branch == "mod6_1" else 5
        rows = data["smith_profile"]["branches"][branch]["multiplicities"]
        branch_rows: list[list[int]] = []
        for row in rows:
            polynomial = expression_polynomial(row["expression"])
            substituted = poly_affine_substitute(polynomial, 6, residue)
            require(
                all(value.denominator == 1 for value in substituted),
                f"integral h-coefficients: {branch}:{row['symbol']}",
            )
            coefficients = [value.numerator for value in substituted]
            require(
                all(value >= 0 for value in coefficients),
                f"nonnegative h-coefficients: {branch}:{row['symbol']}",
            )
            branch_rows.append(coefficients)
        controls[branch] = branch_rows
    return controls


def expression_value(expression: dict[str, Any], p: int, label: str) -> int:
    numerator = 1
    for factor in expression["factors"]:
        value = sum(coefficient * p**degree for degree, coefficient in enumerate(factor["coefficients"]))
        numerator *= value ** factor["power"]
    denominator = expression["denominator"]
    require(numerator % denominator == 0, f"nonintegral {label} at p={p}")
    return numerator // denominator


def is_prime(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def branch_for_prime(p: int) -> str:
    require(is_prime(p) and p > 3, f"branch prime: {p}")
    return "mod6_1" if p % 6 == 1 else "mod6_5"


def epsilon_value(data: dict[str, Any], p: int) -> int:
    exceptional = data["epsilon_1"]["exceptional"]
    if str(p) in exceptional:
        return int(exceptional[str(p)])
    branch = branch_for_prime(p)
    return expression_value(data["epsilon_1"]["branches"][branch]["expression"], p, "epsilon_1")


def profile_value(data: dict[str, Any], p: int) -> tuple[int, ...]:
    exceptional = data["smith_profile"]["exceptional"]
    if str(p) in exceptional:
        return tuple(int(value) for value in exceptional[str(p)])
    branch = branch_for_prime(p)
    rows = data["smith_profile"]["branches"][branch]["multiplicities"]
    return tuple(expression_value(row["expression"], p, row["symbol"]) for row in rows)


def formula_data() -> dict[str, Any]:
    data, _ = load_contract(FORMULAS)
    return data


def smith_profile(p: int) -> tuple[int, ...]:
    if not is_prime(p):
        raise ValueError("p must be prime")
    return profile_value(formula_data(), p)


def epsilon_1(p: int) -> int:
    if not is_prime(p):
        raise ValueError("p must be prime")
    return epsilon_value(formula_data(), p)


def total_order_exponent(p: int) -> int:
    if not is_prime(p):
        raise ValueError("p must be prime")
    numerator = 3 * p**6 - p**5 - p**3 - p
    if numerator % 2:
        raise ArithmeticError("weighted-order formula is not integral")
    return numerator // 2


def _vp(value: int, p: int) -> int:
    valuation = 0
    while value and value % p == 0:
        valuation += 1
        value //= p
    return valuation


def newton_data(p: int) -> tuple[int, int, int]:
    """Return boundary columns, minimal generators and common-image length."""

    if not is_prime(p) or p < 3:
        raise ValueError("Newton data requires an odd prime")
    cutoff = p**2 * (p - 1)
    beta = [0]
    degree = 1
    while beta[-1] < cutoff:
        beta.append(beta[-1] + p ** _vp(degree, p))
        degree += 1
    records: list[tuple[int, int]] = []
    for boundary_index in range(p * (p - 1)):
        first = bisect_left(beta, cutoff - boundary_index)
        initial_order = first + p * boundary_index
        if initial_order < cutoff:
            threshold = first + p * beta[boundary_index]
            records.append((boundary_index, threshold))
    active = [threshold for _, threshold in records if threshold < cutoff]
    return len(records), len(active), sum(cutoff - value for value in active)


def validate_profile_identities(data: dict[str, Any]) -> None:
    rank_target = tuple([Fraction(0)] * 6 + [Fraction(1)])
    order_target = (
        Fraction(0), Fraction(-1, 2), Fraction(0), Fraction(-1, 2),
        Fraction(0), Fraction(-1, 2), Fraction(3, 2),
    )
    for branch in BRANCHES:
        rows = data["smith_profile"]["branches"][branch]["multiplicities"]
        polynomials = [expression_polynomial(row["expression"]) for row in rows]
        rank = (Fraction(0),)
        order = (Fraction(0),)
        for index, polynomial in enumerate(polynomials):
            rank = poly_add(rank, polynomial)
            order = poly_add(order, polynomial, index)
        require(rank == rank_target, f"symbolic rank identity: {branch}")
        require(order == order_target, f"symbolic weighted-order identity: {branch}")

    branch_h_coefficients(data)

    for p, expected in ((2, (30, 6, 19, 6, 2, 1)), (3, (240, 168, 195, 108, 15, 3))):
        profile = profile_value(data, p)
        require(profile == expected, f"exceptional profile: p={p}")
        require(sum(profile) == p**6, f"exceptional rank: p={p}")
        require(sum(index * value for index, value in enumerate(profile)) == (3*p**6-p**5-p**3-p)//2, f"exceptional order: p={p}")


def _render_polynomial(coefficients: list[int]) -> str:
    terms: list[tuple[str, str]] = []
    for degree in range(len(coefficients) - 1, -1, -1):
        coefficient = coefficients[degree]
        if coefficient == 0:
            continue
        sign = "-" if coefficient < 0 else "+"
        magnitude = abs(coefficient)
        if degree == 0:
            body = str(magnitude)
        else:
            coefficient_text = "" if magnitude == 1 else str(magnitude)
            power = "p" if degree == 1 else f"p^{degree}"
            body = coefficient_text + power
        terms.append((sign, body))
    require(bool(terms), "zero polynomial cannot be rendered")
    first_sign, first_body = terms[0]
    rendered = ("-" if first_sign == "-" else "") + first_body
    for sign, body in terms[1:]:
        rendered += sign + body
    return rendered


def render_expression(expression: dict[str, Any]) -> str:
    pieces: list[str] = []
    for factor in expression["factors"]:
        polynomial = _render_polynomial(factor["coefficients"])
        nonzero = sum(value != 0 for value in factor["coefficients"])
        needs_parentheses = nonzero > 1
        piece = f"({polynomial})" if needs_parentheses else polynomial
        if factor["power"] != 1:
            piece += f"^{factor['power']}"
        pieces.append(piece)
    numerator = "".join(pieces)
    denominator = expression["denominator"]
    return numerator if denominator == 1 else f"\\frac{{{numerator}}}{{{denominator}}}"


def render_tex(data: dict[str, Any], source_sha256: str) -> str:
    epsilon = data["epsilon_1"]
    profile = data["smith_profile"]
    eps_one = render_expression(epsilon["branches"]["mod6_1"]["expression"])
    eps_five = render_expression(epsilon["branches"]["mod6_5"]["expression"])
    p2 = ",".join(str(value) for value in profile["exceptional"]["2"])
    p3 = ",".join(str(value) for value in profile["exceptional"]["3"])
    rank_one = render_expression(profile["branches"]["mod6_1"]["multiplicities"][0]["expression"])
    rank_five = render_expression(profile["branches"]["mod6_5"]["multiplicities"][0]["expression"])

    lines = [
        "% Generated deterministically from companion/formulas.json; do not edit by hand.",
        f"% FCIG-FORMULAS-SHA256: {source_sha256}",
        "\\newcommand{\\FCIGDThreeEpsilonClosedFormula}{%",
        "\\begin{cases}",
        f" {epsilon['exceptional']['3']},&p=3,\\\\[1mm]",
        f" {eps_one},&p>3,\\ p\\equiv1\\pmod6,\\\\[3mm]",
        f" {eps_five},&p\\equiv5\\pmod6.",
        "\\end{cases}%",
        "}",
        f"\\newcommand{{\\FCIGDThreeSmithProfileTwo}}{{({p2})}}",
        f"\\newcommand{{\\FCIGDThreeSmithProfileThree}}{{({p3})}}",
        f"\\newcommand{{\\FCIGDThreeModularRankOne}}{{{rank_one}}}",
        f"\\newcommand{{\\FCIGDThreeModularRankTwo}}{{{rank_five}}}",
    ]
    for branch, macro in (
        ("mod6_1", "FCIGDThreeSmithProfileModOne"),
        ("mod6_5", "FCIGDThreeSmithProfileModFive"),
    ):
        lines.extend([
            f"\\newcommand{{\\{macro}}}{{%",
            "\\boxed{\\begin{aligned}",
        ])
        rows = profile["branches"][branch]["multiplicities"]
        for index, row in enumerate(rows):
            ending = ",\\\\" if index < len(rows) - 1 else "."
            lines.append(f" {row['symbol'].replace('_', '_')} &={render_expression(row['expression'])}{ending}")
        lines.extend(["\\end{aligned}}%", "}"])
    return "\n".join(lines) + "\n"


def verify() -> dict[str, Any]:
    data, payload = load_contract(FORMULAS)
    validate_profile_identities(data)
    h_coefficients = branch_h_coefficients(data)
    formula_sha256 = sha256_bytes(payload)
    generated = render_tex(data, formula_sha256)
    generated_path = ROOT.parent / "paper" / "generated" / "formulas.tex"
    require(generated_path.read_text(encoding="utf-8") == generated, "generated TeX drift")

    profile_controls = {
        2: (30, 6, 19, 6, 2, 1),
        3: (240, 168, 195, 108, 15, 3),
        5: (4050, 4140, 4795, 2490, 140, 10),
        7: (26740, 34608, 36225, 19488, 567, 21),
        11: (363000, 545622, 561979, 297330, 3575, 55),
    }
    prime_census = 0
    for prime in range(2, 252):
        if not is_prime(prime):
            continue
        prime_census += 1
        profile = smith_profile(prime)
        require(all(value >= 0 for value in profile), f"negative multiplicity p={prime}")
        require(sum(profile) == prime**6, f"rank identity p={prime}")
        require(
            sum(index * value for index, value in enumerate(profile))
            == total_order_exponent(prime),
            f"weighted-order identity p={prime}",
        )
    for prime, expected in profile_controls.items():
        require(smith_profile(prime) == expected, f"profile control p={prime}")

    newton_controls = {
        3: (3, 3, 18),
        5: (12, 8, 250),
        7: (28, 15, 1635),
        11: (71, 40, 15741),
    }
    for prime, expected in newton_controls.items():
        require(newton_data(prime) == expected, f"Newton control p={prime}")
        require(expected[2] == epsilon_1(prime), f"epsilon/Newton agreement p={prime}")

    result_path = ROOT / "exceptional_profiles" / "RESULT.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    require(result.get("schema") == "fcig.depth3.exceptional-result.v1", "exceptional schema")
    exceptional_cases = result.get("cases")
    require(isinstance(exceptional_cases, dict), "exceptional cases")
    for prime in (2, 3):
        row = exceptional_cases.get(str(prime))
        require(isinstance(row, dict), f"exceptional row p={prime}")
        observed = tuple(
            int(row["profile"].get(str(index), 0)) for index in range(6)
        )
        require(observed == profile_controls[prime], f"exceptional/profile agreement p={prime}")

    epsilon_p2_path = ROOT / "epsilon1_p2" / "RESULT.json"
    epsilon_p2 = json.loads(epsilon_p2_path.read_text(encoding="utf-8"))
    require(
        epsilon_p2.get("schema") == "fcig.depth3.epsilon1-p2-result.v1",
        "p=2 epsilon schema",
    )
    require(epsilon_p2.get("status") == "PASS", "p=2 epsilon status")
    require(epsilon_p2.get("epsilon_1") == epsilon_1(2) == 1, "p=2 epsilon value")
    epsilon_p2_ranks = epsilon_p2.get("rank_lanes", {}).get("rref", {})
    require(epsilon_p2_ranks.get("first_chart") == 8, "p=2 first-chart rank")
    require(epsilon_p2_ranks.get("two_chart") == 9, "p=2 two-chart rank")

    return {
        "boundary": "exact arithmetic supports but does not replace the all-prime proof",
        "branch_h_coefficients": h_coefficients,
        "epsilon1_p2_result_sha256": sha256_bytes(epsilon_p2_path.read_bytes()),
        "exceptional_result_sha256": sha256_bytes(result_path.read_bytes()),
        "formula_sha256": formula_sha256,
        "generated_tex_sha256": sha256_bytes(generated.encode("utf-8")),
        "newton_controls": {
            str(prime): list(values) for prime, values in newton_controls.items()
        },
        "prime_identity_census": prime_census,
        "profile_controls": {
            str(prime): list(values) for prime, values in profile_controls.items()
        },
        "schema": "fcig.depth3.companion-receipt.v1",
        "status": "PASS",
    }


def main() -> int:
    receipt = verify()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
