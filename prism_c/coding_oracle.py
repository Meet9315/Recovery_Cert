"""Independent 4+2 research oracle: polynomial arithmetic and cofactors.

No production codec/profile helpers are imported. This is deliberately slow
verification code, not the runtime encoder or decoder.
"""

import itertools

MATRIX = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1),
          (1, 1, 1, 1), (1, 2, 4, 8))


def multiply(left, right):
    polynomial = 0
    for power in range(8):
        if right & (1 << power):
            polynomial ^= left << power
    for power in range(14, 7, -1):
        if polynomial & (1 << power):
            polynomial ^= 0x11D << (power - 8)
    return polynomial


def determinant(matrix):
    result = 0
    for permutation in itertools.permutations(range(len(matrix))):
        term = 1
        for row, column in enumerate(permutation):
            term = multiply(term, matrix[row][column])
        result ^= term  # In characteristic two, every permutation sign is +1.
    return result


def inverse(matrix):
    value = determinant(matrix)
    if value == 0:
        raise ValueError("Oracle singular minor")
    reciprocal = next(candidate for candidate in range(1, 256) if multiply(value, candidate) == 1)
    size = len(matrix)
    return tuple(tuple(multiply(reciprocal, determinant(tuple(
        tuple(matrix[row][column] for column in range(size) if column != i)
        for row in range(size) if row != j))) for j in range(size)) for i in range(size))


def linear(coefficients, fragments):
    output = []
    for position in range(len(fragments[0])):
        value = 0
        for column in range(len(coefficients)):
            value ^= multiply(coefficients[column], fragments[column][position])
        output.append(value)
    return bytes(output)


def oracle_encode(data):
    size = max(1, (len(data) + 3) // 4)
    padded = data + bytes(size * 4 - len(data))
    sources = tuple(padded[i * size:(i + 1) * size] for i in range(4))
    return tuple(linear(row, sources) for row in MATRIX)


def oracle_recover(rows, length):
    chosen = sorted(rows)
    if len(chosen) != 4:
        raise ValueError("Oracle needs exactly four selected rows")
    coefficients = inverse(tuple(MATRIX[row] for row in chosen))
    fragments = tuple(rows[row] for row in chosen)
    sources = tuple(linear(row, fragments) for row in coefficients)
    return b"".join(sources)[:length]
