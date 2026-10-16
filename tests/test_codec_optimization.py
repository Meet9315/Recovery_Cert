"""Independent field/codec checks and pre-optimization byte layout compatibility."""

import itertools
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from prism_c.coding import combine, encode, gf_mul, recover, xor
from prism_c.coding_oracle import MATRIX, linear, multiply
from prism_c.model import Rejected, profile_spec
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.zoned_store import ZonedFileStore
from tests.test_zoned_store import make_store


def independent_encode(data, profile):
    matrix = ((1, 0), (0, 1), (1, 1)) if profile == DEFAULT_PROFILE else MATRIX
    k = len(matrix[0])
    size = max(1, (len(data) + k - 1) // k)
    padded = data + bytes(k * size - len(data))
    fragments = tuple(padded[i * size:(i+1) * size] for i in range(k))
    return tuple(linear(row, fragments) for row in matrix)


def legacy_encode(data, profile):
    # The previous bytewise algorithm, used only to construct compatible stores.
    code = profile_spec(profile)
    size = max(1, (len(data) + code.data_rows - 1) // code.data_rows)
    padded = data.ljust(size * code.data_rows, b"\x00")
    fragments = tuple(padded[i * size:(i+1) * size] for i in range(code.data_rows))
    rows = []
    for coefficients in code.generator:
        output = bytearray(size)
        for coefficient, fragment in zip(coefficients, fragments):
            if coefficient:
                for i, value in enumerate(fragment):
                    output[i] ^= gf_mul(coefficient, value)
        rows.append(bytes(output))
    return tuple(rows)


class CodecOptimizationTests(unittest.TestCase):
    def test_every_field_product_through_actual_transform_path(self):
        values = bytes(range(256))
        for coefficient in range(256):
            self.assertEqual(combine((coefficient,), (values,)), bytes(multiply(coefficient, v) for v in values))
        self.assertEqual(combine((0, 0), (b"abc", b"xyz")), b"\x00" * 3)
        self.assertEqual(combine((1, 0), (b"\x00\x01\xff", b"xyz")), b"\x00\x01\xff")

    def test_all_supported_bases_and_redundant_subsets_against_independent_encoder(self):
        rng = random.Random(20261016)
        for profile, k, n in ((DEFAULT_PROFILE, 2, 3), (FOUR_PLUS_TWO, 4, 6)):
            for length in (0, 1, 3, 17, 257, 1025, 16385):
                data = rng.randbytes(length)
                expected = independent_encode(data, profile)
                self.assertEqual(encode(data, profile), expected)
                for count in range(k, n+1):
                    for basis in itertools.combinations(range(n), count):
                        with self.subTest(profile=profile, length=length, basis=basis):
                            self.assertEqual(recover({i: expected[i] for i in basis}, length, profile), (data, expected))

    def test_redundant_corruption_and_nonzero_padding_remain_rejected(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            with self.subTest(profile=profile):
                rows = encode(b"integrity boundary\xff", profile)
                damaged = {i: row for i, row in enumerate(rows)}
                damaged[len(rows)-1] = rows[-1][:-1] + bytes([rows[-1][-1] ^ 1])
                with self.assertRaises(Rejected):
                    recover(damaged, 19, profile)
                nonzero = encode(b"data\xff", profile)
                with self.assertRaises(Rejected):
                    recover(dict(enumerate(nonzero)), 4, profile)

    def test_buffer_xor_preserves_zero_high_bytes_and_rejects_unequal_lengths(self):
        rng = random.Random(8021)
        for size in (0, 1, 3, 257, 4096, 1024*1024):
            a, b = rng.randbytes(size), rng.randbytes(size)
            self.assertEqual(xor(a, b), bytes(x ^ y for x, y in zip(a, b)))
            self.assertEqual(xor(a, a), bytes(size))
        with self.assertRaises(Rejected):
            xor(b"ab", b"a")

    def test_legacy_encoded_durable_store_reopens_and_repairs_with_optimized_codec(self):
        with tempfile.TemporaryDirectory() as temp:
            for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
                with self.subTest(profile=profile):
                    root = Path(temp) / profile
                    with patch("prism_c.zoned_store.encode", side_effect=legacy_encode):
                        store, fence, witness, contents = make_store(root, profile)
                    store = ZonedFileStore(root)
                    for name, data in contents.items():
                        self.assertEqual(store.read(name), data)
                    store.execute(fence)
                    self.assertTrue(ZonedFileStore(root).audit()["target"])
                    self.assertEqual(len(store.receipts()), len(witness.actions))
                    for name, data in contents.items():
                        self.assertEqual(ZonedFileStore(root).read(name), data)


if __name__ == "__main__":
    unittest.main()
