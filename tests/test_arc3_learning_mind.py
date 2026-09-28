"""The learning mind — one mind, which learns the region from nothing — in the loop.

A 3x3 "game": ACTION1 moves the one lit cell a step right, ACTION2 a step left.
The mind brings no knowledge of it: it learns each transition as it takes it,
writes it as data built from the frame and report it came in, expects from it
the next time, and is curious about what it has not tried — and the trace a third
party reads says so.
"""

from __future__ import annotations

import pytest

from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
from mind.mind import Mind, mind_rule
from mind.learning import CHOICE_TAGS, HYPOTHESIS_TAGS, Learning
from mind.models.exact import CLOCK_WINDOW, ExactInducer, grid_key, things
from mind.organs import Step
from arc3.observe import FRAME_CHANNEL, STATUS_CHANNEL, admit, transducers
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


def lit(c: int, clock: int = 0) -> list[list[int]]:
    return [[1 if col == c else 0 for col in range(3)], [0, 0, 0], [clock % 2, 0, 0]]


def frame(before, after, action=1, x=None, y=None) -> Signal:
    return Signal(source_id=FRAME_CHANNEL, t=1, raw_payload={
        "entity": "frame", "before": [before], "grids": [after],
        "move": {"kind": "move", "actionId": action, "x": x, "y": y},
        "context": f"action:{action}",
    })


def status(state="NOT_FINISHED", levels=0, action=1, affords=(1, 2)) -> Signal:
    return Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
        "entity": "region",
        "status": {"stateFrom": "NOT_FINISHED", "stateTo": state, "levelsDelta": levels, "depthDelta": 0},
        "context": f"action:{action}", "affords": list(affords),
    })


def seated() -> Mind:
    """The one mind with its learning; its model's seat takes the inducer."""
    return Mind(ExactInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})


def create_mind() -> Mind:
    mind = seated()
    # What it reads, handed in as if recalled: the in-memory store admits no prior.
    mind.receive("task", MIND_TASK.payload, None)
    return mind


def test_the_mind_holds_its_learning_and_its_models_seat_takes_the_inducer():
    # Plone, 2026-09-28: the model is the replaceable computing; the learning is
    # the mind's, whatever its model. Seating a model does not replace it.
    inducer = ExactInducer(ARC_ORGANS)
    mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
    assert isinstance(mind.learning, Learning)
    assert mind.learning.inducer is inducer


def test_the_language_models_seat_is_kept_and_not_run():
    # Its earlier form sat in the learning's place (LOG.md, 2026-09-28): kept,
    # not run; its revision is the language inducer.
    from arc3.mind import UNSEATED, create_mind as seat_language
    with pytest.raises(NotImplementedError, match="earlier form"):
        seat_language()
    assert "language inducer" in UNSEATED


def loop():
    mind = create_mind()
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=mind_rule(mind)), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    return mind, cycle, data, events


def run(cycle, *signals):
    return cycle.run(HostCycleInput(signals=tuple(signals)))


def of_kind(data, kind):
    return [(k, d) for k, d in data.entries() if d.open.get("kind") == kind]


def test_what_it_takes_it_learns_as_data_built_from_the_frame_and_report():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())
    learned = of_kind(data, "hypothesis")
    assert len(learned) == 1
    datum_id, datum = learned[0]
    assert datum.open == HYPOTHESIS_TAGS and datum.fixed.provenance == "nascent"
    assert datum.payload["act"] == [1, None, None] and datum.payload["changed"] is True
    assert datum.payload["status"] == {"stateTo": "NOT_FINISHED", "levelsDelta": 0, "depthDelta": 0}
    written = {w.datum_id: w.built_from for r in events.all() if getattr(r, "activity_kind", None) == "cycle-seal"
               for w in r.activity.written}
    assert written[datum_id] == ("signal-0-0", "signal-0-1"), "built from the frame and the report it came in"


