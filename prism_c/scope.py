"""Authority-derived whole-stripe scope with complete membership coverage."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Rejected, State


@dataclass(frozen=True)
class PlanScope:
    stripes: tuple[str, ...]
    slots: tuple[str, ...]

    @classmethod
    def derive(cls, state: State, stripes, destinations):
        names = tuple(sorted(stripes))
        targets = tuple(sorted(destinations))
        if not names or len(set(names)) != len(names) or len(set(targets)) != len(targets):
            raise Rejected("Scope needs distinct stripes and destination identities")
        if not set(names) <= {s.name for s in state.stripes}:
            raise Rejected("Scope names an unknown stripe")
        if not set(targets) <= {s.key for s in state.slots}:
            raise Rejected("Scope names an unknown slot")
        keys = set(targets) | {s.key for s in state.slots if s.stripe in names}
        scope = cls(names, tuple(sorted(keys)))
        scope.project(state)
        return scope

    def project(self, state: State) -> State:
        specs = tuple(s for s in state.stripes if s.name in self.stripes)
        if {s.name for s in specs} != set(self.stripes) or len(specs) != len(self.stripes):
            raise Rejected("Scoped stripe metadata disappeared")
        members = {s.key for s in state.slots if s.stripe in self.stripes}
        if not members <= set(self.slots):
            raise Rejected("New allocation entered scoped stripe membership")
        slots = tuple(s for s in state.slots if s.key in self.slots)
        if {s.key for s in slots} != set(self.slots) or len(slots) != len(self.slots):
            raise Rejected("Claimed scope slot disappeared or duplicated")
        if any(s.stripe and s.stripe not in self.stripes for s in slots):
            raise Rejected("Scoped destination is assigned to an unscoped stripe")
        domains = {s.domain for s in slots}
        return State(specs, slots, tuple(d for d in state.offline if d in domains))

    def compatible(self, other: PlanScope) -> bool:
        return not (set(self.stripes) & set(other.stripes) or set(self.slots) & set(other.slots))
