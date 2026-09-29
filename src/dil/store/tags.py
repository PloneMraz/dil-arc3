"""The tag schema (protocol §9).

Every datum carries a FIXED layer of four tags, in fixed order, never
overwritten:
    (1) timestamp, (2) cycle-mark, (3) provenance, (4) floor-tag.
Every layer T1–T8 stamps a floor-tag; there are no pass-through layers.

On top of the fixed layer, every datum MUST carry at least THREE open tags, one
of which MUST be `domain` (the class of data it is), so the `[event]` log is
auditable by data class and described along several real dimensions. The agent
MAY mint further OPEN tags denoting *what* the datum is (format, platform,
object) — but never its quality, correctness, or value. Open tags never
overwrite the fixed layer.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from dataclasses import dataclass, field
from typing import Final, Literal, TypeAlias

from ..invariants.types import LayerIndex

# Provenance state (protocol §3, §9). NOT a chain but a directed graph: `prior`
# and `nascent` are one-way entries, and `running`, `simulated`, `projected`,
# `scar` form a circulation with no terminal state — a datum is never a
# conclusion at rest but data waiting to be used. The legal moves are the edge
# set in data_store.py.
#
#   - prior      — host data existing before the loop ran, admitted through the
#                  tagging-gate, not yet run
#   - nascent    — a datum the agent has written anew, not yet run; it bears the
#                  cycle-mark of the cycle that wrote it (v0.3.3)
#   - running    — data in use, in motion through the loop
#   - simulated  — taken up into the building of a situation (§6.2)
#   - projected  — an outcome cast from a situation, not yet collided (§6.2)
#   - scar       — collided with resistance and held
Provenance: TypeAlias = Literal["prior", "nascent", "running", "simulated", "projected", "scar"]

# Open tags: descriptive only (protocol §9, "Open-tag discipline").
#
# A key names a descriptive *dimension* of the datum (what it is); the value is
# its setting on that dimension. The rules governing the layer:
#   - every open tag MUST describe a real dimension the datum actually has;
#   - a key MUST denote the same dimension wherever it appears, so the [event]
#     log is filterable by an auditor;
#   - no tag MAY name a verdict (quality, correctness, value);
#   - at least three open tags MUST be present, one being `domain`.
# The minimum is a floor on honest description, not a quota to pad: a tag
# invented merely to reach the count, that does not describe the datum,
# fabricates data to fill a gap, which the loop forbids.
OpenTags: TypeAlias = dict[str, str]


@dataclass(frozen=True, slots=True)
class FixedTags:
    """The fixed four tags.

    `cycle_mark` is None until the datum has run (a `prior` bears no cycle-mark).
    `floor_tag` is the layer the datum just exited.
    """

    # (1) timestamp — when the datum was stamped.
    timestamp: int
    # (2) cycle-mark — the cycle in which it ran; None while still `prior`.
    cycle_mark: int | None
    # (3) provenance — a directed graph (§9): `prior` (one-way entry), then
    # `running`/`simulated`/`projected`/`scar` circulating.
    provenance: Provenance
    # (4) floor-tag — a single slot naming the layer the datum just exited. Each
    # layer overwrites it as the datum passes, so it always names the *current*
    # layer ("where is it now"). The full path — every layer exited — is NOT held
    # on the datum: it is the stream of `layer-exit` lines in the `[event]` log
    # (§9), read from there and never from a tag.
    floor_tag: LayerIndex


@dataclass(frozen=True, slots=True)
class TaggedDatum:
    """A tagged datum: payload + the fixed four + open tags.

    The path a datum has travelled is NOT carried here (§9): a tag names the
    present only (floor-tag = "where is it now"); the full path — every layer it
    exited, every provenance move — is recorded line-by-line in the `[event]` log
    as it occurs, and read from there, never from a tag. A tag is updated; the
    log is appended to.
    """

    payload: object
    fixed: FixedTags
    open: OpenTags = field(default_factory=dict)


# Open-tag keys that name a verdict are forbidden (protocol §9).
_FORBIDDEN_OPEN_TAG_KEYS: Final[frozenset[str]] = frozenset(
    {"quality", "correctness", "value", "valence", "good", "bad"}
)

# Open-tag keys that MUST be present on every datum (protocol §9, open layer).
# `domain` is mandatory so the `[event]` log is auditable by data class.
REQUIRED_OPEN_TAG_KEYS: Final = ("domain",)

# Minimum number of open tags every datum MUST carry (protocol §9, open layer),
# one of which is `domain`. A floor on honest description, not a quota to pad.
MIN_OPEN_TAGS: Final = 3


def invalid_open_tag_reason(open_tags: OpenTags) -> str | None:
    """Validate the open-tag layer against the schema rules.

    It must carry every required key (domain), at least MIN_OPEN_TAGS tags in
    total, and no forbidden verdict key. Returns the reason a set is invalid, or
    None if it is acceptable. The tagging-gate enforces this; it is kept here
    beside the schema it defends.

    Note: this checks presence, count, and the verdict prohibition — the
    structural rules. That each tag *honestly describes* the datum (the floor's
    intent) is a semantic property the gate cannot verify mechanically; it is the
    minter's responsibility and an auditor's read.
    """
    for required in REQUIRED_OPEN_TAG_KEYS:
        value = open_tags.get(required)
        if value is None or value == "":
            return f'open tag "{required}" is required for auditability but is missing'

    count = len(open_tags)
    if count < MIN_OPEN_TAGS:
        return (
            f"at least {MIN_OPEN_TAGS} open tags are required (one being domain), "
            f"got {count}"
        )

    for key in open_tags:
        if key.lower() in _FORBIDDEN_OPEN_TAG_KEYS:
            return (
                f'open tag "{key}" names a verdict (quality/correctness/value), '
                f"which the schema forbids"
            )

    return None
