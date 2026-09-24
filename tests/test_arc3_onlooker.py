"""The onlooker (tag E): an Other outside the agent, judging how it behaves.

It sees the moves the agent commits and whether the level moved, nothing else.
It says when it thinks the agent is stuck; the mismatch is between the agent,
who expected no objection, and the onlooker, who has one — and it holds only
when the onlooker changes its stance.
"""

from __future__ import annotations

from arc3.action import Move
from arc3.mind import ModelEndpoint, create_mind, mind_rule
from arc3.observe import ONLOOKER_CHANNEL, STATUS_CHANNEL, admit, move_value, transducers
from arc3.onlooker import REPEAT_AT, Onlooker, onlooked
from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log


def saw(onlooker: Onlooker, *moves, levelled_at=()):
    for cycle, m in enumerate(moves):
        move = m if isinstance(m, tuple) else (m, None, None)
        onlooker.saw(cycle, move, cycle in levelled_at)


# ── what it makes of what it sees ──


def test_it_says_nothing_until_a_move_repeats_and_then_points_where_it_began():
    o = Onlooker()
    saw(o, 2, 1, 1, 1)
    assert o.remark() == {"remark": None}
    o.saw(4, (1, None, None), False)
    assert REPEAT_AT == 4
    assert o.remark() == {"remark": "repeating", "move": [1, None, None], "since": 1}
    o.saw(5, (1, None, None), False)
    assert o.remark()["since"] == 1, "the same view, however long it runs"


def test_it_reads_an_alternation_as_the_agent_undoing_itself():
    o = Onlooker()
    saw(o, 3, 1, 2, 1, 2)
    assert o.remark() == {"remark": "back-and-forth", "moves": [[1, None, None], [2, None, None]], "since": 1}


def test_a_level_reached_is_not_being_stuck_and_a_reset_starts_over():
    o = Onlooker()
    saw(o, 1, 1, 1, 1, levelled_at={2})
    assert o.remark() == {"remark": None}, "only one move since the level moved"
    o = Onlooker()
    saw(o, 1, 1, 1, 0, 1)
    assert o.remark() == {"remark": None}


def test_clicks_at_different_places_are_different_moves():
    o = Onlooker()
    saw(o, (6, 1, 1), (6, 2, 2), (6, 3, 3), (6, 4, 4))
    assert o.remark() == {"remark": None}


# ── in the loop ──


class Body:
    """A region that reports its status, the level never moving."""

    def __init__(self, n: int) -> None:
        self.n, self.t, self.delivered = n, 0, []

    def next(self):
        if self.t >= self.n:
            return None
        self.t += 1
        return HostCycleInput(signals=(Signal(source_id=STATUS_CHANNEL, t=self.t, raw_payload={
            "entity": "region", "status": {"stateTo": "NOT_FINISHED", "levelsDelta": 0},
            "context": "action:1", "affords": [1, 2]}),), afforded=frozenset({"region"}))

    def deliver(self, response):
        self.delivered.append(response)


def no_model(*_):
    raise AssertionError("the model is not asked about the onlooker")


def test_the_mismatch_is_the_onlookers_change_of_stance_held_on_its_remark():
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=mind_rule(create_mind(ModelEndpoint(), chat_fn=no_model))),
            t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    source = onlooked(Body(12))
    plan = [1] * 7 + [2, 1, 2, 1, 2]
    scars_at = []
    for i, action in enumerate(plan):
        inp = source.next()
        assert "onlooker" in inp.afforded, "it is there every cycle: its silence is no absence"
        cycle.run(inp)
        mine = [r for r in events.all() if type(r).__name__ == "EventRecord" and r.event.source_id == "onlooker"]
        scars_at += [i] * (len(mine) - len(scars_at))
        source.deliver(Emission(action=move_value(Move(action))))

    # ACTION1 committed at cycles 0-3 is seen by cycle 4: "repeating" — one mismatch.
    # Kept while the agent keeps at it; the change of move ends it — a second.
    # 1 2 1 2, from the last ACTION1 at cycle 6, is seen by cycle 10 — a third.
    # Each scars both sides (v0.3.5): the remark that came, and the one expected.
    assert scars_at == [4, 4, 8, 8, 10, 10]
    remarks = [d for _, d in data.entries() if d.open == {"domain": "reflection", "kind": "remark",
                                                          "source": ONLOOKER_CHANNEL}]
    assert len(remarks) == 12, "every remark is kept as data"
    held = [r for r in events.all() if type(r).__name__ == "EventRecord" and r.event.source_id == "onlooker"]
    assert all(data.get(r.datum_id).open["kind"] == "remark" for r in held), "the scar is on the remark"
    assert set(data.get(held[0].datum_id).payload) == {"entity", "remark", "move", "since"}, \
        "a view of the behaviour, not a retold collision"
    said = [data.get(r.datum_id).payload for r in held]
    assert [(p["remark"], p.get("since")) for p in said] == [
        ("repeating", 0), (None, None),        # it objected; the agent expected silence
        (None, None), ("repeating", 0),        # it took it back; the agent expected the objection
        ("back-and-forth", 6), (None, None),   # it objected again
    ]
