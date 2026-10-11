"""The onlooker (tag E): an Other in the world, who sees the agent act and says what it sees.

It stands outside the agent and outside the host: in the world, beside the
region. It sees acts, opaque, and moments without one — nothing of any game. The
host hears it on a channel of its own. The mismatch is between the agent, who
expected no objection, and the onlooker, who has one; it holds when the
onlooker changes its stance — and each moment the agent stands still, it says so
again.
"""

from __future__ import annotations

from arc3.decisions import situation_fit
from arc3.host import Arc3Source
from arc3.observe import ONLOOKER_CHANNEL, admit, move_value, transducers
from arc3.action import Move
from arc3.command import WAIT
from arc3.organs import ARC_ORGANS
from arc3.task import TASK_CUE
from dil.loop.cycle import Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from mind.mind import Mind, mind_rule
from mind.models.grid import GridInducer
from tests.test_arc3_host import FakeEnv, FakeGameAction, f
from world import REPEAT_AT, Onlooker, World, act_of


def a(n, **data):
    return {"act": n, **data}


def saw(onlooker, *acts):
    for moment, act in enumerate(acts):
        onlooker.saw(moment, act)


# ── what it makes of what it sees ──


def test_it_says_nothing_until_an_act_repeats_and_then_points_where_it_began():
    o = Onlooker()
    saw(o, a(2), a(1), a(1), a(1))
    assert o.remark() == {"remark": None}
    o.saw(4, a(1))
    assert REPEAT_AT == 4
    assert o.remark() == {"remark": "repeating", "act": a(1), "since": 1, "at_least": 4}
    o.saw(5, a(1))
    assert o.remark()["since"] == 1, "the same view, however long it runs"


def test_a_repetition_that_lasts_is_said_again_every_repeat_at_more():
    o = Onlooker()
    saw(o, a(1), a(1), a(1), a(1))
    said = [o.remark()]
    for moment in range(4, 13):
        o.saw(moment, a(1))
        said.append(o.remark())
    assert [r["at_least"] for r in said] == [4, 4, 4, 4, 8, 8, 8, 8, 12, 12]
    changes = sum(1 for before, now in zip(said, said[1:]) if before != now)
    assert changes == 2, "between nudges it holds what it said: a run kept on purpose is not stopped at every act"
    assert {r["since"] for r in said} == {0}


def test_it_reads_an_alternation_as_going_back_and_forth():
    o = Onlooker()
    saw(o, a(3), a(1), a(2), a(1), a(2))
    assert o.remark() == {"remark": "back-and-forth", "acts": [a(1), a(2)], "since": 1, "at_least": 4}


def test_a_back_and_forth_that_lasts_is_said_again_each_alternation_more():
    # Held and never said again, it let the agent go back and forth for hundreds
    # of cycles with one remark (LOG.md, 2026-09-27).
    o = Onlooker()
    saw(o, a(3), a(1), a(2), a(1), a(2))
    said = [o.remark()]
    for moment in range(5, 13):
        o.saw(moment, a(1) if moment % 2 else a(2))
        said.append(o.remark())
    assert [r["at_least"] for r in said] == [4, 4, 4, 4, 8, 8, 8, 8, 12]
    assert {r["since"] for r in said} == {1}


def test_standing_still_is_said_again_each_moment_it_lasts():
    o = Onlooker()
    saw(o, a(1), None)
    assert o.remark() == {"remark": "standing still", "since": 1, "for": 1}
    o.saw(2, None)
    assert o.remark() == {"remark": "standing still", "since": 1, "for": 2}, "the same fact, longer: a new nudge"
    o.saw(3, a(1))
    assert o.remark() == {"remark": None}


def test_it_knows_no_game_every_act_is_just_an_act():
    o = Onlooker()
    saw(o, a("RESET"), a("RESET"), a("RESET"), a("RESET"))
    assert o.remark()["remark"] == "repeating", "no act is special to it"
    o = Onlooker()
    saw(o, a(6, x=1, y=1), a(6, x=2, y=2), a(6, x=3, y=3), a(6, x=4, y=4))
    assert o.remark() == {"remark": None}, "acts that differ in what they carry are different acts"


# ── where it stands: in the world, not in the host ──


def test_the_world_shows_each_act_to_the_others_once_they_watch():
    env = FakeEnv([f(), f(), f()])
    o = Onlooker()
    world = World(env, others={"onlooker": o})
    world.step(FakeGameAction(0))                 # before anyone watches: opening, unseen
    assert world.remarks() == {"onlooker": {"remark": None}}
    world.step(FakeGameAction(1))
    world.idle()
    assert o.remark() == {"remark": "standing still", "since": 1, "for": 1}
    assert env.steps == [(0, {}), (1, {})], "the region got the acts; the idle moment reached it not"
    assert act_of(FakeGameAction(6), {"x": 3, "y": 4}) == {"act": 6, "x": 3, "y": 4}


def test_the_host_hears_the_onlooker_and_keeps_cycling_while_the_body_stands_still():
    # The body's acts are scripted here (`plan`), not the mind's: the mind only
    # fills T5, as it would in a run.
    mind = Mind(GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=mind_rule(mind), fit=situation_fit),
            t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    source = Arc3Source(World(FakeEnv([f()] * 10), others={"onlooker": Onlooker()}),
                        FakeGameAction, action_budget=6)
    heard = []
    plan = [move_value(Move(1))] + [dict(WAIT)] * 4
    for action in plan:
        inp = source.next()
        assert inp is not None
        heard.append([s.raw_payload for s in inp.signals if s.source_id == ONLOOKER_CHANNEL])
        cycle.run(inp)
        source.deliver(Emission(action=action))
    inp = source.next()
    assert inp is not None and {s.source_id for s in inp.signals} == {ONLOOKER_CHANNEL}, \
        "a cycle the body stood still in carries only what is heard"
    assert inp.afforded == {"onlooker"}, "the region is not counted absent: nothing was done to it"
    assert heard[-1] == [{"entity": "onlooker", "remark": "standing still", "since": 1, "for": 3}]
    assert source.next() is None, "standing still counts against the budget: it has an end"
    assert source.spent == 1 and source.waits == 4, "the waits cost no action"
    scars = [r for r in events.all() if type(r).__name__ == "EventRecord" and r.event.source_id == "onlooker"]
    assert len({r.anchor.cycle for r in scars}) == 3, "each nudge is a new remark, and collides"
