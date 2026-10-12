"""Immutable finite storage model and bounded continuation planner."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json


class Rejected(ValueError):
    """A state transition or witness does not satisfy the supported contract."""


@dataclass(frozen=True)
class Stripe:
    name: str
    eligible: tuple[str, ...]


@dataclass(frozen=True)
class Slot:
    key: str
    domain: str
    status: str = "FREE"
    stripe: str = ""
    row: int = -1
    incarnation: int = 0


@dataclass(frozen=True)
class State:
    stripes: tuple[Stripe, ...]
    slots: tuple[Slot, ...]
    offline: tuple[str, ...] = ()

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

    def target(self) -> bool:
        return all(
            {s.row for s in self.slots if s.status == "LIVE" and s.stripe == spec.name
             and s.domain not in self.offline} == {0, 1, 2}
            for spec in self.stripes
        )

    def ledger(self) -> dict:
        result: dict[str, dict[str, int]] = {}
        for slot in self.slots:
            counts = result.setdefault(slot.domain, {k: 0 for k in
                ("FREE", "RESERVED", "STAGED", "LIVE", "RETIRED")})
            counts[slot.status] += 1
        return result


@dataclass(frozen=True)
class Action:
    kind: str
    slot: str
    stripe: str = ""
    row: int = -1
    incarnation: int = 0


@dataclass(frozen=True)
class Witness:
    initial: str
    actions: tuple[Action, ...]
    terminal: str
    version: int = 1

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> dict:
        return {**asdict(self), "digest": self.digest()}

    @classmethod
    def from_dict(cls, value: dict) -> Witness:
        witness = cls(value["initial"], tuple(Action(**a) for a in value["actions"]),
                      value["terminal"], value["version"])
        if witness.digest() != value["digest"]:
            raise Rejected("Witness digest mismatch")
        return witness


class SearchStatus(str, Enum):
    FOUND = "FOUND"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SearchResult:
    status: SearchStatus
    witness: Witness | None
    explored: int
    reason: str


def validate_state(state: State) -> None:
    names = {spec.name for spec in state.stripes}
    if len(names) != len(state.stripes) or len({s.key for s in state.slots}) != len(state.slots):
        raise Rejected("Duplicate stripe or slot identity")
    for slot in state.slots:
        if slot.status not in {"FREE", "RESERVED", "STAGED", "LIVE", "RETIRED"}:
            raise Rejected("Unknown slot state")
        if slot.incarnation < 0:
            raise Rejected("Invalid incarnation")
        if slot.status == "FREE" and (slot.stripe or slot.row != -1):
            raise Rejected("Free slot retains an allocation")
        if slot.status in {"RESERVED", "STAGED", "LIVE"}:
            if slot.stripe not in names or slot.row not in {0, 1, 2}:
                raise Rejected("Allocation has invalid stripe/row")
            spec = next(s for s in state.stripes if s.name == slot.stripe)
            if slot.domain not in spec.eligible:
                raise Rejected("Ineligible placement")
    for spec in state.stripes:
        live = [s for s in state.slots if s.stripe == spec.name and s.status == "LIVE"
                and s.domain not in state.offline]
        if len({s.row for s in live}) < 2:
            raise Rejected(f"Stripe {spec.name} is below its safety floor")
        if len({s.domain for s in live}) != len(live):
            raise Rejected("Live fragments co-located in a failure domain")


def transition(state: State, action: Action) -> State:
    """Planner transition function; checker.py supplies a separate replay."""
    validate_state(state)
    slot = next((s for s in state.slots if s.key == action.slot), None)
    if slot is None or slot.domain in state.offline:
        raise Rejected("Missing or offline slot")
    if slot.incarnation != action.incarnation:
        raise Rejected("Stale slot incarnation")
    if action.kind == "reserve":
        spec = next((s for s in state.stripes if s.name == action.stripe), None)
        if slot.status != "FREE" or spec is None or action.row not in {0, 1, 2}:
            raise Rejected("Invalid reservation")
        if slot.domain not in spec.eligible:
            raise Rejected("Ineligible destination")
        if any(s.stripe == spec.name and s.status in {"RESERVED", "STAGED", "LIVE"}
               and (s.row == action.row or s.domain == slot.domain) for s in state.slots):
            raise Rejected("Conflicting row or destination reservation")
        updated = replace(slot, status="RESERVED", stripe=spec.name, row=action.row,
                          incarnation=slot.incarnation + 1)
    else:
        if (slot.stripe, slot.row) != (action.stripe, action.row):
            raise Rejected("Allocation identity mismatch")
        if action.kind == "stage" and slot.status == "RESERVED":
            updated = replace(slot, status="STAGED")
        elif action.kind == "promote" and slot.status == "STAGED":
            updated = replace(slot, status="LIVE")
        elif action.kind == "retire" and slot.status == "LIVE":
            updated = replace(slot, status="RETIRED")
        elif action.kind == "reclaim" and slot.status == "RETIRED":
            updated = replace(slot, status="FREE", stripe="", row=-1)
        else:
            raise Rejected("Illegal slot transition")
    result = replace(state, slots=tuple(updated if s.key == slot.key else s for s in state.slots))
    validate_state(result)
    return result


def successors(state: State) -> list[tuple[Action, State]]:
    """Finite repair-only grammar: no migration or new live-fragment retirement.

    Incarnations may increase only once per initially free/retired slot because
    newly promoted data is not retired by this search. INFEASIBLE is relative to
    this complete finite grammar, not all possible storage operations.
    """
    candidates = []
    for slot in state.slots:
        if slot.status == "FREE":
            candidates.extend(Action("reserve", slot.key, spec.name, row, slot.incarnation)
                              for spec in state.stripes for row in range(3))
        else:
            kind = {"RESERVED": "stage", "STAGED": "promote", "RETIRED": "reclaim"}.get(slot.status)
            if kind:
                candidates.append(Action(kind, slot.key, slot.stripe, slot.row, slot.incarnation))
    result = []
    for action in candidates:
        try:
            result.append((action, transition(state, action)))
        except Rejected:
            continue
    return result


def plan(state: State, max_states: int = 20_000, max_steps: int = 30) -> SearchResult:
    validate_state(state)
    if max_states < 1 or max_steps < 0:
        return SearchResult(SearchStatus.UNKNOWN, None, 0, "Invalid/exhausted budget")
    queue = deque([(state, ())])
    seen = {state}
    explored = 0
    cutoff = False
    while queue:
        current, path = queue.popleft()
        if explored >= max_states:
            return SearchResult(SearchStatus.UNKNOWN, None, explored, "State budget exhausted")
        explored += 1
        if current.target():
            return SearchResult(SearchStatus.FOUND, Witness(state.fingerprint(), path,
                current.fingerprint()), explored, "Checked candidate available")
        outgoing = successors(current)
        if len(path) >= max_steps:
            cutoff |= any(nxt not in seen for _, nxt in outgoing)
            continue
        for action, nxt in outgoing:
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + (action,)))
    status = SearchStatus.UNKNOWN if cutoff else SearchStatus.INFEASIBLE
    return SearchResult(status, None, explored,
        "Depth budget exhausted" if cutoff else "Finite repair-only grammar exhausted")


def fixture(reclamation: bool = False, infeasible: bool = False) -> State:
    stripes = (Stripe("A", ("S", "T", "X", "Y")), Stripe("B", ("S", "T", "X")))
    slots = tuple(Slot(f"{name}{row}", domain, "LIVE", name, row, 1)
                  for name in ("A", "B") for row, domain in enumerate(("S", "T")))
    x = Slot("X0", "X", "RETIRED" if reclamation else "FREE", incarnation=1 if reclamation else 0)
    y = Slot("Y0", "Y", "RETIRED" if infeasible else "FREE")
    # Infeasible fixture: X is permanently offline; B cannot use Y.
    return State(stripes, slots + (x, y), ("X",) if infeasible else ())
