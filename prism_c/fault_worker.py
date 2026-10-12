"""Subprocess used to interrupt storage commands without Python unwinding."""

import argparse
import os

from .storage import Authority


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("plan")
    parser.add_argument("fence", type=int)
    parser.add_argument("step", type=int)
    parser.add_argument("point")
    parser.add_argument("--validation-mode", default="conventional_cached",
                        choices=("conventional_cached", "selective", "full", "shadow"))
    args = parser.parse_args()

    def interrupt(point):
        if point == args.point:
            os._exit(77)

    Authority(args.root, validation_mode=args.validation_mode).step(args.plan, args.fence, args.step, fault=interrupt)
    raise SystemExit("Requested fault point was not reached")


if __name__ == "__main__":
    main()
