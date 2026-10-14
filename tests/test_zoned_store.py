import concurrent.futures
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

from prism_c.model import Rejected, SearchStatus
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from prism_c.zoned_baseline import conventional_zoned_plan, separated_gc_plan
from prism_c.zoned_campaign import zoned_fixture
from prism_c.zoned_fault import EXIT_CODE
from prism_c.zoned_model import ZExtent, ZStripe, ZZone, ZonedState, goal, replay
from prism_c.zoned_store import ZonedFileStore


def content(initial):
    return {s.name: bytes((i + sum(s.name.encode())) % 251
                          for i in range(PROFILES[s.profile].data_rows * 64)) for s in initial.stripes}


def make_store(root, profile=DEFAULT_PROFILE, control=False, extra=False):
    initial = zoned_fixture(profile, extra=extra)
    store = ZonedFileStore.create(root, initial, content(initial))
    fence = store.takeover()
    result = separated_gc_plan(initial) if control else conventional_zoned_plan(initial)
    assert result.status == SearchStatus.FOUND
    store.admit(result.witness, fence)
    return store, fence, result.witness, content(initial)


class ZonedStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "store"

    def tearDown(self):
        self.temp.cleanup()

    def test_actual_bytes_joint_control_and_parity_both_profiles(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for extra in (False, True):
                writes = []
                for control in (False, True):
                    with self.subTest(profile=profile, extra=extra, control=control):
                        root = Path(self.temp.name) / f"{profile}-{extra}-{control}"
                        store, fence, witness, contents = make_store(root, profile, control, extra)
                        for cursor in range(len(witness.actions)):
                            store.advance(fence, cursor)
                            for name, data in contents.items():
                                self.assertEqual(ZonedFileStore(root).read(name), data)
                            store.audit()
                        self.assertEqual(store.snapshot(), replay(zoned_fixture(profile, extra=extra), witness))
                        self.assertTrue(store.audit()["target"])
                        writes.append(sum(r["stage_bytes"] for r in store.receipts()))
                self.assertEqual(writes, [64, 64] if extra else [64, 128])

    def test_real_process_exits_reconcile_without_double_append_or_reset(self):
        boundaries = [(kind, boundary) for kind in ("stage", "reset_ack") for boundary in
                      ("before_prepare", "after_prepare", "before_io", "after_io", "before_commit", "after_commit")]
        boundaries += [("reset_request", b) for b in ("before_commit", "after_commit")]
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for kind, boundary in boundaries:
                with self.subTest(profile=profile, kind=kind, boundary=boundary):
                    root = Path(self.temp.name) / f"{profile}-{kind}-{boundary}"
                    store, fence, witness, contents = make_store(root, profile)
                    process = subprocess.run([sys.executable, "-m", "prism_c.zoned_fault", str(root),
                                              str(fence), kind, boundary], capture_output=True, text=True,
                                             timeout=45, cwd=Path(__file__).resolve().parents[1])
                    self.assertEqual(process.returncode, EXIT_CODE, process.stderr)
                    store = ZonedFileStore(root)
                    before = store.info()
                    for name, data in contents.items():
                        self.assertEqual(store.read(name), data)
                    if before["pending"]:
                        zone = before["pending"]["action"]["zone"]
                        ledger = store.ledger()[zone]
                        self.assertLessEqual(ledger["appendable_units"], ledger["capacity_units"] - ledger["charged_units"])
                        self.assertGreaterEqual(ledger["charged_units"], 1)
                        if kind == "reset_ack":
                            self.assertEqual(ledger["appendable_units"], 0)
                    newer = store.takeover()
                    with self.assertRaises(Rejected):
                        store.advance(fence)
                    store.execute(newer)
                    self.assertTrue(store.audit()["target"])
                    self.assertEqual(store.snapshot(), replay(zoned_fixture(profile), witness))
                    self.assertEqual(sum(r["stage_bytes"] for r in store.receipts()), 64)
                    self.assertEqual(len(store.receipts()), len(witness.actions))
                    self.assertEqual(store.ledger()["A"]["incarnation"], 2)
                    self.assertEqual(store.zone_path("A").stat().st_size, 64)
                    for name, data in contents.items():
                        self.assertEqual(store.read(name), data)

    def test_partial_process_append_quarantines_and_never_rewinds(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            with self.subTest(profile=profile):
                root = Path(self.temp.name) / profile
                store, fence, _, contents = make_store(root, profile)
                process = subprocess.run([sys.executable, "-m", "prism_c.zoned_fault", str(root), str(fence),
                                          "stage", "half_io"], capture_output=True, text=True, timeout=45,
                                         cwd=Path(__file__).resolve().parents[1])
                self.assertEqual(process.returncode, EXIT_CODE, process.stderr)
                store = ZonedFileStore(root)
                newer = store.takeover()
                before = store.info()
                self.assertEqual(store.zone_path("A").stat().st_size, 32)
                with self.assertRaisesRegex(Rejected, "quarantined"):
                    store.advance(newer)
                self.assertEqual(store.info()["cursor"], before["cursor"])
                self.assertIsNotNone(store.info()["pending"])
                self.assertTrue(ZonedFileStore(root).info()["quarantine"])
                self.assertTrue(all(z["appendable_units"] == 0 for z in store.ledger().values()))
                self.assertEqual(store.ledger()["A"]["charged_units"], 1)
                self.assertEqual(store.zone_path("A").stat().st_size, 32)
                self.assertEqual(store.read("object"), contents["object"])
                with self.assertRaises(Rejected):
                    store.execute(newer)

    def test_invalid_complete_pending_append_is_quarantined(self):
        store, fence, witness, _ = make_store(self.root)
        class Interrupted(Exception):
            pass
        def stop(kind, boundary):
            if (kind, boundary) == ("stage", "after_io"):
                raise Interrupted()
        with self.assertRaises(Interrupted):
            store.execute(fence, stop)
        path = store.zone_path("A")
        with path.open("r+b") as handle:
            handle.write(b"wrong")
        size = path.stat().st_size
        with self.assertRaisesRegex(Rejected, "quarantined"):
            store.advance(store.takeover())
        self.assertEqual(path.stat().st_size, size)
        self.assertFalse(goal(store.snapshot()))

    def test_corrupt_sources_and_staging_cannot_publish(self):
        for source in ("A", "X"):
            with self.subTest(source=source):
                store, fence, _, _ = make_store(Path(self.temp.name) / source)
                before = store.info()
                with store.zone_path(source).open("r+b") as handle:
                    handle.write(b"BAD")
                with self.assertRaisesRegex(Rejected, "Unauthentic"):
                    store.advance(fence)
                self.assertEqual(store.info()["cursor"], before["cursor"])

    def test_pending_reset_keeps_charge_and_open_active_tokens_until_ack(self):
        spec = ZStripe("object", ("S", "T", "X", "A"))
        initial = ZonedState((spec,), (ZZone("S", "S", 1, (ZExtent("LIVE", "object", 0),), "FULL"),
                                      ZZone("T", "T", 1, (ZExtent("LIVE", "object", 1),), "FULL"),
                                      ZZone("X", "X", 1, (ZExtent("LIVE", "object", 2),), "FULL"),
                                      ZZone("A", "A", 2, (ZExtent(),), "OPEN")), (("A", 2),))
        store = ZonedFileStore.create(self.root, initial, content(initial))
        fence = store.takeover()
        witness = conventional_zoned_plan(initial).witness
        store.admit(witness, fence)
        store.advance(fence)
        self.assertEqual(store.ledger()["A"]["phase"], "RESETTING")
        self.assertEqual(store.ledger()["A"]["charged_units"], 1)
        self.assertTrue(store.ledger()["A"]["open_token"])
        self.assertTrue(store.ledger()["A"]["active_token"])
        class Interrupted(Exception):
            pass
        def stop(kind, boundary):
            if boundary == "after_io":
                raise Interrupted()
        with self.assertRaises(Interrupted):
            store.advance(fence, hook=stop)
        self.assertEqual(store.ledger()["A"]["physical_bytes"], 0)
        self.assertEqual(store.ledger()["A"]["charged_units"], 1)
        self.assertEqual(store.ledger()["A"]["appendable_units"], 0)
        self.assertTrue(store.ledger()["A"]["open_token"])
        store.execute(store.takeover())
        self.assertEqual(store.ledger()["A"]["appendable_units"], 2)
        self.assertFalse(store.ledger()["A"]["active_token"])

    def test_duplicate_old_reset_cannot_erase_reused_incarnation(self):
        store, fence, witness, _ = make_store(self.root)
        store.execute(fence)
        before = store.zone_path("A").read_bytes()
        reset_cursor = next(i for i, a in enumerate(witness.actions) if a.kind == "reset_ack")
        result = store.advance(fence, reset_cursor)
        self.assertEqual(result["status"], "ALREADY_APPLIED")
        self.assertEqual(result["receipt"]["action"]["incarnation"], 1)
        self.assertEqual(store.ledger()["A"]["incarnation"], 2)
        self.assertEqual(store.zone_path("A").read_bytes(), before)
        with self.assertRaises(Rejected):
            store.advance(fence, len(witness.actions) + 1)

    def test_takeover_after_prepare_blocks_old_actor_before_file_io(self):
        store, fence, _, _ = make_store(self.root)
        newer = []
        def takeover(kind, boundary):
            if (kind, boundary) == ("reset_ack", "after_prepare"):
                newer.append(ZonedFileStore(self.root).takeover())
        with self.assertRaisesRegex(Rejected, "Stale authority"):
            store.execute(fence, takeover)
        self.assertEqual(store.zone_path("A").stat().st_size, 128)
        store.execute(newer[0])
        self.assertTrue(store.audit()["target"])

    def test_takeover_waits_for_io_transaction_and_authenticated_read_waits_for_reset(self):
        store, fence, _, contents = make_store(self.root)
        entered, release = threading.Event(), threading.Event()
        def block(kind, boundary):
            if (kind, boundary) == ("reset_ack", "before_io"):
                entered.set()
                if not release.wait(10):
                    raise AssertionError("Test failed to release physical I/O")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            writer = pool.submit(store.execute, fence, block)
            self.assertTrue(entered.wait(10))
            owner = pool.submit(store.takeover)
            reader = pool.submit(store.read, "object")
            self.assertFalse(owner.done())
            self.assertFalse(reader.done())
            release.set()
            newer = owner.result(timeout=15)
            self.assertEqual(reader.result(timeout=15), contents["object"])
            try:
                writer.result(timeout=15)
            except Rejected:
                pass  # Takeover may win any subsequent operation, never in-flight I/O.
        store.execute(newer)
        self.assertTrue(store.audit()["target"])

    def test_unsafe_witness_pins_grants_and_reservation_block_reset(self):
        for field in ("pins", "grants"):
            with self.subTest(field=field):
                initial = zoned_fixture()
                victim = initial.zones[0]
                victim = replace(victim, extents=(replace(victim.extents[0], **{field: 1}), victim.extents[1]))
                blocked = replace(initial, zones=(victim,) + initial.zones[1:])
                store = ZonedFileStore.create(Path(self.temp.name) / field, blocked, content(blocked))
                witness = conventional_zoned_plan(initial).witness
                with self.assertRaises(Rejected):
                    store.admit(replace(witness, initial=blocked.fingerprint()), store.takeover())
                self.assertEqual(store.zone_path("A").stat().st_size, 128)

    def test_fresh_root_controlled_paths_version_and_no_plaintext_fallback(self):
        initial = zoned_fixture()
        strange = "../nested/zone"
        initial = replace(initial, zones=tuple(replace(z, name=strange) if z.name == "A" else z for z in initial.zones),
                          reclaim=((strange, 1),))
        store = ZonedFileStore.create(self.root, initial, content(initial))
        self.assertEqual(store.zone_path(strange).parent, self.root / "zones")
        self.assertEqual(store.info()["format"], "prism-zoned-file-v1")
        self.assertEqual(set(store.info()["manifests"]["object"]), {"epoch", "profile", "length", "sha256", "rows"})
        with self.assertRaises(FileExistsError):
            ZonedFileStore.create(self.root, initial, content(initial))
        with self.assertRaises(Rejected):
            ZonedFileStore(Path(self.temp.name) / "absent")
        with closing(sqlite3.connect(store.db_path)) as db, db:
            doc = store.info()
            doc["format"] = "unknown-version"
            db.execute("UPDATE authority SET document=?", (json.dumps(doc),))
        with self.assertRaises(Rejected):
            ZonedFileStore(self.root)

    def test_two_objects_restore_from_files_with_different_commitments(self):
        zones = tuple(ZZone(name, name, 1, (ZExtent("LIVE", stripe, row, pins=1),), "FULL")
                      for name, stripe, row in (("S", "a", 0), ("T", "a", 1), ("U", "b", 0), ("V", "b", 1)))
        zones += (ZZone("X", "X", 1), ZZone("Y", "Y", 1))
        domains = tuple(z.domain for z in zones)
        initial = ZonedState((ZStripe("a", domains), ZStripe("b", domains)), zones)
        contents = content(initial)
        self.assertNotEqual(contents["a"], contents["b"])
        store = ZonedFileStore.create(self.root, initial, contents)
        fence = store.takeover()
        store.admit(conventional_zoned_plan(initial).witness, fence)
        store.execute(fence)
        self.assertTrue(store.audit()["target"])
        self.assertEqual(sum(r["stage_bytes"] for r in store.receipts()), 128)
        for name, data in contents.items():
            self.assertEqual(ZonedFileStore(self.root).read(name), data)

    def test_no_retired_hole_reuse_and_finished_tail_remains_unavailable(self):
        initial = zoned_fixture()
        # The all-dead zone has an earlier retired unit and a stranded finished tail.
        initial = replace(initial, zones=initial.zones + (ZZone("F", "F", 3, (ZExtent(),), "FINISHED"),))
        store = ZonedFileStore.create(self.root, initial, content(initial))
        self.assertEqual(store.ledger()["A"]["physical_bytes"], 128)
        self.assertEqual(store.ledger()["A"]["appendable_units"], 0)
        self.assertEqual(store.ledger()["F"]["appendable_units"], 0)
        fence = store.takeover()
        store.admit(conventional_zoned_plan(initial).witness, fence)
        store.execute(fence)
        self.assertEqual(store.zone_path("F").stat().st_size, 64)
        self.assertEqual(store.ledger()["F"]["appendable_units"], 0)

    def test_altered_pending_incarnation_cannot_reset(self):
        store, fence, _, _ = make_store(self.root)
        class Interrupted(Exception):
            pass
        def stop(kind, boundary):
            if (kind, boundary) == ("reset_ack", "after_prepare"):
                raise Interrupted()
        with self.assertRaises(Interrupted):
            store.execute(fence, stop)
        doc = store.info()
        doc["pending"]["action"]["incarnation"] += 1
        with closing(sqlite3.connect(store.db_path)) as db, db:
            db.execute("UPDATE authority SET document=?", (json.dumps(doc),))
        with self.assertRaisesRegex(Rejected, "binding"):
            store.advance(store.takeover())
        self.assertEqual(store.zone_path("A").stat().st_size, 128)


if __name__ == "__main__":
    unittest.main()
