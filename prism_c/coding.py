"""Systematic 2+1 XOR and 4+2 P/Q erasure coding over GF(256).

Runtime digests establish row authenticity. This is not an RFC wire codec.
"""

import hashlib

from .model import Rejected, profile_spec
from .profiles import DEFAULT_PROFILE


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xor(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise Rejected("Unequal fragment lengths")
    return (int.from_bytes(left, "little") ^ int.from_bytes(right, "little")).to_bytes(len(left), "little")


# Primitive polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11d), alpha = 2.
_EXP = [0] * 510
_LOG = [0] * 256
_element = 1
for _power in range(255):
    _EXP[_power] = _element
    _LOG[_element] = _power
    _element <<= 1
    if _element & 0x100:
        _element ^= 0x11D
for _power in range(255, 510):
    _EXP[_power] = _EXP[_power - 255]


def gf_mul(left: int, right: int) -> int:
    return 0 if left == 0 or right == 0 else _EXP[_LOG[left] + _LOG[right]]


def gf_inverse(value: int) -> int:
    if value == 0:
        raise Rejected("Singular reconstruction matrix")
    return _EXP[255 - _LOG[value]]


def invert(matrix):
    size = len(matrix)
    rows = [list(row) + [int(i == j) for j in range(size)] for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = next((i for i in range(column, size) if rows[i][column]), None)
        if pivot is None:
            raise Rejected("Singular reconstruction matrix")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        factor = gf_inverse(rows[column][column])
        rows[column] = [gf_mul(value, factor) for value in rows[column]]
        for i in range(size):
            if i != column and rows[i][column]:
                factor = rows[i][column]
                rows[i] = [a ^ gf_mul(factor, b) for a, b in zip(rows[i], rows[column])]
    return tuple(tuple(row[size:]) for row in rows)


# Immutable field transforms: 64 KiB of payload, built once per interpreter.
# These preserve the existing polynomial and all codeword bytes. Initialization
# is included in E19's separate cold-module measurements, not hidden as free work.
_MUL_TABLES = tuple(bytes(gf_mul(coefficient, value) for value in range(256))
                    for coefficient in range(256))


def combine(coefficients, fragments):
    size = len(fragments[0])
    active = tuple((coefficient, fragment) for coefficient, fragment in zip(coefficients, fragments) if coefficient)
    if len(active) == 1 and active[0][0] == 1 and len(active[0][1]) == size:
        return active[0][1]  # Systematic rows already are immutable bytes.
    output = 0
    for coefficient, fragment in active:
        transformed = fragment if coefficient == 1 else fragment.translate(_MUL_TABLES[coefficient])
        output ^= int.from_bytes(transformed, "little")
    return output.to_bytes(size, "little")


def encode(data: bytes, profile: str = DEFAULT_PROFILE) -> tuple[bytes, ...]:
    code = profile_spec(profile)
    if not isinstance(data, bytes):
        raise Rejected("Content must be bytes")
    size = max(1, (len(data) + code.data_rows - 1) // code.data_rows)
    padded = data.ljust(size * code.data_rows, b"\x00")
    source = tuple(padded[i * size:(i + 1) * size] for i in range(code.data_rows))
    return tuple(combine(row, source) for row in code.generator)


def recover(rows: dict[int, bytes], length: int, profile: str = DEFAULT_PROFILE) -> tuple[bytes, tuple[bytes, ...]]:
    code = profile_spec(profile)
    if (not isinstance(rows, dict) or len(rows) < code.data_rows
            or any(type(row) is not int or row not in range(code.total_rows) for row in rows)
            or any(not isinstance(fragment, bytes) for fragment in rows.values())):
        raise Rejected("Need distinct valid rows for the selected profile")
    sizes = {len(fragment) for fragment in rows.values()}
    if (len(sizes) != 1 or next(iter(sizes)) < 1 or type(length) is not int
            or length < 0 or length > next(iter(sizes)) * code.data_rows):
        raise Rejected("Invalid content/fragment length")
    chosen = sorted(rows)[:code.data_rows]
    inverse = invert(tuple(code.generator[row] for row in chosen))
    source = tuple(combine(row, tuple(rows[i] for i in chosen)) for row in inverse)
    regenerated = tuple(combine(row, source) for row in code.generator)
    if any(fragment != regenerated[row] for row, fragment in rows.items()):
        raise Rejected("Supplied code rows are inconsistent")
    padded = b"".join(source)
    if any(padded[length:]):
        raise Rejected("Nonzero content padding")
    return padded[:length], regenerated