def test_it_commands_an_act_not_yet_taken_and_says_why():
    mind, cycle, data, events = loop()
    result = run(cycle, frame(lit(0), lit(1)), status())
    # From lit(1) nothing is known: both acts are untried; ACTION1 changed the
    # state once, ACTION2 never tried — the less known is the more wanted.
    assert mind.commands[-1] == (1, (2, None, None))
    choice = [d for _, d in of_kind(data, "choice")][-1]
    assert choice.open == CHOICE_TAGS and choice.payload["why"] == "not yet taken from here"
    move = {"kind": "move", "actionId": 2, "x": None, "y": None}
    assert result.tests == (move,), "the command is T5's test"
    from_t5 = [r for r in events.all() if getattr(r, "activity_kind", None) == "emission" and r.issuing_layer == 5]
    assert {"kind": "test", "action": move} in [r.action for r in from_t5], "recorded from T5, as a test"


def test_an_act_taken_again_is_expected_as_learned_and_the_expectation_is_the_datums():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())          # learned: from lit(0), ACTION1 -> lit(1)
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    run(cycle, frame(lit(0), lit(1)), status())          # the same act from the same state
    assert mind.holds == [0, 0, 1], "the third it expected, from what it learned"
    learned_id = of_kind(data, "hypothesis")[0][0]
    assert data.get(learned_id).fixed.provenance != "scar"


def test_the_same_act_giving_something_else_scars_the_datum_and_it_no_longer_holds():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    run(cycle, frame(lit(0), lit(2)), status())          # the same act, from the same state, elsewhere
    learned_id = of_kind(data, "hypothesis")[0][0]
    scars = [r for r in events.all() if type(r).__name__ == "EventRecord" and r.datum_id == learned_id]
    assert scars, "the expectation was the datum's, and the region refuted it"
    run(cycle, frame(lit(2), lit(1), action=2), status(action=2))
    refuted = [(k, d) for k, d in of_kind(data, "hypothesis") if d.payload["holds"] is False]
    assert refuted, "said in a datum of its own: it no longer predicts from it"
    written = {w.datum_id: w.built_from for r in events.all() if getattr(r, "activity_kind", None) == "cycle-seal"
               for w in r.activity.written}
    assert learned_id in written[refuted[0][0]], "built from the hypothesis it refutes"
    assert data.get(learned_id).payload["holds"] is True, "the first is not rewritten"
    assert [r for r in events.all() if getattr(r, "activity_kind", None) == "revision"] == [], \
        "nothing is revised in place (Plone, 2026-09-27)"


def test_a_hypothesis_right_more_often_than_wrong_is_still_held():
    # FIT_LAW (Plone, 2026-09-28): held while right more often than wrong.
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    run(cycle, frame(lit(0), lit(1)), status())          # borne out: 2 for, 0 against
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    run(cycle, frame(lit(0), lit(2)), status())          # not borne out: 2 for, 1 against
    model = mind.learning
    h = model._edges[(model.inducer.situation(lit(0)), (1, None, None))].hypothesis
    assert (h.supports, h.fails, h.holds) == (2, 1, True)
    assert not [d for _, d in of_kind(data, "hypothesis") if d.payload["holds"] is False]


def test_the_game_ended_is_met_with_reset():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(state="GAME_OVER"))
    assert mind.commands[-1] == (1, (0, None, None))
    assert mind.thoughts[-1].why.startswith("the region has ended")


def test_a_row_that_changes_whatever_is_done_is_the_clock_and_not_where_the_game_stands():
    inducer = ExactInducer(ARC_ORGANS)
    grids = [lit(0, clock=i) for i in range(CLOCK_WINDOW + 1)]
    for i in range(CLOCK_WINDOW):
        a = [1, 2, 3][i % 3]
        inducer.perceive(Step(before=grids[i], act=(a, None, None), after=grids[i + 1]), ("act", a))
    assert inducer.clock == frozenset({2})
    assert inducer.situation(lit(0, 0)) == inducer.situation(lit(0, 1))


