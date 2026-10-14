"""Independent uniform-cost reference: no production transitions/goal/heuristic."""

from dataclasses import replace
import heapq
from itertools import count

from .model import Rejected, SearchStatus
from .profiles import PROFILES
from .zoned_model import ZAction, ZExtent, ZWitness


def _valid(s):
    if (type(s.stripes) is not tuple or type(s.zones) is not tuple
            or type(s.max_open) is not int or type(s.max_active) is not int
            or min(s.max_open, s.max_active) < 0):
        return False
    specs = {p.name: p for p in s.stripes}
    if not specs or not s.zones or len(specs) != len(s.stripes) or len({z.name for z in s.zones}) != len(s.zones):
        return False
    domains = {z.domain for z in s.zones}
    if (type(s.offline) is not tuple or len(set(s.offline)) != len(s.offline)
            or not set(s.offline) <= domains):
        return False
    for p in s.stripes:
        if (p.profile not in PROFILES or type(p.eligible) is not tuple or not p.eligible
                or len(set(p.eligible)) != len(p.eligible) or not set(p.eligible) <= domains
                or type(p.single_fault) is not bool):
            return False
    opens = active = 0
    for z in s.zones:
        if (type(z.capacity) is not int or z.capacity < 1 or type(z.extents) is not tuple
                or type(z.external_hold) is not int or z.external_hold < 0
                or z.incarnation < 1 or len(z.extents) + z.external_hold + int(z.reservation is not None) > z.capacity):
            return False
        if z.phase not in ("EMPTY", "OPEN", "CLOSED", "FULL", "FINISHED", "RESETTING"):
            return False
        if z.phase == "EMPTY" and z.extents or z.phase == "FULL" and len(z.extents) != z.capacity:
            return False
        if z.phase in ("OPEN", "CLOSED") and len(z.extents) == z.capacity or z.phase == "CLOSED" and not z.extents:
            return False
        if z.phase == "RESETTING":
            if (z.reset_prior not in ("OPEN", "CLOSED", "FULL", "FINISHED") or not z.extents
                    or z.reservation or z.external_hold
                    or any(e.status != "RETIRED" or e.pins or e.grants for e in z.extents)):
                return False
            phase = z.reset_prior
            if phase == "FULL" and len(z.extents) != z.capacity or phase in ("OPEN", "CLOSED") and len(z.extents) == z.capacity:
                return False
        else:
            if z.reset_prior:
                return False
            phase = z.phase
        opens += phase == "OPEN"
        active += phase in ("OPEN", "CLOSED")
        if z.reservation is not None:
            if (z.phase != "OPEN" or z.reservation[0] not in specs
                    or type(z.reservation[1]) is not int
                    or z.reservation[1] not in range(PROFILES[specs[z.reservation[0]].profile].total_rows)):
                return False
        for e in z.extents:
            if (e.status not in ("LIVE", "STAGED", "RETIRED") or min(e.pins, e.grants) < 0
                    or type(e.pins) is not int or type(e.grants) is not int):
                return False
            if e.stripe:
                if e.stripe not in specs or e.row not in range(PROFILES[specs[e.stripe].profile].total_rows):
                    return False
            elif e.status != "RETIRED" or e.row != -1:
                return False
    if opens > s.max_open or active > s.max_active:
        return False
    for p in s.stripes:
        if p.profile not in PROFILES or not p.eligible:
            return False
        copies = sum(e.status != "RETIRED" and e.stripe == p.name for z in s.zones for e in z.extents)
        copies += sum(z.reservation is not None and z.reservation[0] == p.name for z in s.zones)
        if copies > PROFILES[p.profile].total_rows + 1:
            return False
    return True


def _safe(s):
    for p in s.stripes:
        checks = [None]
        if p.single_fault:
            checks.extend(sorted({z.domain for z in s.zones if z.domain not in s.offline}))
        for failed in checks:
            rows = set()
            for z in s.zones:
                if z.domain in s.offline or z.domain == failed:
                    continue
                for e in z.extents:
                    if e.status == "LIVE" and e.stripe == p.name:
                        rows.add(e.row)
            if len(rows) < PROFILES[p.profile].data_rows:
                return False
    return True


def _done(s):
    for z in s.zones:
        if z.reservation is not None or z.phase == "RESETTING" or any(e.status == "STAGED" for e in z.extents):
            return False
    for name, units in s.reclaim:
        z = next(z for z in s.zones if z.name == name)
        free = 0 if z.phase in ("FULL", "FINISHED", "RESETTING") else z.capacity - len(z.extents) - z.external_hold
        if free < units or z.domain in s.offline:
            return False
    for p in s.stripes:
        rows, domains, total = set(), set(), 0
        for z in s.zones:
            for e in z.extents:
                if e.status == "LIVE" and e.stripe == p.name:
                    if z.domain not in p.eligible or z.domain in s.offline:
                        return False
                    total += 1
                    rows.add(e.row)
                    domains.add(z.domain)
        n = PROFILES[p.profile].total_rows
        if total != n or rows != set(range(n)) or len(domains) != n:
            return False
    return True


def _key(s):
    return (s.stripes, tuple((z.name, z.domain, z.capacity, z.phase, z.external_hold,
                             z.reservation, z.reset_prior, z.extents) for z in s.zones),
            s.offline, s.reclaim, s.max_open, s.max_active)


