"""The region served from another process: one arcade, one scorecard, many games at once.

Scoring allows one `make` per game and one scorecard, and the official harness
plays every game in threads of one process. The mind bounds the programs it
runs with SIGALRM, which only the main thread of a process can use; so each game
here is played in a process of its own, and the region — the arcade, its
scorecard and every game made on it — stays in the one process that made them.
A game's process reaches its region through this: `reset`, and `step` with an
action's id and data, answered with the frame as plain data.

Plain data both ways, by design. The engine's `GameAction` does not survive a
pickle (`GameAction(1)` raises; `action.py`), and the frame the host reads needs
only its grids, its state's name, its actions and its level counts.

This is the world's side, like the region itself: it chooses nothing and reads
nothing into what it carries.
"""

from __future__ import annotations

import threading
from multiprocessing.managers import BaseManager
from types import SimpleNamespace
from typing import Any


def plain(raw: Any) -> dict[str, Any] | None:
    """An engine frame as plain data: what `arc3.frame.read_frame` reads, no more."""
    if raw is None:
        return None
    state = getattr(raw, "state", None)
    return {
        "game_id": str(getattr(raw, "game_id", "") or ""),
        "frame": [[[int(c) for c in row] for row in grid] for grid in (getattr(raw, "frame", None) or [])],
        "state": getattr(state, "name", None) or str(state),
        "available_actions": [int(a) for a in (getattr(raw, "available_actions", None) or [])],
        "levels_completed": int(getattr(raw, "levels_completed", 0) or 0),
        "win_levels": int(getattr(raw, "win_levels", 0) or 0),
    }


class Regions:
    """The games made on one arcade, played on request from other processes."""

    def __init__(self, envs: dict[str, Any], action_cls: Any) -> None:
        self._envs = envs
        self._ga = action_cls

    def games(self) -> list[str]:
        return list(self._envs)

    def reset(self, game: str) -> dict[str, Any] | None:
        return plain(self._envs[game].reset())

    def step(self, game: str, action_id: int, data: dict[str, int] | None) -> dict[str, Any] | None:
        action = self._ga.from_id(int(action_id))
        if data:
            action.set_data(data)
        return plain(self._envs[game].step(action, data or None))


class _Server(BaseManager):
    pass


class _Client(BaseManager):
    pass


_Client.register("regions")


def serve(regions: Regions, authkey: bytes, address: tuple[str, int] = ("127.0.0.1", 0)) -> tuple[str, int]:
    """Serve the regions from this process, on a thread; returns the address."""
    _Server.register("regions", callable=lambda: regions)
    manager = _Server(address=address, authkey=authkey)
    server = manager.get_server()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.address


class RemoteRegion:
    """One game of the served regions, as a region the host can open and act on."""

    def __init__(self, address: tuple[str, int], authkey: bytes, game: str) -> None:
        client = _Client(address=address, authkey=authkey)
        client.connect()
        self._regions = client.regions()
        self._game = game

    def reset(self) -> SimpleNamespace | None:
        out = self._regions.reset(self._game)
        return None if out is None else SimpleNamespace(**out)

    def step(self, action: Any, data: dict[str, int] | None = None) -> SimpleNamespace | None:
        action_id = getattr(action, "value", action)
        out = self._regions.step(self._game, int(action_id), dict(data) if data else None)
        return None if out is None else SimpleNamespace(**out)


__all__ = ["Regions", "RemoteRegion", "plain", "serve"]
