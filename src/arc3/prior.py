"""What the character may know before it has lived a single cycle.

A creature put in a box arrives with a very long history: what its genes carry
and what others taught it. This character arrives with none. So what it is given
beforehand is the least that lets it know what it is doing here: the directive,
and the rules of the place it is in. Everything else is left for it to think
through and interpret.

**Where it comes from.** Only public documents published by the competition,
quoted verbatim, each with its source. Nothing here is about a particular game,
and nothing was learned by playing one. The competition rules allow this: data
beyond the competition data may be used if it is "publicly available and equally
accessible to use by all Participants" (Kaggle rules §6.a); what they forbid is
"information from hand labeling or human prediction of the validation dataset or
test data records" (§2.b of the entry rules), and none of this is either.

**How it enters.** Through the door the protocol already has for exactly this:
the host declares it as pre-existing memory, and the runtime admits each item
through the tagging-gate, stamped `prior` with no cycle-mark (§9, "no side
door"). An item that cannot be tagged honestly is refused, not smuggled in.

**How it is recalled.** Not poured in. It waits in the store until something
arrives that it is about: each item's open tag `object` says what that is, on
the same dimension the status channel describes its reports with, and T3 asks
the store with that description (§6.4 query). The directive is about the
region's status, so the first status report brings it to mind. The other items
are about things no arrival describes yet, and wait.

The directive is the one sentence the competition gives every model on its
official leaderboard. The character is told no more than that.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from dil.host import PreexistingItem

from .observe import STATUS_OBJECT

# Every item carries these open tags: the gate requires `domain` and at least
# three in all, and forbids any key that names a verdict.
DOMAIN: Final = "arc3-rules"

REPORT: Final = "https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf"
SCHEMA: Final = "https://docs.arcprize.org/game-schema.md"
ACTIONS: Final = "https://docs.arcprize.org/actions.md"
SCORING: Final = "https://docs.arcprize.org/methodology.md"
COMPETITION: Final = "https://docs.arcprize.org/toolkit/competition_mode.md"


# Every quote names the document it is taken from, because one item can draw on
# several; the open tag names only where all of them come from.
SOURCE_TAG: Final = "arcprize-public-docs"


def _q(text: str, source: str) -> dict[str, str]:
    """One sentence, verbatim, and where it was read."""
    return {"text": text, "source": source}


def _item(key: str, kind: str, about: str, payload: dict) -> PreexistingItem:
    return PreexistingItem(
        id=f"prior:{key}",
        payload=payload,
        open={"domain": DOMAIN, "kind": kind, "source": SOURCE_TAG, "object": about},
    )


DIRECTIVE: Final = _item(
    "directive",
    "directive",
    STATUS_OBJECT,
    {
        # The official leaderboard's system prompt, given to every model alike.
        "says": [_q("You are playing a game. Your goal is to win.", REPORT)],
        # What winning and ending without a win are, in the game schema's own
        # words, and the signal a frame carries for each. The mind reads these
        # from here; it does not carry them in its code.
        "objective": {
            "state": "WIN",
            "means": _q("The objective was completed successfully", SCHEMA),
        },
        "ended_without": {
            "state": "GAME_OVER",
            "means": _q("The run ended without a win", SCHEMA),
        },
        "toward": {
            "count": "levels_completed",
            "of": "win_levels",
            "means": _q(
                "Each environment in ARC-AGI-3 is structured as a series of "
                "levels. A level ends when a win condition (terminal frame) is "
                "reached.",
                REPORT,
            ),
        },
    },
)

LEVELS: Final = _item(
    "levels",
    "structure",
    "level-structure",
    {
        "says": [
            _q("Environments are developed with a level-based structure, with at "
               "least six levels per environment.", REPORT),
            _q("The first level in an environment functions as a tutorial level "
               "and is intentionally easy (to both humans and AI).", REPORT),
            _q("Later levels are therefore expected to require the accumulation "
               "and integration of concepts learned earlier in the environment.",
               REPORT),
            _q("Each environment contains multiple mechanics.", REPORT),
        ],
    },
)

COST: Final = _item(
    "cost",
    "cost",
    "action-cost",
    {
        "says": [
            _q("Each turn where the agent submits a command, move, or input that "
               "affects the game state counts as an action.", SCORING),
            _q("Internal operations that do not alter the environment (tool "
               "calls, reasoning steps, retries) are not counted as actions.",
               SCORING),
            _q("level_score = (human_baseline_actions / ai_actions) ^ 2", SCORING),
            _q("To unlock a maximum game score of 100%, the AI must complete all "
               "levels, including the final one.", SCORING),
        ],
    },
)

BODY: Final = _item(
    "body",
    "body",
    "body",
    {
        "says": [
            _q("The agent views a 64x64 grid where each cell is one of 16 "
               "possible colors.", REPORT),
            _q("Frame sequences allow for non-interactive animations (e.g., an "
               "object moving across the screen) between player turns.", REPORT),
            _q("The environment’s state does not change asynchronously from "
               "the agent’s actions.", REPORT),
            _q("Each game exposes only the subset currently available through the "
               "response's `available_actions` field.", ACTIONS),
            _q("When a game reaches a game-over state, the only valid action is "
               "`RESET`.", ACTIONS),
            _q("Only Level Resets are permitted, Game Resets are not allowed and "
               "become Level Resets", COMPETITION),
        ],
        "actions": {
            "RESET": _q("Initializes or restarts the game or level state", ACTIONS),
            "ACTION1": _q("Simple action - varies by game (semantically mapped to "
                          "up)", ACTIONS),
            "ACTION2": _q("Simple action - varies by game (semantically mapped to "
                          "down)", ACTIONS),
            "ACTION3": _q("Simple action - varies by game (semantically mapped to "
                          "left)", ACTIONS),
            "ACTION4": _q("Simple action - varies by game (semantically mapped to "
                          "right)", ACTIONS),
            "ACTION5": _q("Simple action - varies by game (e.g., interact, select, "
                          "rotate, attach/detach, execute, etc.)", ACTIONS),
            "ACTION6": _q("Complex action requiring x,y coordinates (0-63 range)",
                          ACTIONS),
            "ACTION7": _q("Simple undo action", ACTIONS),
        },
    },
)

WORLD: Final = _item(
    "world",
    "world",
    "things",
    {
        "says": [
            _q("Objectness: Elements are perceived as coherent, persistent "
               "entities that can move, collide, or be occluded.", REPORT),
            _q("Basic geometry and topology: Understanding of symmetries, "
               "rotations, and elementary topology (e.g., “inside” vs. "
               "“outside”, connectedness, holes).", REPORT),
            _q("Basic physics: Intuitive rules like gravity, momentum, and "
               "bouncing.", REPORT),
            _q("Agentness: Recognizing that certain objects act with intent and "
               "pursue goals.", REPORT),
            _q("No language or cultural symbols: Environments never use numbers, "
               "letters, recognizable real-world clip-art (like flowers or keys), "
               "or cultural conventions (like green meaning “go”).", REPORT),
        ],
    },
)

RULES: Final[tuple[PreexistingItem, ...]] = (DIRECTIVE, LEVELS, COST, BODY, WORLD)


class ArcRules:
    """The host's pre-existing memory: the rules, offered for admission.

    Offered, not loaded. The runtime scans this once at startup and each item has
    to pass the tagging-gate before it is in the store at all.
    """

    __slots__ = ("_items",)

    def __init__(self, items: tuple[PreexistingItem, ...] = RULES) -> None:
        self._items = items

    def scan(self) -> Iterable[PreexistingItem]:
        return iter(self._items)


__all__ = ["DIRECTIVE", "DOMAIN", "RULES", "ArcRules"]
