"""Complete-coverage component cache for trusted continuation validation."""

from dataclasses import asdict, dataclass
import json

from .checker import replay
from .model import Action, Rejected, Slot, State, Stripe, Witness
from .profiles import DEFAULT_PROFILE


VERSION = 1


def state_from_dict(value: dict) -> State:
    return State(tuple(Stripe(s["name"], tuple(s["eligible"]), s.get("profile", DEFAULT_PROFILE)) for s in value["stripes"]),
                 tuple(Slot(**s) for s in value["slots"]), tuple(value["offline"]))


def partition(state: State, actions: tuple[Action, ...]) -> list[tuple[State, tuple[Action, ...]]]:
    """Derive complete membership, merging stripe dependencies sharing a slot."""
    parent = {s.name: s.name for s in state.stripes}

    def find(name):
        if name not in parent:
            raise Rejected("Unknown stripe in dependency coverage")
        while parent[name] != name:
            name = parent[name]
        return name

    owners = {slot.key: ({slot.stripe} if slot.stripe in parent else set()) for slot in state.slots}
    for action in actions:
        if action.slot not in owners:
            raise Rejected("Unknown slot in dependency coverage")
        if action.stripe:
            find(action.stripe)
            owners[action.slot].add(action.stripe)
    for names in owners.values():
        if names:
            root = find(sorted(names)[0])
            for name in sorted(names)[1:]:
                parent[find(name)] = root
    groups: dict[str, tuple[list, list, list]] = {}
    for spec in state.stripes:
        groups.setdefault("stripe:" + find(spec.name), ([], [], []))[0].append(spec)
    slot_group = {}
    for slot in state.slots:
        names = owners[slot.key]
        group = "stripe:" + find(next(iter(names))) if names else "slot:" + slot.key
        groups.setdefault(group, ([], [], []))[1].append(slot)
        slot_group[slot.key] = group
    for action in actions:
        groups[slot_group[action.slot]][2].append(action)
    result = []
    for group in sorted(groups):
        specs, slots, subset = groups[group]
        domains = {slot.domain for slot in slots}
        projection = State(tuple(specs), tuple(slots), tuple(d for d in state.offline if d in domains))
        result.append((projection, tuple(subset)))
    return result


@dataclass
class Component:
    expected: State
    actions: tuple[Action, ...]
    terminal: State


class ContinuationCache:
    """Only internal checked metadata may instantiate a reusable certificate."""

    def __init__(self, witness: Witness, cursor: int, components: list[Component]):
        self.witness_digest = witness.digest()
        self.cursor = cursor
        self.components = components
        self.last_stats = {"reused_components": 0, "replayed_components": 0, "replayed_actions": 0,
                           "coverage_rebuilds": 0}

    @classmethod
    def build(cls, state: State, witness: Witness, cursor: int = 0):
        if witness.version != 1 or not 0 <= cursor <= len(witness.actions):
            raise Rejected("Unsupported witness/cursor")
        if cursor == 0 and state.fingerprint() != witness.initial:
            raise Rejected("Initial snapshot conflict")
        final = replay(state, witness.actions[cursor:])
        if final.fingerprint() != witness.terminal:
            raise Rejected("Full suffix does not reach committed terminal state")
        components = [Component(start, subset, replay(start, subset))
                      for start, subset in partition(state, witness.actions[cursor:])]
        cache = cls(witness, cursor, components)
        cache.last_stats = {"reused_components": 0, "replayed_components": len(components),
                            "replayed_actions": 2 * len(witness.actions[cursor:]), "coverage_rebuilds": 1}
        return cache

    def to_json(self, incarnation: str) -> str:
        return json.dumps({"version": VERSION, "incarnation": incarnation,
                           "witness_digest": self.witness_digest, "cursor": self.cursor,
                           "components": [{"expected": asdict(c.expected),
                                           "actions": [asdict(a) for a in c.actions],
                                           "terminal": asdict(c.terminal)} for c in self.components]}, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str, witness: Witness, cursor: int, incarnation: str):
        value = json.loads(raw)
        if (value["version"] != VERSION or value["incarnation"] != incarnation or
                value["witness_digest"] != witness.digest() or value["cursor"] != cursor):
            raise Rejected("Cache binding mismatch")
        components = [Component(state_from_dict(c["expected"]), tuple(Action(**a) for a in c["actions"]),
                                state_from_dict(c["terminal"])) for c in value["components"]]
        return cls(witness, cursor, components)

    def validate(self, state: State, witness: Witness, cursor: int) -> State:
        if self.witness_digest != witness.digest() or self.cursor != cursor:
            raise Rejected("Wrong cached continuation")
        if cursor == 0 and state.fingerprint() != witness.initial:
            raise Rejected("Initial snapshot conflict")
        projected = partition(state, witness.actions[cursor:])
        def identity(start):
            return (tuple(s.name for s in start.stripes), tuple(s.key for s in start.slots))
        old = {identity(c.expected): c for c in self.components}
        stats = {"reused_components": 0, "replayed_components": 0, "replayed_actions": 0,
                 "coverage_rebuilds": 0}
        self.last_stats = stats
        updated = []
        if set(old) != {identity(p) for p, _ in projected}:
            rebuilt = self.build(state, witness, cursor)
            self.components = rebuilt.components
            self.last_stats = rebuilt.last_stats
            return replay_merge(state, self.components, witness.terminal)
        for start, actions in projected:
            previous = old[identity(start)]
            if previous.expected == start and previous.actions == actions:
                updated.append(previous)
                stats["reused_components"] += 1
            else:
                stats["replayed_components"] += 1
                stats["replayed_actions"] += len(actions)
                updated.append(Component(start, actions, replay(start, actions)))
        final = replay_merge(state, updated, witness.terminal)
        self.components, self.last_stats = updated, stats
        return final

    def advance(self, before: State, after: State, action: Action) -> None:
        """Consume exactly the checked step; called only after current-step replay."""
        for component in self.components:
            if any(s.key == action.slot for s in component.expected.slots):
                if not component.actions or component.actions[0] != action:
                    raise Rejected("Cache advancement is out of order")
                changed = {s.key: s for s in after.slots}
                component.expected = State(component.expected.stripes,
                    tuple(changed[s.key] for s in component.expected.slots), component.expected.offline)
                component.actions = component.actions[1:]
                self.cursor += 1
                return
        raise Rejected("Current action is outside cached dependency coverage")


