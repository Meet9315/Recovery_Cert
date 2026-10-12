"""Independent replay of witnesses, without importing planner transitions."""

from dataclasses import replace

from .model import Action, Rejected, State, Witness, profile_spec


def replay(state: State, actions: tuple[Action, ...], require_target: bool = True) -> State:
    records = {s.key: {"domain": s.domain, "status": s.status, "stripe": s.stripe,
                      "row": s.row, "incarnation": s.incarnation} for s in state.slots}
    if len(records) != len(state.slots):
        raise Rejected("Duplicate slot")
    policies = {s.name: set(s.eligible) for s in state.stripes}
    codes = {s.name: profile_spec(s.profile) for s in state.stripes}
    if len(policies) != len(state.stripes):
        raise Rejected("Duplicate stripe")

    def safety():
        for item in records.values():
            if item["status"] not in {"FREE", "RESERVED", "STAGED", "LIVE", "RETIRED"}:
                raise Rejected("Unknown allocation status")
            if item["status"] == "FREE" and (item["stripe"] or item["row"] != -1):
                raise Rejected("Free capacity contains an allocation identity")
            if item["status"] in {"RESERVED", "STAGED", "LIVE"}:
                if (item["stripe"] not in policies or type(item["row"]) is not int
                        or item["row"] not in range(codes[item["stripe"]].total_rows)):
                    raise Rejected("Unknown allocated row")
                if item["domain"] not in policies[item["stripe"]]:
                    raise Rejected("Policy violation")
        for name in policies:
            live = [r for r in records.values() if r["stripe"] == name and r["status"] == "LIVE"
                    and r["domain"] not in state.offline]
            if len({r["row"] for r in live}) < codes[name].data_rows:
                raise Rejected("Decoding floor violated")
            if len({r["domain"] for r in live}) != len(live):
                raise Rejected("Failure-domain placement violated")

    safety()
    for action in actions:
        if action.slot not in records:
            raise Rejected("Unknown slot")
        record = records[action.slot]
        if record["domain"] in state.offline or record["incarnation"] != action.incarnation:
            raise Rejected("Offline or stale allocation")
        if action.kind == "reserve":
            if (record["status"] != "FREE" or action.stripe not in policies or type(action.row) is not int
                    or action.row not in range(codes[action.stripe].total_rows)):
                raise Rejected("Invalid capacity acquisition")
            if record["domain"] not in policies[action.stripe]:
                raise Rejected("Ineligible capacity acquisition")
            for other in records.values():
                if other["stripe"] == action.stripe and other["status"] in {"LIVE", "STAGED", "RESERVED"}:
                    if other["row"] == action.row or other["domain"] == record["domain"]:
                        raise Rejected("Duplicate row or competing reservation")
            record.update(status="RESERVED", stripe=action.stripe, row=action.row,
                          incarnation=action.incarnation + 1)
        else:
            if (record["stripe"], record["row"]) != (action.stripe, action.row):
                raise Rejected("Wrong fragment identity")
            rules = {"stage": ("RESERVED", "STAGED"), "promote": ("STAGED", "LIVE"),
                     "retire": ("LIVE", "RETIRED"), "reclaim": ("RETIRED", "FREE")}
            if action.kind not in rules or record["status"] != rules[action.kind][0]:
                raise Rejected("Invalid predecessor state")
            record["status"] = rules[action.kind][1]
            if action.kind == "reclaim":
                record.update(stripe="", row=-1)
        safety()
    if require_target:
        for name in policies:
            rows = {r["row"] for r in records.values() if r["stripe"] == name
                    and r["status"] == "LIVE" and r["domain"] not in state.offline}
            if rows != set(range(codes[name].total_rows)):
                raise Rejected("Incomplete terminal protection")
    return replace(state, slots=tuple(replace(s, **records[s.key]) for s in state.slots))


def check(state: State, witness: Witness) -> State:
    if witness.version != 1 or witness.initial != state.fingerprint():
        raise Rejected("Version/snapshot mismatch")
    final = replay(state, witness.actions)
    if final.fingerprint() != witness.terminal:
        raise Rejected("Incorrect terminal commitment")
    return final
