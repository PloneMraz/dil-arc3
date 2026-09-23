"""The thinking organ.

It supplies the expectation and nothing else — no test here hands it an afforded
set or asks it for a move, because it can do neither.
"""

from __future__ import annotations

from arc3.effect import diff
from arc3.model import (
    MIN_MOVER_VOTES,
    NO_CONTEXT,
    OFF_GRID,
    create_model,
    predict_rule,
)
from arc3.observe import effect_value, observe
from arc3.action import Move
from dil.loop.layers.t3 import T3Input, create_t3
from dil.loop.types import ModField
from arc3 import GAME_CHANNEL, game_transducer
from tests.test_arc3_effect import framed, marker


def moved(from_rc, to_rc, value=9):
    a, b = framed({from_rc: value}), framed({to_rc: value})
    return diff(a, b)


def teach(model, entity, before, after, times=MIN_MOVER_VOTES):
    """Teach the way the host does: name the situation off the frame the move
    was made from, THEN accrue what it did."""
    for _ in range(times):
        context = model.context(before, entity)
        model.observe(entity, context, diff(before, after))


def teach_up(model, entity="action:1", times=MIN_MOVER_VOTES):
    teach(model, entity, framed({(30, 30): 9}), framed({(25, 30): 9}), times)


# ── what it learns, and refuses to learn too fast ──


def test_the_mover_is_learned_not_configured():
    model = create_model()
    assert model.mover is None
    teach_up(model)
    assert model.mover == 9


def test_the_background_is_not_mistaken_for_the_mover():
    """When a thing steps into empty space the hole it leaves steps the other
    way, so the background collects displacement votes it has not earned. It
    ties with, and can beat, the thing that actually moved."""
    model = create_model()
    teach_up(model)
    assert model.background == 0
    assert model.mover == 9


def test_one_sighting_is_not_enough_to_trust_a_mover():
    """One observation is a coincidence."""
    model = create_model()
    teach_up(model, times=1)
    assert MIN_MOVER_VOTES > 1
    assert model.mover is None


def test_each_affordance_learns_its_own_displacement():
    model = create_model()
    teach_up(model, "action:1")
    teach(model, "action:2", framed({(30, 30): 9}), framed({(35, 30): 9}))
    assert model.displacement("action:1") == (-5, 0)
    assert model.displacement("action:2") == (5, 0)


# ── naming the situation ──


def test_there_is_no_context_before_anything_is_known():
    model = create_model()
    assert model.context(framed(marker(30, 30)), "action:1") == NO_CONTEXT


def test_the_context_names_what_lies_where_the_move_would_land():
    model = create_model()
    teach_up(model)
    # A wall of 7s five rows above the mover at (30, 30).
    frame = framed({(30, 30): 9, (25, 30): 7})
    assert "7:1" in model.context(frame, "action:1")


def test_the_same_obstruction_in_two_places_reads_as_one_situation():
    """Translation invariance again — the property the effect signature rests
    on. Without it the model would have to learn every wall separately."""
    model = create_model()
    teach_up(model)
    here = model.context(framed({(30, 30): 9, (25, 30): 7}), "action:1")
    there = model.context(framed({(12, 8): 9, (7, 8): 7}), "action:1")
    assert here == there != NO_CONTEXT


def test_an_edge_of_the_grid_is_named_as_such():
    model = create_model()
    teach_up(model)
    frame = framed({(2, 30): 9})  # five rows up is off the grid
    assert f"{OFF_GRID}:1" in model.context(frame, "action:1")


def test_an_unknown_affordance_has_no_context():
    model = create_model()
    teach_up(model, "action:1")
    assert model.context(framed(marker(30, 30)), "action:9") == NO_CONTEXT


# ── predicting ──


def test_an_unmet_affordance_has_nothing_to_predict():
    assert create_model().predict("action:1", NO_CONTEXT) is None


def test_a_situation_seen_before_answers_from_its_own_evidence():
    model = create_model()
    blocked, moves = moved((30, 30), (30, 30)), moved((30, 30), (25, 30))
    model.observe("action:1", "wall", blocked)
    model.observe("action:1", "open", moves)
    model.observe("action:1", "open", moves)
    assert model.predict("action:1", "wall") == blocked
    assert model.predict("action:1", "open") == moves


def test_an_unseen_situation_falls_back_to_persistence():
    """It is never worse-informed than the rule it replaces."""
    model = create_model()
    last = moved((30, 30), (25, 30))
    model.observe("action:1", "open", last)
    assert model.predict("action:1", "a situation never met") == last


# ── the rule, and the order that is INV-8 in code ──


def unit_for(move, prev, now, context):
    host = observe(prev, move, now, diff(prev, now), t=0, context=context)
    t3 = create_t3({GAME_CHANNEL: game_transducer})
    units = t3.process(
        T3Input(signals=host.signals), ModField(), lambda *a, **k: None, lambda *a, **k: None
    ).units
    return units[0]


def test_the_first_sighting_predicts_the_observation_itself():
    model = create_model()
    rule = predict_rule(model)
    prev, now = framed(marker(30, 30)), framed(marker(25, 30))
    observed = unit_for(Move(1), prev, now, "open")
    assert rule("action:1", (), observed) is observed


def test_the_rule_predicts_before_it_accrues():
    """INV-8 in code. If the rule read this cycle's effect before predicting,
    the expectation would be built from the answer and the prediction error
    would be scoring itself.

    Two cycles in the SAME context with DIFFERENT effects: the second
    prediction must be the FIRST effect. If accrual happened first, it would be
    the second — the answer predicting itself.
    """
    model = create_model()
    rule = predict_rule(model)
    a, b, c = framed(marker(30, 30)), framed(marker(25, 30)), framed(marker(10, 10))

    first = unit_for(Move(1), a, b, "same-context")
    rule("action:1", (), first)

    second = unit_for(Move(1), a, c, "same-context")
    predicted = rule("action:1", (first,), second)

    assert predicted.content["value"]["effect"] == effect_value(diff(a, b))
    assert predicted.content["value"]["effect"] != second.content["value"]["effect"]


def test_only_the_effect_is_replaced_in_the_predicted_unit():
    """So T5's content comparison reduces to the effect — which is what tag H
    declares fit to be."""
    model = create_model()
    rule = predict_rule(model)
    a, b = framed(marker(30, 30)), framed(marker(25, 30))
    first = unit_for(Move(1), a, b, "ctx")
    rule("action:1", (), first)
    second = unit_for(Move(1), a, b, "ctx")
    predicted = rule("action:1", (first,), second)

    for key in ("entity", "game", "affords", "context"):
        assert predicted.content["value"][key] == second.content["value"][key]
    assert predicted.ref_frame == second.ref_frame
