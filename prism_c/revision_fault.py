"""Actual process-exit probe for revision validation/revoke/commit boundaries."""

import json
import os
import sys

from .model import Witness
from .storage import Authority


if __name__ == "__main__":
    request = json.load(sys.stdin)
    def interrupt(point):
        if point == request["point"]:
            os._exit(77)
    Authority(request["root"], request["mode"]).revise(
        request["parent"], Witness.from_dict(request["witness"]), request["destinations"],
        request["fence"], request["request_id"], request["expected_digest"], fault=interrupt)
    raise SystemExit("Requested revision fault was not reached")
