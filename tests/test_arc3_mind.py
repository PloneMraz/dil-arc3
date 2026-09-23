"""The thinking algorithm, and the bridge it plugs into.

It supplies the expectation and nothing else — no test here hands it an afforded
set or asks it for a move, because it can do neither.
"""

from __future__ import annotations

import json

from arc3 import Move, observe
from arc3.mind import (
    PROGRESS_WINDOW,
    CONTEXTS_KNOWN,
    CONTEXT_NOVELTY,
    NO_CONTEXT,
    create_mind,
    observed_outcome,
    predict_rule,
    situation_of,
)
from arc3.observe import VISION_CHANNEL, transducers
from dil.loop.layers.t3 import T3Input, create_t3
from dil.loop.layers.t4 import STRANGER, T4Input, create_t4
from dil.loop.types import ModField
from tests.test_arc3_perceive import framed


def thing(r: int, c: int, value: int = 9, **kw):
    return framed({(r, c): value, (r, c + 1): value}, **kw)


def a_cycle(move=Move(1), before=None, after=None):
    before = before if before is not None else thing(30, 30)
    after = after if after is not None else thing(25, 30)
    return observe(before, move, after, t=7)


def units_of(host):
    t3 = create_t3(transducers())
    return t3.process(
        T3Input(signals=host.signals), ModField(), lambda *a: None, lambda *a: None
    ).units


NO_OP = lambda *a, **k: None


# ── what travels inward ──


def test_one_signal_per_Other_and_one_for_the_region():
    host = a_cycle()
    entities = [s.raw_payload["entity"] for s in host.signals]
    assert "region" in entities
    assert any(e.startswith("thing:") for e in entities)
    assert len(entities) == len(set(entities)), "one signal per Other"


def test_things_arrive_on_the_vision_channel():
    host = a_cycle()
    vision = [s for s in host.signals if s.source_id == VISION_CHANNEL]
    assert vision and all(s.raw_payload["entity"].startswith("thing:") for s in vision)


def test_the_context_is_what_the_agent_just_did():
    host = a_cycle(Move(3))
    assert all(s.raw_payload["context"] == "action:3" for s in host.signals)


def test_action6_coordinates_are_not_part_of_the_context():
    """Declared: 4096 contexts that each recur once would let nothing accrue."""
    a = a_cycle(Move(6, 1, 1)).signals[0].raw_payload["context"]
    b = a_cycle(Move(6, 50, 20)).signals[0].raw_payload["context"]
    assert a == b == "action:6"


def test_the_payload_is_json_shaped_so_t5_can_compare_it():
    payload = a_cycle().signals[0].raw_payload
    assert json.loads(json.dumps(payload)) == payload


def test_the_grid_never_travels_inward():
    for signal in a_cycle().signals:
        assert "grids" not in signal.raw_payload
        assert "cells" not in signal.raw_payload


# ── the loop's own seams bind it ──


def test_t4s_default_resolver_binds_every_Other():
    """No custom resolver needed: the payload carries the `entity` key T4's
    declared default reads."""
    bound = create_t4().process(
        T4Input(units=units_of(a_cycle())), ModField(), NO_OP, NO_OP
    ).bound
    ids = [b.entity_id for b in bound]
    assert STRANGER not in ids
    assert "region" in ids


def test_several_Others_reach_T4_at_once():
    """What the affordance reading could never do — and why T8 produced nothing.
    T8's RelValue needs N >= 2."""
    before = framed({(5, 5): 9, (20, 20): 3, (40, 40): 7})
    after = framed({(6, 5): 9, (20, 20): 3, (40, 40): 7})
    bound = create_t4().process(
        T4Input(units=units_of(observe(before, Move(1), after, t=1))),
        ModField(), NO_OP, NO_OP,
    ).bound
    assert len({b.entity_id for b in bound}) >= 4


# ── the mind ──


def test_an_unmet_Other_has_nothing_to_predict():
    assert create_mind().predict("thing:9", "action:1") is None


def test_a_situation_met_before_answers_by_majority():
    mind = create_mind()
    mind.observe("thing:9", "action:1", {"moved": [0, 0]})
    mind.observe("thing:9", "action:1", {"moved": [-5, 0]})
    mind.observe("thing:9", "action:1", {"moved": [-5, 0]})
    assert mind.predict("thing:9", "action:1") == {"moved": [-5, 0]}


def test_an_unmet_situation_falls_back_to_what_the_Other_last_did():
    mind = create_mind()
    mind.observe("thing:9", "action:1", {"moved": [-5, 0]})
    assert mind.predict("thing:9", "action:4") == {"moved": [-5, 0]}


def test_two_Others_are_kept_apart():
    mind = create_mind()
    mind.observe("thing:9", "action:1", {"moved": [-5, 0]})
    mind.observe("thing:3", "action:1", {"moved": [0, 0]})
    assert mind.predict("thing:9", "action:1") != mind.predict("thing:3", "action:1")
    assert mind.entities_known() == 2


