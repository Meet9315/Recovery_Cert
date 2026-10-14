"""Bounded joint zoned repair/GC model; no physical or durable I/O."""

from dataclasses import asdict, dataclass, replace
import hashlib
import json

from .model import Rejected
from .profiles import DEFAULT_PROFILE, PROFILES


@dataclass(frozen=True)
class ZStripe:
    name: str
    eligible: tuple[str, ...]
    profile: str = DEFAULT_PROFILE
    single_fault: bool = False

    @property
    def code(self):
        return PROFILES[self.profile]


@dataclass(frozen=True)
class ZExtent:
    status: str = "RETIRED"
    stripe: str = ""
    row: int = -1
    pins: int = 0
    grants: int = 0


@dataclass(frozen=True)
class ZZone:
    name: str
    domain: str
    capacity: int
    extents: tuple[ZExtent, ...] = ()
    phase: str = "EMPTY"
    incarnation: int = 1
    external_hold: int = 0
    reservation: tuple[str, int] | None = None
    reset_prior: str = ""

    def uses_open(self):
        return self.phase == "OPEN" or self.phase == "RESETTING" and self.reset_prior == "OPEN"

    def uses_active(self):
        return self.phase in ("OPEN", "CLOSED") or self.phase == "RESETTING" and self.reset_prior in ("OPEN", "CLOSED")

    def appendable(self):
        if self.phase in ("FULL", "FINISHED", "RESETTING"):
            return 0
        return self.capacity - len(self.extents) - self.external_hold - int(self.reservation is not None)


@dataclass(frozen=True)
class ZAction:
    kind: str
    zone: str
    incarnation: int
    offset: int = -1
    stripe: str = ""
    row: int = -1


@dataclass(frozen=True)
class ZonedState:
    stripes: tuple[ZStripe, ...]
    zones: tuple[ZZone, ...]
    reclaim: tuple[tuple[str, int], ...] = ()
    offline: tuple[str, ...] = ()
    max_open: int = 1
    max_active: int = 1

    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

    def key(self):
        # Incarnations affect command validity but not future nominal feasibility.
        # Witness replay still checks exact incarnations and initial fingerprint.
        return (self.stripes, tuple((z.name, z.domain, z.capacity, z.extents, z.phase,
                                    z.external_hold, z.reservation, z.reset_prior) for z in self.zones),
                self.reclaim, self.offline, self.max_open, self.max_active)


@dataclass(frozen=True)
class ZWitness:
    initial: str
    actions: tuple[ZAction, ...]

    def to_dict(self):
        return asdict(self)