def test_things_are_regions_of_one_colour_and_the_ground_is_left_out():
    grid = [[0] * 8 for _ in range(8)]
    grid[1][1] = grid[1][2] = 3
    grid[5][5] = 4
    found = things(grid)
    assert [(c, n) for c, n, _, _ in found] == [(4, 1), (3, 2)], "smallest first; the ground (0) is too large"
    assert found[0][2:] == (5, 5)


def test_clicking_that_never_did_anything_is_wanted_less_whatever_is_left_to_click():
    # ar25 and sk48 on Kaggle: 0 of ~200 clicks changed anything, and each new
    # thing to click was a new kind, so clicking went on (LOG.md). The action is
    # chosen first, over every kind of it.
    mind, cycle, data, events = loop()
    mind.learning._actions = {6: [20, 0, 0], 1: [5, 5, 0]}
    mind.learning._kinds = {("act", 1): [5, 5, 0]}
    run(cycle, frame(lit(0), lit(1)), status(affords=(1, 6)))
    assert mind.commands[-1][1][0] == 1, "the action that changes things, not an untried click"


def test_the_onlookers_word_puts_the_act_it_names_behind_the_others():
    from arc3.observe import ONLOOKER_CHANNEL
    from dil.loop.types import Signal
    def remark(said):
        return Signal(source_id=ONLOOKER_CHANNEL, t=1, raw_payload={"entity": "onlooker", **said})

    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(), remark({"remark": None}))
    said = {"remark": "repeating", "act": {"act": "ACTION2"}, "since": 0, "at_least": 4}
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), remark(said))   # its word changed
    assert (mind.learning._here, (2, None, None)) in mind.learning.objections()
    thought = [d for _, d in of_kind(data, "thought")]
    assert thought and thought[-1].payload["objected"] == [[mind.learning._here, [2, None, None]]], \
        "what was objected to, and where, is written"


def test_what_the_onlooker_said_is_named_in_what_was_built_from_it():
    from arc3.observe import ONLOOKER_CHANNEL
    def remark(said):
        return Signal(source_id=ONLOOKER_CHANNEL, t=1, raw_payload={"entity": "onlooker", **said})

    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(), remark({"remark": None}))
    said = {"remark": "repeating", "act": {"act": "ACTION2"}, "since": 0, "at_least": 4}
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), remark(said))   # heard in cycle 1
    run(cycle, frame(lit(0), lit(1)), status(), remark(said))                     # quoted by the choice
    written = {w.datum_id: w.built_from for r in events.all() if getattr(r, "activity_kind", None) == "cycle-seal"
               for w in r.activity.written}
    thought_id = sorted(k for k, _ in of_kind(data, "thought"))[0]
    assert "signal-1-2" in written[thought_id], "the thought names the remark it objected on"
    quoting = [k for k, d in of_kind(data, "choice") if d.payload.get("onlooker")]
    assert quoting and all(any(s.endswith("-2") and s.startswith("signal-") for s in written[k]) for k in quoting), \
        "a choice that quotes the onlooker names its remark"


# ── the onlooker's word strikes the mind (Plone, 2026-09-27) ──

def _remark(said):
    from arc3.observe import ONLOOKER_CHANNEL
    from dil.loop.types import Signal
    return Signal(source_id=ONLOOKER_CHANNEL, t=1, raw_payload={"entity": "onlooker", **said})


QUIET = {"remark": None}