# ── reading an observation ──


def test_a_thing_reports_a_change_and_the_region_a_status():
    units = units_of(a_cycle())
    outcomes = [observed_outcome(u) for u in units]
    assert all(o is not None for o in outcomes)
    assert any("moved" in o for o in outcomes if isinstance(o, dict))
    assert any("levelsDelta" in o for o in outcomes if isinstance(o, dict))


def test_the_situation_is_read_off_the_observation():
    assert situation_of(units_of(a_cycle(Move(2)))[0]) == "action:2"


# ── the rule, and the order that is INV-8 in code ──


def test_the_first_sighting_predicts_the_observation_itself():
    rule = predict_rule(create_mind())
    unit = units_of(a_cycle())[0]
    assert rule(unit.content["value"]["entity"], (), unit) is unit


def test_the_rule_predicts_before_it_accrues():
    """INV-8 in code. Two cycles in the SAME situation with DIFFERENT outcomes:
    the second prediction must be the FIRST outcome. If accrual ran first it
    would be the second — the answer predicting itself."""
    mind = create_mind()
    rule = predict_rule(mind)

    first = units_of(a_cycle(Move(1), thing(30, 30), thing(25, 30)))[0]
    entity = first.content["value"]["entity"]
    rule(entity, (), first)

    second = units_of(a_cycle(Move(1), thing(30, 30), thing(30, 30)))[0]
    predicted = rule(entity, (first,), second)

    assert predicted.content["value"]["change"]["moved"] == [-5, 0]
    assert predicted.content["value"]["change"] != second.content["value"]["change"]


def test_only_the_outcome_is_replaced_in_the_predicted_unit():
    mind = create_mind()
    rule = predict_rule(mind)
    first = units_of(a_cycle())[0]
    entity = first.content["value"]["entity"]
    rule(entity, (), first)
    second = units_of(a_cycle())[0]
    predicted = rule(entity, (first,), second)

    for key in ("entity", "context"):
        assert predicted.content["value"][key] == second.content["value"][key]
    assert predicted.ref_frame == second.ref_frame


def test_the_rule_reports_its_reading_of_the_situation_upward():
    mind = create_mind()
    reported: list[dict[str, float]] = []
    rule = predict_rule(mind)
    unit = units_of(a_cycle())[0]
    entity = unit.content["value"]["entity"]

    rule(entity, (), unit, lambda params, weight=1.0: reported.append(dict(params)))
    rule(entity, (unit,), units_of(a_cycle())[0],
         lambda params, weight=1.0: reported.append(dict(params)))

    # The rule reports twice per call — its reading of novelty, then its
    # per-action readings — so pick out the novelty reports.
    novelty = [r for r in reported if CONTEXT_NOVELTY in r]
    assert novelty[0][CONTEXT_NOVELTY] == 1.0, "a situation met for the first time"
    assert novelty[0][CONTEXTS_KNOWN] == 0.0
    assert novelty[1][CONTEXT_NOVELTY] == 0.0, "and now familiar"
    assert novelty[1][CONTEXTS_KNOWN] == 1.0
    assert any(k.startswith("progress:") for r in reported for k in r), "and progress"


def test_a_rule_with_nothing_to_report_still_works():
    rule = predict_rule(create_mind())
    unit = units_of(a_cycle())[0]
    assert rule(unit.content["value"]["entity"], (), unit) is unit
    assert NO_CONTEXT == ""


# ── learning progress, and the noisy-TV failure it exists to avoid ──


def test_a_situation_not_yet_used_enough_counts_as_still_being_learned():
    mind = create_mind()
    assert mind.progress("action:1") == 1.0


def test_noise_that_cannot_be_learned_shows_no_progress():
    """MEASURED before this existed: curiosity took one action 103 times in 120
    because its outcome never became predictable. Following progress rather than
    ignorance, steady unpredictability reads as zero and curiosity moves on."""
    mind = create_mind()
    for t in range(2 * PROGRESS_WINDOW):
        # Half right, half wrong, every use, for ever: irreducible.
        mind.score("action:1", "a", "a", t)
        mind.score("action:1", "a", "b", t)
    assert mind.progress("action:1") == 0.0


def test_something_being_learned_shows_progress():
    mind = create_mind()
    for t in range(PROGRESS_WINDOW):
        mind.score("action:1", "a", "b", t)  # wrong at first
    for t in range(PROGRESS_WINDOW, 2 * PROGRESS_WINDOW):
        mind.score("action:1", "a", "a", t)  # then right
    assert mind.progress("action:1") == 1.0


def test_a_world_that_changes_under_an_action_is_worth_attention_again():
    """Absolute progress: accuracy that starts falling counts too."""
    mind = create_mind()
    for t in range(PROGRESS_WINDOW):
        mind.score("action:1", "a", "a", t)
    for t in range(PROGRESS_WINDOW, 2 * PROGRESS_WINDOW):
        mind.score("action:1", "a", "b", t)
    assert mind.progress("action:1") == 1.0
