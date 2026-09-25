"""The region served from another process: one arcade and scorecard, many games at once."""

from __future__ import annotations

from arc3.host import Arc3Source
from arc3.observe import move_value
from arc3.action import Move
from dil.loop.layers.t2 import Emission
from tests.test_arc3_host import FakeEnv, FakeGameAction, f
from world.remote import Regions, RemoteRegion, plain, serve


def test_a_game_made_in_one_process_is_played_from_another_as_plain_data():
    env = FakeEnv([f(1, actions=(6,)), f(2, actions=(6,))])
    address = serve(Regions({"g1": env}, FakeGameAction), b"k")
    region = RemoteRegion(address, b"k", "g1")
    source = Arc3Source(region, FakeGameAction, action_budget=5)
    assert source.next() is not None, "the opening frame came across"
    source.deliver(Emission(action=move_value(Move(6, 3, 4))))
    assert env.steps[-1] == (6, {"x": 3, "y": 4}), "the action's id and its cell reached the game"
    assert source.next() is not None


def test_plain_is_what_the_host_reads_and_nothing_else():
    got = plain(f(1, state="GAME_OVER", actions=(6,)))
    assert set(got) == {"game_id", "frame", "state", "available_actions", "levels_completed", "win_levels"}
    assert got["state"] == "GAME_OVER" and got["available_actions"] == [6]
    assert plain(None) is None
