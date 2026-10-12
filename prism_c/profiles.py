"""Versioned immutable coding contracts; arbitrary matrices are excluded."""

from dataclasses import dataclass
from types import MappingProxyType

DEFAULT_PROFILE = "xor-2+1-v1"
FOUR_PLUS_TWO = "pq-4+2-gf256-v1"


@dataclass(frozen=True)
class CodeProfile:
    name: str
    data_rows: int
    generator: tuple[tuple[int, ...], ...]

    @property
    def total_rows(self):
        return len(self.generator)


PROFILES = MappingProxyType({
    DEFAULT_PROFILE: CodeProfile(DEFAULT_PROFILE, 2, ((1, 0), (0, 1), (1, 1))),
    FOUR_PLUS_TWO: CodeProfile(FOUR_PLUS_TWO, 4,
        ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1),
         (1, 1, 1, 1), (1, 2, 4, 8))),
})
