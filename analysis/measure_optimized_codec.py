"""E19 configuration of the verified E18 collector; all arms share the new codec.

The configuration is fixed here and in codec_optimization_protocol.md before
collection. This is a fresh campaign, not a continuation of old-source E18.
"""

from pathlib import Path

from prism_c import zoned_measure as measure
from prism_c.coding import digest


def main():
    measure.PROTOCOL = Path(__file__).resolve().parents[1] / "experiments/codec_optimization_protocol.md"
    measure.GROUPS = (4, 6, 8, 12, 16)
    original_metadata = measure.metadata

    def configured_metadata():
        result = original_metadata()
        result.update(experiment="E19 shared conventional codec", calibration_group_ladder=measure.GROUPS,
                      collector_driver_sha256=digest(Path(__file__).read_bytes()))
        return result

    measure.metadata = configured_metadata
    return measure.main()


if __name__ == "__main__":
    raise SystemExit(main())
