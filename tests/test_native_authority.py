"""Portable independent device-state checks for the native journal authority.

Actual NVMe/process-fault evidence is collected separately by E21 on Linux.
"""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prism_c.model import Rejected
from prism_c.native_authority import NativeAuthority, NativeClient, Uncertain
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from prism_c.zoned_baseline import conventional_zoned_plan
from prism_c.zoned_campaign import zoned_fixture


class MemorySession:
    """Independent position/condition simulator; no production transition helpers."""
    def __init__(self, initial, descriptor):
        self.descriptor = str(descriptor)
        self.binding = {"session": "test-session", "serial": "test-controller", "boot_id": "test-boot",
                        "namespaces": {z.name: {"nsid": i+1, "capacity_units": z.capacity, "image": "memory"}
                                       for i, z in enumerate(initial.zones)}}
        self.store, self.bound, self.fence = None, None, 0
        self.data = {z.name: bytearray() for z in initial.zones}
        self.conditions = {z.name: 1 for z in initial.zones}
        self.operations = []

    def call(self, op, fence, **args):
        if op == "bind":
            if self.bound not in (None, self.store) or self.fence:
                raise Uncertain("Session already bound")
            self.bound = self.store
            return
        if self.store != self.bound:
            raise Uncertain("Wrong authority")
        if op == "fence":
            if fence < self.fence:
                raise Uncertain("Stale fence")
            self.fence = fence
            return
        if fence != self.fence:
            raise Uncertain("Stale command")
        name = args["zone"]
        capacity = self.binding["namespaces"][name]["capacity_units"]*4096
        data = self.data[name]
        if op == "report":
            return {"type": 2, "condition": self.conditions[name], "capacity_lba": capacity//512,
                    "start_lba": 0, "reported_zones": 1,
                    "wp_lba": (2**64-1 if self.conditions[name] == 14 else len(data)//512)}
        if op == "write":
            payload = bytes.fromhex(args["payload"])
            if args["offset"] != len(data) or len(data)+len(payload) > capacity or self.conditions[name] == 14:
                raise Uncertain("Wrong sequential position/capacity")
            data.extend(payload)
            self.conditions[name] = 14 if len(data) == capacity else (3 if self.conditions[name] == 3 else 2)
        elif op == "read":
            return bytes(data[args["offset"]:args["offset"]+args["length"]]).hex()
        elif op == "manage":
            action = args["action"]
            if action == 4:
                data.clear()
                self.conditions[name] = 1
            elif action == 3:
                self.conditions[name] = 3
            elif action == 1:
                self.conditions[name] = 4 if data else 1
            elif action == 2:
                self.conditions[name] = 14
            else:
                raise Uncertain("Unknown physical action")
        elif op != "flush":
            raise AssertionError(op)
        self.operations.append((op, name, args.get("action"), args.get("operation")))


class NativeAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make(self, profile=DEFAULT_PROFILE, extra=False, name="store"):
        initial = zoned_fixture(profile, extra=extra)
        contents = {s.name: bytes((i+19) % 251 for i in range(PROFILES[s.profile].data_rows*4096)) for s in initial.stripes}
        session = MemorySession(initial, self.root/"session.json")
        with patch("prism_c.native_authority.NativeClient", return_value=session):
            authority = NativeAuthority.create(self.root/name, initial, contents, session.descriptor)
        fence = authority.takeover()
        witness = conventional_zoned_plan(initial).witness
        authority.admit(witness, fence)
        return authority, session, fence, contents, witness

    def test_both_profiles_and_headroom_preserve_native_model_and_exact_bytes(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for extra in (False, True):
                with self.subTest(profile=profile, extra=extra):
                    authority, session, fence, contents, witness = self.make(profile, extra, f"{profile}-{extra}")
                    for cursor in range(len(witness.actions)):
                        authority.advance(fence, cursor)
                        authority = NativeAuthority(authority.root, session)
                        self.assertEqual(authority.read("object"), contents["object"])
                    self.assertTrue(authority.audit()["target"])
                    self.assertEqual(len(authority.receipts()), len(witness.actions))
                    self.assertEqual(sum(r["stage_bytes"] for r in authority.receipts()), 4096)
                    operations = len(session.operations)
                    authority.advance(fence, 0)
                    authority.execute(fence)
                    self.assertEqual(len(session.operations), operations)

    def test_completed_write_before_metadata_commit_is_adopted_once(self):
        authority, session, fence, contents, _ = self.make()
        def fail(kind, boundary):
            if (kind, boundary) == ("stage", "after_io"):
                raise RuntimeError("Actor exited after native completion")
        with self.assertRaises(RuntimeError):
            authority.execute(fence, fail)
        writes = sum(op[0] == "write" and op[3] != "bootstrap" for op in session.operations)
        self.assertEqual(writes, 2)
        authority = NativeAuthority(authority.root, session)
        new_fence = authority.takeover()
        with self.assertRaises(Rejected):
            authority.advance(fence)
        authority.execute(new_fence)
        self.assertEqual(sum(op[0] == "write" and op[3] != "bootstrap" for op in session.operations), writes)
        self.assertEqual(authority.read("object"), contents["object"])

    def test_partial_append_quarantines_without_rewind_or_free_credit(self):
        authority, session, fence, _, _ = self.make()
        def fail(kind, boundary):
            if (kind, boundary) == ("stage", "half_io"):
                raise RuntimeError("Actor exited after half append")
        with self.assertRaises(RuntimeError):
            authority.execute(fence, fail)
        sizes = {name: len(data) for name, data in session.data.items()}
        new_fence = authority.takeover()
        with self.assertRaises(Rejected):
            authority.execute(new_fence)
        self.assertTrue(authority.info()["quarantine"])
        self.assertTrue(all(r["appendable_units"] == 0 for r in authority.ledger().values()))
        self.assertEqual({name: len(data) for name, data in session.data.items()}, sizes)

    def test_altered_prepared_identity_is_rejected_before_device_mutation(self):
        authority, session, fence, _, _ = self.make()
        def fail(kind, boundary):
            if (kind, boundary) == ("stage", "after_prepare"):
                raise RuntimeError("Actor stopped with intent")
        with self.assertRaises(RuntimeError):
            authority.execute(fence, fail)
        with authority.transaction() as db:
            document = authority.load(db)
            document["pending"]["id"] = "altered"
            authority.save(db, document)
        operations = len(session.operations)
        with self.assertRaises(Rejected):
            authority.advance(fence)
        self.assertEqual(len(session.operations), operations)
        self.assertTrue(all(r["appendable_units"] == 0 for r in authority.ledger().values()))

    def test_descriptor_recreation_and_second_authority_are_not_silently_adopted(self):
        authority, session, _, _, _ = self.make()
        original = authority.info()["binding"]
        changed = {**original, "serial": "recreated-controller", "socket": "unused", "token": "unused"}
        descriptor = self.root/"changed-session.json"
        descriptor.write_text(json.dumps(changed))
        with self.assertRaises(Rejected):
            NativeClient(descriptor, original)
        other = MemorySession(zoned_fixture(), self.root/"other")
        other.binding["session"] = "another-session"
        with self.assertRaises(Rejected):
            NativeAuthority(authority.root, other)
        initial = zoned_fixture()
        with patch("prism_c.native_authority.NativeClient", return_value=session), self.assertRaises(Rejected):
            NativeAuthority.create(self.root/"second", initial, {"object": bytes(8192)}, session.descriptor)

    def test_invalid_cursor_and_changed_capacity_fail_closed(self):
        authority, session, fence, _, _ = self.make()
        for cursor in (-1, True, .5):
            with self.assertRaises(Rejected):
                authority.advance(fence, cursor)
        zone = authority.snapshot().zones[0]
        observed = session.call("report", fence, zone=zone.name)
        self.assertFalse(authority.matches(zone, {**observed, "capacity_lba": observed["capacity_lba"]+1}))
        self.assertFalse(authority.matches(replace(zone, incarnation=zone.incarnation+1), {**observed, "type": 1}))


if __name__ == "__main__":
    unittest.main()