def validate(state):
    if (type(state.stripes) is not tuple or type(state.zones) is not tuple
            or type(state.reclaim) is not tuple or type(state.offline) is not tuple
            or type(state.max_open) is not int or type(state.max_active) is not int
            or min(state.max_open, state.max_active) < 0
            or not state.stripes or not state.zones):
        raise Rejected("Invalid immutable zoned scope")
    specs = {s.name: s for s in state.stripes}
    names = {z.name for z in state.zones}
    domains = {z.domain for z in state.zones}
    if len(specs) != len(state.stripes) or len(names) != len(state.zones):
        raise Rejected("Duplicate scope identity")
    if len(set(state.offline)) != len(state.offline) or not set(state.offline) <= domains:
        raise Rejected("Unknown/duplicate offline domain")
    for spec in state.stripes:
        if (not isinstance(spec.name, str) or not spec.name or spec.profile not in PROFILES
                or type(spec.eligible) is not tuple or not spec.eligible
                or len(set(spec.eligible)) != len(spec.eligible)
                or not set(spec.eligible) <= domains or type(spec.single_fault) is not bool):
            raise Rejected("Invalid coding/placement contract")
    for zone in state.zones:
        if (not isinstance(zone.name, str) or not zone.name or not isinstance(zone.domain, str) or not zone.domain
                or type(zone.capacity) is not int or zone.capacity < 1
                or type(zone.incarnation) is not int or zone.incarnation < 1
                or type(zone.extents) is not tuple or len(zone.extents) > zone.capacity
                or type(zone.external_hold) is not int or zone.external_hold < 0
                or zone.phase not in ("EMPTY", "OPEN", "CLOSED", "FULL", "FINISHED", "RESETTING")):
            raise Rejected("Invalid zone geometry/phase")
        if (zone.phase == "EMPTY" and zone.extents or zone.phase == "FULL" and len(zone.extents) != zone.capacity
                or zone.phase in ("OPEN", "CLOSED") and len(zone.extents) == zone.capacity
                or zone.phase == "CLOSED" and not zone.extents
                or zone.phase == "RESETTING" and (not zone.extents or zone.external_hold or zone.reservation)):
            raise Rejected("Phase/write-pointer contradiction")
        if (zone.phase == "RESETTING" and zone.reset_prior not in ("OPEN", "CLOSED", "FULL", "FINISHED")
                or zone.phase != "RESETTING" and zone.reset_prior):
            raise Rejected("Reset token provenance is missing or stale")
        if zone.phase == "RESETTING" and (zone.reset_prior == "FULL" and len(zone.extents) != zone.capacity
                or zone.reset_prior in ("OPEN", "CLOSED") and len(zone.extents) == zone.capacity):
            raise Rejected("Pending reset has contradictory prior geometry")
        if zone.reservation is not None:
            if (type(zone.reservation) is not tuple or len(zone.reservation) != 2
                    or zone.phase != "OPEN" or zone.reservation[0] not in specs
                    or type(zone.reservation[1]) is not int
                    or zone.reservation[1] not in range(specs[zone.reservation[0]].code.total_rows)):
                raise Rejected("Invalid append reservation")
        if len(zone.extents) + zone.external_hold + int(zone.reservation is not None) > zone.capacity:
            raise Rejected("Append budget overcommitted")
        for extent in zone.extents:
            if (extent.status not in ("LIVE", "STAGED", "RETIRED")
                    or type(extent.pins) is not int or type(extent.grants) is not int
                    or min(extent.pins, extent.grants) < 0):
                raise Rejected("Invalid extent/reference record")
            if extent.stripe:
                if (extent.stripe not in specs or type(extent.row) is not int
                        or extent.row not in range(specs[extent.stripe].code.total_rows)):
                    raise Rejected("Invalid coding row")
            elif extent.status != "RETIRED" or extent.row != -1:
                raise Rejected("Unbound retained extent")
        if zone.phase == "RESETTING" and any(e.status != "RETIRED" or e.pins or e.grants for e in zone.extents):
            raise Rejected("Reset pending with retained dependencies")
    if sum(z.uses_open() for z in state.zones) > state.max_open:
        raise Rejected("Open-zone limit exceeded")
    if sum(z.uses_active() for z in state.zones) > state.max_active:
        raise Rejected("Active-zone limit exceeded")
    if len({name for name, _ in state.reclaim}) != len(state.reclaim):
        raise Rejected("Duplicate reclamation goal")
    for name, units in state.reclaim:
        if name not in names or type(units) is not int or not 1 <= units <= next(z.capacity for z in state.zones if z.name == name):
            raise Rejected("Invalid required appendable goal")
    for spec in state.stripes:
        working = sum(e.stripe == spec.name and e.status != "RETIRED" for z in state.zones for e in z.extents)
        working += sum(z.reservation is not None and z.reservation[0] == spec.name for z in state.zones)
        if working > spec.code.total_rows + 1:
            raise Rejected("Bounded working-copy limit exceeded")


def protected(state):
    for spec in state.stripes:
        faults = (None,) + (tuple(sorted({z.domain for z in state.zones} - set(state.offline))) if spec.single_fault else ())
        for fault in faults:
            rows = {e.row for z in state.zones if z.domain not in state.offline and z.domain != fault
                    for e in z.extents if e.status == "LIVE" and e.stripe == spec.name}
            if len(rows) < spec.code.data_rows:
                return False
    return True


def goal(state, repair=True):
    if any(z.reservation or z.phase == "RESETTING" for z in state.zones):
        return False
    if any(e.status == "STAGED" for z in state.zones for e in z.extents):
        return False
    for name, units in state.reclaim:
        zone = next(z for z in state.zones if z.name == name)
        if zone.domain in state.offline or zone.appendable() < units:
            return False
    if repair:
        for spec in state.stripes:
            live = [(e.row, z.domain) for z in state.zones for e in z.extents if e.stripe == spec.name and e.status == "LIVE"]
            if (len(live) != spec.code.total_rows or {r for r, _ in live} != set(range(spec.code.total_rows))
                    or len({d for _, d in live}) != len(live)
                    or any(d not in spec.eligible or d in state.offline for _, d in live)):
                return False
    return True


