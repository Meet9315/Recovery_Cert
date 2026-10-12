import json
from pathlib import Path
import tempfile
import unittest

from prism_c.coding import digest
from prism_c.controller_benchmark import _fixture
from prism_c.model import Rejected
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO


class ReadReuseTests(unittest.TestCase):
    def test_missing_row_identity_is_checked_before_returning_decoded_content(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for api in ("read", "read_snapshot"):
                with self.subTest(profile=profile, api=api), tempfile.TemporaryDirectory() as tmp:
                    store, _, _, _ = _fixture(Path(tmp) / "store", 2, profile, False, 112, "conventional_cached")
                    with store._transaction() as db:
                        record = db.execute("SELECT * FROM stripes WHERE name='stripe-00'").fetchone()
                        hashes = json.loads(record["row_digests"])
                        hashes[1 if profile == FOUR_PLUS_TWO else 2] = "wrong missing-row identity"
                        db.execute("UPDATE stripes SET row_digests=? WHERE name='stripe-00'", (json.dumps(hashes),))
                    with self.assertRaisesRegex(Rejected, "Source content identity mismatch"):
                        getattr(store, api)("stripe-00")

    def test_authentic_but_inconsistent_extra_row_is_not_ignored(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for api in ("read", "read_snapshot"):
                with self.subTest(profile=profile, api=api), tempfile.TemporaryDirectory() as tmp:
                    from prism_c.baseline import conventional_plan
                    store, fence, _, _ = _fixture(Path(tmp) / "store", 2, profile, False, 113, "conventional_cached")
                    store.execute(store.admit(conventional_plan(store.snapshot()), fence), fence)
                    with store._transaction() as db:
                        spec = db.execute("SELECT * FROM stripes WHERE name='stripe-00'").fetchone()
                        record = db.execute("SELECT * FROM slots WHERE stripe='stripe-00' AND status='LIVE' ORDER BY row DESC LIMIT 1").fetchone()
                        raw = bytearray(store._io(db, record)[:spec["fragment_size"]])
                        raw[0] ^= 1
                        store._io(db, record, bytes(raw))
                        altered_digest = digest(bytes(raw))
                        hashes = json.loads(spec["row_digests"])
                        hashes[record["row"]] = altered_digest
                        db.execute("UPDATE stripes SET row_digests=? WHERE name='stripe-00'", (json.dumps(hashes),))
                        db.execute("UPDATE slots SET digest=? WHERE key=?", (altered_digest, record["key"]))
                    with self.assertRaisesRegex(Rejected, "inconsistent"):
                        getattr(store, api)("stripe-00")

    def test_empty_odd_and_multislot_sized_contents_match_through_both_read_apis(self):
        from prism_c.storage import Authority
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for length in (0, 1, 1025, 65537):
                with self.subTest(profile=profile, length=length), tempfile.TemporaryDirectory() as tmp:
                    rows = 6 if profile == FOUR_PLUS_TWO else 3
                    domains = tuple(f"D{i}" for i in range(rows))
                    store = Authority.create(Path(tmp) / "store", dict.fromkeys(domains, 1), 65536)
                    content = bytes((i * 17 + 3) % 256 for i in range(length))
                    store.bootstrap("object", content, dict(enumerate(domains)), domains, store.takeover(), profile)
                    self.assertEqual(store.read("object"), content)
                    self.assertEqual(store.read_snapshot("object"), content)
