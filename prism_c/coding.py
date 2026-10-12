"""Dependency-free fixed 2-data + XOR-parity demonstrator, not a 4+2 codec."""

import hashlib

from .model import Rejected


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xor(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise Rejected("Unequal fragment lengths")
    return bytes(a ^ b for a, b in zip(left, right))


def encode(data: bytes) -> tuple[bytes, bytes, bytes]:
    size = max(1, (len(data) + 1) // 2)
    padded = data.ljust(size * 2, b"\x00")
    first, second = padded[:size], padded[size:]
    return first, second, xor(first, second)


def recover(rows: dict[int, bytes], length: int) -> tuple[bytes, tuple[bytes, bytes, bytes]]:
    if len(rows) < 2 or not set(rows) <= {0, 1, 2}:
        raise Rejected("Need two distinct valid code rows")
    if 0 in rows and 1 in rows:
        first, second = rows[0], rows[1]
    elif 0 in rows and 2 in rows:
        first, second = rows[0], xor(rows[0], rows[2])
    else:
        second, first = rows[1], xor(rows[1], rows[2])
    if len(first) != len(second) or length < 0 or length > len(first) * 2:
        raise Rejected("Invalid content/fragment length")
    return (first + second)[:length], (first, second, xor(first, second))
