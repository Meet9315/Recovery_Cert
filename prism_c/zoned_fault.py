"""Actual process-exit helper for the opt-in file emulator's tests."""

import argparse
import os

from .zoned_store import ZonedFileStore


EXIT_CODE = 86


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("fence", type=int)
    parser.add_argument("kind")
    parser.add_argument("boundary")
    args = parser.parse_args()

    def fault(kind, boundary):
        if (kind, boundary) == (args.kind, args.boundary):
            os._exit(EXIT_CODE)

    ZonedFileStore(args.root).execute(args.fence, fault)
    raise AssertionError("Requested exit boundary was never reached")


if __name__ == "__main__":
    main()