def replay_merge(state: State, components: list[Component], terminal: str) -> State:
    slots = {s.key: s for c in components for s in c.terminal.slots}
    specs = {s.name: s for c in components for s in c.terminal.stripes}
    if len(slots) != len(state.slots) or len(specs) != len(state.stripes):
        raise Rejected("Incomplete terminal coverage")
    final = State(tuple(specs[s.name] for s in state.stripes), tuple(slots[s.key] for s in state.slots), state.offline)
    if final.fingerprint() != terminal:
        raise Rejected("Cached terminal commitment mismatch")
    return final


class WholeSuffixCache:
    """Conventional exact-state guarded evidence; a strong deployed comparator."""

    def __init__(self, witness: Witness, cursor: int, expected: State, terminal: State):
        self.witness_digest = witness.digest()
        self.cursor = cursor
        self.expected = expected
        self.terminal = terminal
        self.last_stats = {"guard_reused": False, "replayed_actions": 0}

    @classmethod
    def build(cls, state: State, witness: Witness, cursor: int = 0):
        if witness.version != 1 or not 0 <= cursor <= len(witness.actions):
            raise Rejected("Unsupported witness/cursor")
        if cursor == 0 and state.fingerprint() != witness.initial:
            raise Rejected("Initial snapshot conflict")
        final = replay(state, witness.actions[cursor:])
        if final.fingerprint() != witness.terminal:
            raise Rejected("Guarded suffix does not reach committed terminal")
        cache = cls(witness, cursor, state, final)
        cache.last_stats["replayed_actions"] = len(witness.actions) - cursor
        return cache

    @classmethod
    def from_json(cls, raw: str, witness: Witness, cursor: int, incarnation: str):
        value = json.loads(raw)
        if (value["version"] != VERSION or value["kind"] != "whole" or
                value["incarnation"] != incarnation or value["cursor"] != cursor or
                value["witness_digest"] != witness.digest()):
            raise Rejected("Guarded cache binding mismatch")
        return cls(witness, cursor, state_from_dict(value["expected"]), state_from_dict(value["terminal"]))

    def to_json(self, incarnation: str) -> str:
        return json.dumps({"version": VERSION, "kind": "whole", "incarnation": incarnation,
                           "witness_digest": self.witness_digest, "cursor": self.cursor,
                           "expected": asdict(self.expected), "terminal": asdict(self.terminal)}, sort_keys=True)

    def validate(self, state: State, witness: Witness, cursor: int) -> State:
        if self.witness_digest != witness.digest() or self.cursor != cursor:
            raise Rejected("Wrong guarded continuation")
        if state == self.expected:
            self.last_stats = {"guard_reused": True, "replayed_actions": 0}
            return self.terminal
        rebuilt = self.build(state, witness, cursor)
        self.expected, self.terminal, self.last_stats = rebuilt.expected, rebuilt.terminal, rebuilt.last_stats
        return self.terminal

    def advance(self, before: State, after: State, action: Action) -> None:
        if before != self.expected:
            raise Rejected("Guarded cursor advanced from unexpected state")
        self.expected = after
        self.cursor += 1
