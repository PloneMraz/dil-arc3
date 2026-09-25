"""The world — what lies outside the agent: the region it acts on, and the Others who see it act.

Neither the agent nor its host. The host's body touches the region (`reset`,
`step`) and, when it does not act, lets a moment pass (`idle`); the Others in
the world see each act, or the lack of one, as anyone standing by would. What an
Other says reaches the agent only as the host hears it (`remarks`), on the
host's own channel for it. The host holds the world as its environment; it does
not know what an Other is.

The Others watch from the agent's first moment: the first time the host asks
what they say. What the host does to open the region before then is not seen.
"""

from __future__ import annotations

from typing import Any

from .onlooker import ALTERNATION, REPEAT_AT, Onlooker


def act_of(action: Any, data: Any) -> dict[str, Any]:
    """An act as the world shows it: its name, and what it carried."""
    name = getattr(action, "name", None)
    if name is None:
        name = getattr(action, "value", None)
    return {"act": name if name is not None else str(action), **(dict(data) if data else {})}


class World:
    """The region, and the Others standing by."""

    __slots__ = ("_region", "_others", "_moment", "_watching")

    def __init__(self, region: Any, others: dict[str, Any] | None = None) -> None:
        self._region = region
        self._others = dict(others or {})
        self._moment = 0
        self._watching = False

    @property
    def region(self) -> Any:
        return self._region

    def reset(self) -> Any:
        return self._region.reset()

    def step(self, action: Any, data: Any = None) -> Any:
        """The agent acts on the region; the Others see it act."""
        out = self._region.step(action, data)
        if self._watching:
            for other in self._others.values():
                other.saw(self._moment, act_of(action, data))
            self._moment += 1
        return out

    def idle(self) -> None:
        """A moment passes in which the agent does not act; the Others see that too."""
        if self._watching:
            for other in self._others.values():
                other.saw(self._moment, None)
            self._moment += 1

    def remarks(self) -> dict[str, dict[str, Any]]:
        """What each Other says now, by who says it."""
        self._watching = True
        return {name: other.remark() for name, other in self._others.items()}

    def __getattr__(self, name: str) -> Any:
        # Anything else the host reads of its environment is the region's.
        return getattr(self._region, name)


__all__ = ["ALTERNATION", "REPEAT_AT", "Onlooker", "World", "act_of"]