def test_the_word_strikes_before_the_body_moves_and_the_mind_commands_again():
    # From lit(1) the untried act the mind would take is ACTION2 (it tried 1).
    # The onlooker objects to ACTION2 in the same cycle: the mind thinks and
    # commands again before the body moves, and the body carries out the last.
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    said = {"remark": "repeating", "act": {"act": "ACTION2"}, "since": 0, "at_least": 4}
    result = run(cycle, frame(lit(0), lit(1)), status(), _remark(said))
    moves = [t for t in result.tests]
    assert len(moves) == 2, "the command it gave on the status, and the one after the word"
    assert moves[0]["actionId"] == 2 and moves[1]["actionId"] != 2
    from arc3.command import carry_out
    from dil.loop.cycle import RespondContext
    from dil.loop.types import ModField
    assert carry_out(RespondContext(cycle=1, appraisal=result.appraisal, expectations=(), host=HostCycleInput(
        signals=(status(affords=(1, 2)),)), field=ModField(), tests=result.tests))["actionId"] == moves[1]["actionId"], \
        "the body carries out the last"


def test_said_again_after_it_was_answered_the_answer_is_scarred():
    mind, cycle, data, events = loop()
    said = {"remark": "repeating", "act": {"act": "ACTION1"}, "since": 0, "at_least": 4}
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(said))   # answered here
    answer_id = sorted(k for k, _ in of_kind(data, "thought"))[0]
    run(cycle, frame(lit(0), lit(1)), status(), _remark({**said, "at_least": 8}))  # the answer came back
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark({**said, "at_least": 8}))
    moved = [(r.from_, r.to) for r in events.all() if getattr(r, "activity_kind", None) == "provenance"
             and r.datum_id == answer_id]
    assert ("running", "scar") in moved, f"the answer was what the expectation was, and it failed: {moved}"


def test_quiet_after_an_answer_is_the_answer_holding_and_lifts_the_objection():
    mind, cycle, data, events = loop()
    said = {"remark": "repeating", "act": {"act": "ACTION2"}, "since": 0, "at_least": 4}
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    r = run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(said))
    assert mind.learning.objections()
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(QUIET))
    assert mind.learning.objections() == set(), "the onlooker stopped saying it: lifted (H7 (ii))"
    choices = [d.payload for _, d in of_kind(data, "choice") if d.payload.get("lifted")]
    assert choices, "what was lifted is written"


def test_a_back_and_forth_is_objected_to_at_the_states_it_ran_through():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(QUIET))
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    said = {"remark": "back-and-forth", "acts": [{"act": "ACTION1"}, {"act": "ACTION2"}], "since": 0,
            "at_least": 4}
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(said))
    model = mind.learning
    s0, s1 = model.inducer.situation(lit(0)), model.inducer.situation(lit(1))
    got = model.objections()
    assert (s0, (1, None, None)) in got and (s1, (2, None, None)) in got, "each act where it was taken"
    assert (s0, (2, None, None)) not in got, "not the act that leaves the loop from here"


def test_a_way_through_an_objected_act_is_taken_only_when_there_is_no_other():
    from mind.learning import Edge
    mind, cycle, data, events = loop()
    model = mind.learning
    # A known state a with two known ways out, 1 and 2, both to states with an
    # act not yet taken; 1 objected to at a.
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    here = model._here
    model._objected[("repeating", (1, None, None))] = {(model._now_raw, (1, None, None))}
    assert (here, (1, None, None)) in model.objections()
    first = [e for e in model._out.get(here, {}).values()]
    path = model._path(here, lambda n: n != here, (1, 2), avoid=model.objections())
    assert path is None or path[0][0] != (1, None, None)


def test_every_known_act_objected_to_the_act_that_is_always_open():
    # Every act at every state known: lit(0) and lit(1), ACTION1 and ACTION2 each.
    mind, cycle, data, events = loop()
    model = mind.learning
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    run(cycle, frame(lit(1), lit(1), action=1), status(), _remark(QUIET))
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(QUIET))
    run(cycle, frame(lit(0), lit(0), action=2), status(action=2), _remark(QUIET))
    model._learned_since_reset = False
    here_raw = model._now_raw
    said = ("repeating", (1, None, None))
    model._objected[said] = {(here_raw, (1, None, None)), (here_raw, (2, None, None))}
    ctx = mind._context("command")
    ctx.remark = {"remark": "repeating", "act": {"act": "ACTION1"}}
    proposal, _ = model.propose(ctx)
    assert proposal.act == model.organs.reset and "objected" in proposal.why, proposal