def step(state, action):
    validate(state)
    zones = list(state.zones)
    index = next((i for i, z in enumerate(zones) if z.name == action.zone), None)
    if index is None or action.incarnation != zones[index].incarnation:
        raise Rejected("Unknown zone or stale incarnation")
    zone = zones[index]
    kind = action.kind
    if kind != "retire" and zone.domain in state.offline:
        raise Rejected("Physical operation targets offline domain")
    if zone.phase == "RESETTING" and kind != "reset_ack":
        raise Rejected("Pending reset excludes other mutations")
    if kind == "open":
        if zone.phase not in ("EMPTY", "CLOSED") or zone.appendable() < 1:
            raise Rejected("Zone cannot open")
        zone = replace(zone, phase="OPEN")
    elif kind == "close":
        if zone.phase != "OPEN" or zone.reservation:
            raise Rejected("Zone cannot close")
        zone = replace(zone, phase="CLOSED" if zone.extents else "EMPTY")
    elif kind == "finish":
        if zone.phase not in ("OPEN", "CLOSED") or zone.reservation or zone.external_hold or not zone.extents:
            raise Rejected("Zone cannot finish")
        zone = replace(zone, phase="FINISHED")
    elif kind == "reserve":
        spec = next((s for s in state.stripes if s.name == action.stripe), None)
        if (spec is None or type(action.row) is not int or action.row not in range(spec.code.total_rows)
                or zone.domain not in spec.eligible or zone.phase != "OPEN"
                or zone.reservation or zone.appendable() < 1
                or any(e.stripe == spec.name and e.row == action.row and e.status != "RETIRED" for e in zone.extents)):
            raise Rejected("Invalid/exhausted append reservation")
        zone = replace(zone, reservation=(spec.name, action.row))
    elif kind == "stage":
        if zone.phase != "OPEN" or zone.reservation != (action.stripe, action.row):
            raise Rejected("Stage has no matching held append")
        spec = next(s for s in state.stripes if s.name == action.stripe)
        rows = {e.row for z in state.zones if z.domain not in state.offline for e in z.extents
                if e.stripe == spec.name and e.status == "LIVE"}
        if len(rows) < spec.code.data_rows:
            raise Rejected("No decoding basis for staged row")
        extents = zone.extents + (ZExtent("STAGED", action.stripe, action.row),)
        zone = replace(zone, extents=extents, reservation=None,
                       phase="FULL" if len(extents) == zone.capacity else "OPEN")
    elif kind in ("promote", "retire", "discard"):
        if type(action.offset) is not int or action.offset not in range(len(zone.extents)):
            raise Rejected("Invalid extent offset")
        extents = list(zone.extents)
        extent = extents[action.offset]
        if kind == "promote":
            spec = next((s for s in state.stripes if s.name == extent.stripe), None)
            if extent.status != "STAGED" or spec is None or zone.domain not in spec.eligible:
                raise Rejected("Unadoptable staging")
            extents[action.offset] = replace(extent, status="LIVE")
        else:
            expected = "LIVE" if kind == "retire" else "STAGED"
            if extent.status != expected or extent.pins or extent.grants:
                raise Rejected("Retained/granted extent cannot retire")
            extents[action.offset] = replace(extent, status="RETIRED")
        zone = replace(zone, extents=tuple(extents))
    elif kind == "reset_request":
        if (not zone.extents or zone.reservation or zone.external_hold
                or any(e.status != "RETIRED" or e.pins or e.grants for e in zone.extents)):
            raise Rejected("Reset dependencies remain")
        zone = replace(zone, phase="RESETTING", reset_prior=zone.phase)
    elif kind == "reset_ack":
        if zone.phase != "RESETTING":
            raise Rejected("No matching pending reset")
        zone = replace(zone, phase="EMPTY", extents=(), incarnation=zone.incarnation + 1, reset_prior="")
    else:
        raise Rejected("Unknown zoned transition")
    zones[index] = zone
    after = replace(state, zones=tuple(zones))
    validate(after)
    if not protected(after):
        raise Rejected("Transition violates immediate decoding/fault floor")
    return after


def successors(state):
    for zone in state.zones:
        actions = [ZAction(kind, zone.name, zone.incarnation) for kind in
                   ("open", "close", "finish", "reset_request", "reset_ack")]
        if zone.reservation:
            actions.append(ZAction("stage", zone.name, zone.incarnation,
                                   stripe=zone.reservation[0], row=zone.reservation[1]))
        for offset in range(len(zone.extents)):
            actions.extend(ZAction(kind, zone.name, zone.incarnation, offset) for kind in ("promote", "retire", "discard"))
        for spec in state.stripes:
            actions.extend(ZAction("reserve", zone.name, zone.incarnation, stripe=spec.name, row=row)
                           for row in range(spec.code.total_rows))
        for action in actions:
            try:
                after = step(state, action)
            except Rejected:
                continue
            yield action, after


def replay(initial, witness):
    validate(initial)
    if witness.initial != initial.fingerprint() or not protected(initial):
        raise Rejected("Witness has stale/unsafe initial state")
    current = initial
    for action in witness.actions:
        current = step(current, action)
    if not goal(current):
        raise Rejected("Witness does not restore target/headroom")
    return current
