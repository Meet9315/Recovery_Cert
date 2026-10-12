import concurrent.futures
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from prism_c.baseline import conventional_plan
from prism_c.checker import replay
from prism_c.controller_benchmark import _fixture
from prism_c.model import Action, Rejected, Witness
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.storage import Authority
from tests.test_storage import make_store


class SnapshotReadTests(unittest.TestCase):
    def test_read_completes_during_writer_and_sees_only_committed_offline_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _ = make_store(Path(tmp) / "store")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                with store._transaction() as db:
                    db.execute("UPDATE settings SET value='[\"S\",\"T\"]' WHERE key='offline'")
                    future = pool.submit(store.read_snapshot, "A")
                    self.assertEqual(future.result(timeout=2), b"immutable object A with an odd length!")
            with self.assertRaises(Rejected):
                store.read_snapshot("A")

    def test_read_connection_rejects_writes_and_releases_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence = make_store(Path(tmp) / "store")
            with self.assertRaises(sqlite3.OperationalError):
                with store._read_transaction() as db:
                    self.assertEqual(db.execute("PRAGMA query_only").fetchone()[0], 1)
                    db.execute("UPDATE settings SET value='99' WHERE key='fence'")
            self.assertEqual(store.takeover(), fence + 1)

    def test_both_coding_profiles_and_worker_paths_return_exact_bytes(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                with self.subTest(profile=profile, workers=workers), tempfile.TemporaryDirectory() as tmp:
                    store, fence, contents, _ = _fixture(Path(tmp) / "store", 2, profile, workers, 81, "shadow")
                    for name, data in contents.items():
                        self.assertEqual(store.read_snapshot(name), data)
                    identifier = store.admit(conventional_plan(store.snapshot()), fence)
                    while store.plan_info(identifier)["status"] == "ACTIVE":
                        store.step(identifier, fence)
                        for name, data in contents.items():
                            self.assertEqual(store.read_snapshot(name), data)
                    self.assertTrue(Authority(store.root).audit()["target"])

    def test_actual_retire_reclaim_race_falls_back_after_closing_old_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence = make_store(Path(tmp) / "store")
            store.execute(store.admit(conventional_plan(store.snapshot()), fence), fence)
            initial = store.snapshot()
            slot = next(s for s in initial.slots if s.stripe == "A" and s.row == 2)
            actions = (Action("retire", slot.key, "A", 2, slot.incarnation),
                       Action("reclaim", slot.key, "A", 2, slot.incarnation),
                       Action("reserve", slot.key, "A", 2, slot.incarnation),
                       Action("stage", slot.key, "A", 2, slot.incarnation + 1),
                       Action("promote", slot.key, "A", 2, slot.incarnation + 1))
            witness = Witness(initial.fingerprint(), actions, replay(initial, actions).fingerprint())
            identifier = store.admit(witness, fence)
            writer, original_io, raced = Authority(store.root), store._io, []
            def reading(db, record, data=None):
                if not raced and data is None and record["key"] == slot.key:
                    raced.append(True)
                    writer.step(identifier, fence)
                    writer.step(identifier, fence)
                return original_io(db, record, data)
            with patch.object(store, "_io", side_effect=reading), patch.object(store, "read", wraps=store.read) as fallback:
                self.assertEqual(store.read_snapshot("A"), b"immutable object A with an odd length!")
                self.assertEqual(fallback.call_count, 1)
            self.assertEqual(raced, [True])
            self.assertEqual(writer.plan_info(identifier)["cursor"], 2)
            writer.execute(identifier, fence)
            self.assertTrue(writer.audit()["target"])

    def test_corruption_and_identity_mismatch_still_reject_with_one_fallback(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for kind in ("source", "identity"):
                with self.subTest(profile=profile, kind=kind), tempfile.TemporaryDirectory() as tmp:
                    store, _, _, _ = _fixture(Path(tmp) / "store", 2, profile, False, 83, "conventional_cached")
                    with store._transaction() as db:
                        if kind == "source":
                            record = db.execute("SELECT * FROM slots WHERE stripe='stripe-00' AND status='LIVE' LIMIT 1").fetchone()
                            store._io(db, record, b"corrupt")
                        else:
                            db.execute("UPDATE stripes SET content_digest='wrong' WHERE name='stripe-00'")
                    with patch.object(store, "read", wraps=store.read) as fallback, self.assertRaises(Rejected):
                        store.read_snapshot("stripe-00")
                    self.assertEqual(fallback.call_count, 1)

    def test_unknown_content_rejects_and_other_io_errors_are_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _ = make_store(Path(tmp) / "store")
            with self.assertRaises(Rejected):
                store.read_snapshot("missing")
            with patch.object(store, "_io", side_effect=OSError("device unavailable")), \
                 patch.object(store, "read", wraps=store.read) as fallback, self.assertRaises(OSError):
                store.read_snapshot("A")
            self.assertEqual(fallback.call_count, 0)