def test_a_way_whose_first_act_is_objected_is_taken_only_when_there_is_no_other_and_it_says_so():
    mind, cycle, data, events = loop()
    model = mind.learning
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(QUIET))
    # At lit(0): ACTION1 known (to lit(1), where ACTION1 is untried); ACTION2 untried.
    said = ("repeating", (1, None, None))
    model._objected[said] = {(model._now_raw, (1, None, None)), (model._now_raw, (2, None, None))}
    ctx = mind._context("command")
    ctx.remark = {"remark": "repeating", "act": {"act": "ACTION1"}}
    proposal, _ = model.propose(ctx)
    assert proposal.act == (1, None, None) and "no other way" in proposal.why, proposal


def test_told_it_stands_still_with_nothing_to_do_it_resets():
    mind, cycle, data, events = loop()
    model = mind.learning
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    model._learned_since_reset = False
    ctx = mind._context("command")
    ctx.remark = {"remark": "standing still", "since": 1, "for": 1}
    ctx.offers = ()
    proposal, _ = model.propose(ctx)
    assert proposal.act == model.organs.reset and "standing still" in proposal.why


def test_an_objection_survives_the_clock_growing():
    mind, cycle, data, events = loop()
    model = mind.learning
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    said = {"remark": "repeating", "act": {"act": "ACTION2"}, "since": 0, "at_least": 4}
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2), _remark(said))
    before = model.objections()
    model.inducer.clock = frozenset({2})
    model._reindex(())
    assert {a for _, a in model.objections()} == {a for _, a in before}
    assert all(state in model._state_of.values() for state, _ in model.objections()), "read under the new clock"


def test_the_field_reaches_the_mind_and_alertness_lets_it_think_more_in_a_cycle():
    from dil.loop.types import ModField
    from mind.mind import mind_rule
    mind, cycle, data, events = loop()
    rule = mind_rule(mind)
    f = ModField(params={"alertness": 1.0}, t=0)
    rule("x", (), __import__("dil.loop.types", fromlist=["InfoUnit"]).InfoUnit(
        content={"channel": "none", "value": 1}, ref_frame=__import__("dil.loop.types", fromlist=["RefFrame"]).RefFrame(bound_layer=3, ref="x"), t=0), field=f)
    assert mind._field is f and mind._context("x").field is f


def test_a_mind_that_held_no_aim_at_its_first_step_commands_once_it_holds_one():
    # Without an onlooker nothing arrives in a cycle the body stood still in, so a
    # mind that held no aim at its first step, and was never asked again, stood
    # for the whole run (LOG.md, 2026-09-28). Once what it reads comes back and it
    # holds an aim, while the body waits, it commands.
    mind = seated()   # the task not yet recalled
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=mind_rule(mind)), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    first = run(cycle, frame(lit(0), lit(1)), status())
    assert first.tests == () and mind.commands[-1][1] is None, "no aim yet: nothing commanded"
    pushed: list = []
    mind.take_return({"open": dict(MIND_TASK.open), "payload": MIND_TASK.payload, "entity": MIND_TASK.id},
                     write=lambda request: None, ask=None, test=pushed.append)
    assert pushed and mind.commands[-1][1] is not None, "the aim held, the waiting body gets a command"