def reference_successors(s):
    for i, z in enumerate(s.zones):
        changes = []
        online = z.domain not in s.offline
        if online:
            if z.phase in ("EMPTY", "CLOSED") and z.capacity - len(z.extents) - z.external_hold > 0:
                changes.append((ZAction("open", z.name, z.incarnation), replace(z, phase="OPEN")))
            if z.phase == "OPEN" and z.reservation is None:
                changes.append((ZAction("close", z.name, z.incarnation), replace(z, phase="CLOSED" if z.extents else "EMPTY")))
            if z.phase in ("OPEN", "CLOSED") and z.reservation is None and not z.external_hold and z.extents:
                changes.append((ZAction("finish", z.name, z.incarnation), replace(z, phase="FINISHED")))
            if (z.phase != "RESETTING" and z.extents and not z.reservation and not z.external_hold
                    and all(e.status == "RETIRED" and not e.pins and not e.grants for e in z.extents)):
                changes.append((ZAction("reset_request", z.name, z.incarnation), replace(z, phase="RESETTING", reset_prior=z.phase)))
            if z.phase == "RESETTING":
                changes.append((ZAction("reset_ack", z.name, z.incarnation),
                                replace(z, phase="EMPTY", extents=(), incarnation=z.incarnation + 1, reset_prior="")))
            if z.phase == "OPEN":
                if z.reservation is None:
                    if len(z.extents) + z.external_hold < z.capacity:
                        for p in s.stripes:
                            if z.domain not in p.eligible:
                                continue
                            for row in range(PROFILES[p.profile].total_rows):
                                if any(e.status != "RETIRED" and (e.stripe, e.row) == (p.name, row) for e in z.extents):
                                    continue
                                changes.append((ZAction("reserve", z.name, z.incarnation, stripe=p.name, row=row),
                                                replace(z, reservation=(p.name, row))))
                else:
                    name, row = z.reservation
                    p = next(p for p in s.stripes if p.name == name)
                    source_rows = {e.row for src in s.zones if src.domain not in s.offline for e in src.extents
                                   if e.status == "LIVE" and e.stripe == name}
                    if len(source_rows) >= PROFILES[p.profile].data_rows:
                        written = z.extents + (ZExtent("STAGED", name, row),)
                        changes.append((ZAction("stage", z.name, z.incarnation, stripe=name, row=row),
                                        replace(z, extents=written, reservation=None, phase="FULL" if len(written) == z.capacity else "OPEN")))
        if z.phase != "RESETTING":
            for j, e in enumerate(z.extents):
                kinds = []
                if online and e.status == "STAGED":
                    p = next(p for p in s.stripes if p.name == e.stripe)
                    if z.domain in p.eligible:
                        kinds.append(("promote", "LIVE"))
                    if not e.pins and not e.grants:
                        kinds.append(("discard", "RETIRED"))
                if e.status == "LIVE" and not e.pins and not e.grants:
                    kinds.append(("retire", "RETIRED"))
                for kind, status in kinds:
                    ex = list(z.extents)
                    ex[j] = replace(e, status=status)
                    changes.append((ZAction(kind, z.name, z.incarnation, j), replace(z, extents=tuple(ex))))
        for action, zone in changes:
            zones = list(s.zones)
            zones[i] = zone
            after = replace(s, zones=tuple(zones))
            if _valid(after) and _safe(after):
                yield action, after


def oracle_replay(initial, witness):
    if witness.initial != initial.fingerprint() or not _valid(initial) or not _safe(initial):
        raise Rejected("Reference rejects initial witness")
    s = initial
    for action in witness.actions:
        match = next((after for allowed, after in reference_successors(s) if allowed == action), None)
        if match is None:
            raise Rejected("Reference rejects action")
        s = match
    if not _done(s):
        raise Rejected("Reference rejects terminal target")
    return s


def zoned_oracle(initial, max_states=20000):
    if not _valid(initial):
        raise Rejected("Invalid oracle scope")
    if type(max_states) is not int or max_states < 0:
        raise ValueError("Invalid reference budget")
    if not _safe(initial):
        return SearchStatus.INFEASIBLE, None, None, 0
    for spec in initial.stripes:
        possible = {z.domain for z in initial.zones if z.domain in spec.eligible and z.domain not in initial.offline}
        if len(possible) < PROFILES[spec.profile].total_rows:
            return SearchStatus.INFEASIBLE, None, None, 0
    for name, units in initial.reclaim:
        z = next(z for z in initial.zones if z.name == name)
        available = 0 if z.phase in ("FULL", "FINISHED", "RESETTING") else z.capacity - len(z.extents) - z.external_hold - int(z.reservation is not None)
        if available < units and (z.external_hold or any(e.pins or e.grants for e in z.extents)):
            return SearchStatus.INFEASIBLE, None, None, 0
    order = count()
    heap = [(0, 0, next(order), initial, ())]
    visited = {_key(initial): (0, 0)}
    explored = 0
    while heap:
        writes, length, _, s, path = heapq.heappop(heap)
        if visited.get(_key(s)) != (writes, length):
            continue
        if explored >= max_states:
            return SearchStatus.UNKNOWN, None, None, explored
        explored += 1
        if _done(s):
            return SearchStatus.FOUND, ZWitness(initial.fingerprint(), path), (writes, length), explored
        for action, after in reference_successors(s):
            cost = writes + (action.kind == "stage"), length + 1
            key = _key(after)
            if key in visited and visited[key] <= cost:
                continue
            visited[key] = cost
            heapq.heappush(heap, (*cost, next(order), after, path + (action,)))
    return SearchStatus.INFEASIBLE, None, None, explored