def _grid(i: int) -> list[list[int]]:
    """A 3x3 grid of its own for each i: a state apart from every other."""
    return [[i % 16, 0, 0], [0, (i // 16) % 16, 0], [0, 0, 0]]


def test_told_once_it_repeats_while_every_step_goes_somewhere_new_it_keeps_on():
    mind, cycle, data, events = loop()
    for i in range(1, 4):
        run(cycle, frame(_grid(i), _grid(i + 1), action=1), status(), _remark(QUIET))
    said = {"remark": "repeating", "act": {"act": "ACTION1"}, "since": 0, "at_least": 4}
    run(cycle, frame(_grid(4), _grid(5), action=1), status(), _remark(said))
    thought = [d.payload for _, d in of_kind(data, "thought")][-1]
    assert "kept_on" in thought and mind.learning.objections() == set(), \
        "its own steps say the repetition is getting somewhere: it keeps on, and says why"
    assert mind._answer == (), "it expects to hear it again if it is wrong, not the onlooker to stop"


def test_told_again_it_objects():
    mind, cycle, data, events = loop()
    for i in range(1, 4):
        run(cycle, frame(_grid(i), _grid(i + 1), action=1), status(), _remark(QUIET))
    said = {"remark": "repeating", "act": {"act": "ACTION1"}, "since": 0, "at_least": 4}
    run(cycle, frame(_grid(4), _grid(5), action=1), status(), _remark(said))
    for i in range(5, 8):
        run(cycle, frame(_grid(i), _grid(i + 1), action=1), status(), _remark(said))   # held: no collision
    assert mind.learning.objections() == set()
    run(cycle, frame(_grid(8), _grid(9), action=1), status(), _remark({**said, "at_least": 8}))
    assert any(a == (1, None, None) for _, a in mind.learning.objections()), "said again: it objects"
    assert [d.payload for _, d in of_kind(data, "thought")][-1]["again"] is True


def test_a_repetition_that_goes_nowhere_new_is_objected_to_at_once():
    mind, cycle, data, events = loop()
    for _ in range(3):
        run(cycle, frame(_grid(1), _grid(1), action=1), status(), _remark(QUIET))
    said = {"remark": "repeating", "act": {"act": "ACTION1"}, "since": 0, "at_least": 4}
    run(cycle, frame(_grid(1), _grid(1), action=1), status(), _remark(said))
    assert any(a == (1, None, None) for _, a in mind.learning.objections())


def test_short_term_perception_is_as_long_as_t5s_window_under_the_field():
    from dil.loop.types import ModField
    mind, cycle, data, events = loop()
    for i in range(1, 30):
        run(cycle, frame(_grid(i), _grid(i + 1), action=1), status(), _remark(QUIET))
    for field, n in ((ModField(params={}), 16), (ModField(params={"exploration": 1.0}), 8),
                     (ModField(params={"exploration": 0.0}), 24)):
        mind._field = field
        assert len(mind._context("x").seen) == n, (field.params, n)


def test_a_choice_commanded_again_says_which_it_replaces():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    said = {"remark": "repeating", "act": {"act": "ACTION2"}, "since": 0, "at_least": 4}
    run(cycle, frame(lit(0), lit(1)), status(), _remark(said))
    choices = [d.payload for _, d in of_kind(data, "choice")]
    last = choices[-1]
    assert last["supersedes"]["chose"] == [2, None, None] and last["chose"] != [2, None, None], \
        "the second choice of the cycle, the one the body carries out, names the one it replaces"
    assert "supersedes" not in choices[-2]


def test_what_it_reads_recalled_again_later_is_no_reason_to_command():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(), _remark(QUIET))
    mind.commands.append((mind.frame_calls, None))    # the body waits, for its own reasons
    pushed: list = []
    mind.take_return({"open": dict(MIND_TASK.open), "payload": MIND_TASK.payload, "entity": MIND_TASK.id},
                     write=lambda request: None, ask=None, test=pushed.append)
    assert pushed == [], "only its first arrival commands a body waiting for want of an aim"


def test_curiosity_counts_somewhere_new_not_a_change():
    # S2b (Plone, 2026-09-28): an act that only takes it back where it stood
    # changes the state and reaches nowhere new.
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())                     # somewhere new
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))   # back: a change, not new
    assert mind.learning._actions[1][:2] == [1, 1]
    assert mind.learning._actions[2][:2] == [1, 0]
