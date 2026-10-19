"""The field reaches every layer (INV-7): "each layer receives it as background…
it modulates how each layer interprets input" — "same data + different field →
different meaning". Each test gives one layer the same input under two fields
and shows the reading differ, and shows NEUTRAL reads as the reference did.
Which axis each layer reads is declared in decisions.FIELD_WIRING. Ported from
dil-core 1e0a22a (field.test.ts, contribute.test.ts).
"""

from __future__ import annotations

import re

import pytest

from dil.loop.appraisal import AppraisalInput, appraise
from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.field import (
    AXES, EXPLORATION, NEUTRAL, TRUST, axis, falling, rising, shifted_count, votes,
)
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layer import run_layer
from dil.loop.layers.t1 import create_t1, grace_of
from dil.loop.layers.t2 import Emission, ObservedChange, T2Input, create_t2
from dil.loop.layers.t3 import T3Input, create_t3
from dil.loop.layers.t4 import STRANGER, BoundInfo, T4Input, create_t4
from dil.loop.layers.t5 import T5Input, T5Result, create_t5
from dil.loop.layers.t6 import IndependenceEvidence, T6Input, create_t6
from dil.loop.layers.t7 import ExpectedEntity, T7Input, create_t7
from dil.loop.layers.t8 import ObservedInteraction, T8Input, create_t8
from dil.loop.types import Expectation, InfoUnit, ModField, OtherModel, PredErr, RefFrame, Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.tagging_gate import HostDatum, admit_host_data

EMPTY = ModField(params={}, t=0)


def field(**params: float) -> ModField:
    return ModField(params=dict(params), t=0)


def datum():
    return admit_host_data(HostDatum(payload=1, admitting_layer=1, open={"domain": "d", "a": "1", "b": "2"}), 0)


def unit(entity: str, value: object) -> InfoUnit:
    return InfoUnit(
        content={"infoType": "raw", "channel": "ch", "value": {"entity": entity, "value": value}},
        ref_frame=RefFrame(bound_layer=3, ref="channel:ch"),
        t=1,
    )


def sig(entity: str, value: object, t: int = 1) -> Signal:
    return Signal(source_id="ch", t=t, raw_payload={"entity": entity, "value": value})


def loop(seed: dict[str, float] | None = None):
    glob = create_glob_mod(seed or {}, 0)
    layers = Layers(
        t1=create_t1(), t2=create_t2(), t3=create_t3(), t4=create_t4(),
        t5=create_t5(), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    cycle = create_cycle(
        layers=layers, glob=glob, data=create_data_store(), events=create_event_log(),
        initial_emission=Emission(action="boot"),
    )
    return cycle, glob


# ── the reading law ──

def test_an_axis_the_field_does_not_carry_reads_neutral_and_neutral_shifts_nothing():
    assert axis(EMPTY, TRUST) == NEUTRAL
    assert rising(NEUTRAL) == 1 and falling(NEUTRAL) == 1
    assert shifted_count(8, rising(NEUTRAL)) == 8


def test_the_field_modulates_and_never_annuls():
    # DIL-en-v7 §2: a field that determined a layer's reading would be a halted loop.
    for v in (0.0, 1.0):
        assert rising(v) >= 0.5 and falling(v) >= 0.5


def test_an_axis_is_read_within_0_and_1():
    assert axis(field(trust=7), TRUST) == 1
    assert axis(field(trust=-1), TRUST) == 0


def test_a_vote_outside_0_and_1_is_refused_not_clamped():
    with pytest.raises(ValueError):
        votes({TRUST: 1.5})


def test_rounding_is_half_up_as_in_dil_core():
    assert shifted_count(1, 1.5) == 2 and shifted_count(3, 1.5) == 5 and shifted_count(3, 0.5) == 2


# ── each layer, same data, different field ──

def test_t1_under_trust_a_short_silence_does_not_unconfirm_the_environment():
    def read(f: ModField) -> bool:
        t1 = create_t1()
        run_layer(t1, (sig("x", 1),), f, datum())
        return run_layer(t1, (), f, datum()).output.content["present"]

    assert read(EMPTY) is False, "NEUTRAL: confirmed only when the region speaks (reference)"
    assert read(field(trust=1)) is True
    assert grace_of(1) == 2 and grace_of(NEUTRAL) == 0


def test_t2_under_trust_an_older_emission_is_still_matched_as_the_cause():
    def read(f: ModField) -> str:
        t2 = create_t2(window=1, stability_threshold=1)
        env = run_layer(create_t1(), (), EMPTY, datum()).output
        run_layer(t2, T2Input(env=env, emitted=Emission(action="X")), f, datum())
        out = run_layer(
            t2, T2Input(env=env, emitted=Emission(action="Y"), changes=(ObservedChange(id="c", value="X"),)), f, datum()
        )
        return out.output.tagged[0].agency

    assert read(EMPTY) == "ENV_PUSHED", "NEUTRAL: only the last emission is in reach"
    assert read(field(trust=1)) == "SELF_WRITTEN"


def test_t3_leaning_to_explore_asks_a_cue_again():
    described = {"ch": lambda s: ("raw", s.raw_payload, {"kind": "k"})}

    def asks(f: ModField) -> int:
        t3 = create_t3(described)
        return sum(
            len(run_layer(t3, T3Input(signals=(sig("x", i, t=i),)), f, datum()).emissions) for i in range(10)
        )

    assert asks(EMPTY) == 1, "NEUTRAL: asked once (reference)"
    assert asks(field(exploration=1)) == 2, "fully exploring: asked again after half the span"


def test_t4_with_little_trust_a_named_entity_takes_more_sightings():
    def first(f: ModField) -> str:
        return run_layer(create_t4(), T4Input(units=(unit("a", 1),)), f, datum()).output.bound[0].entity_id

    assert first(EMPTY) == "a"
    assert first(field(trust=0)) == STRANGER


def test_t5_exploring_keeps_a_shorter_baseline_and_confidence_is_untouched():
    def read(f: ModField) -> Expectation:
        t5 = create_t5(baseline_window=4)
        last = None
        for i in range(6):
            last = run_layer(t5, T5Input(bound=(BoundInfo(unit=unit("a", i), entity_id="a"),)), f, datum()).output.results[0]
        return last.expectation

    assert len(read(EMPTY).built_from) == 4
    assert len(read(field(exploration=1)).built_from) == 2
    assert read(field(exploration=1)).confidence == read(EMPTY).confidence, "never into confidence (§13.4)"


def test_t5_hands_the_field_to_a_rule_that_takes_it():
    seen: list[ModField | None] = []

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, test=None, field=None):
        seen.append(field)
        return observed

    f = field(alertness=0.9)
    run_layer(create_t5(predict=rule), T5Input(bound=(BoundInfo(unit=unit("a", 1), entity_id="a"),)), f, datum())
    assert seen == [f]


def test_t5_a_rule_written_before_the_field_is_still_called_as_it_was():
    def old(entity_id, window, observed, contribute=None, ask=None, write=None, test=None):
        return observed

    run_layer(create_t5(predict=old), T5Input(bound=(BoundInfo(unit=unit("a", 1), entity_id="a"),)), EMPTY, datum())


def _t5_result(delta: float) -> T5Result:
    predicted = unit("a", 0)
    return T5Result(
        entity_id="a",
        expectation=Expectation(predicted=predicted, confidence=0, recurrence=0),
        pred_err=PredErr(observed=unit("a", 1), predicted=predicted, delta=delta, signed="+"),
    )


def test_t6_under_trust_one_resistance_counts_for_more():
    def read(f: ModField) -> float:
        out = run_layer(create_t6(), T6Input(results=(_t5_result(1.0),)), f, datum()).output.others[0]
        return out.independence_evidence.resistances

    assert read(EMPTY) == 1
    assert read(field(trust=1)) == 1.5
    assert read(field(trust=0)) == 0.5, "less, never nothing"


def test_t7_the_more_alert_the_longer_an_entity_stays_demanded_back():
    def read(f: ModField) -> int:
        t7 = create_t7(attention_span=2)
        e = ExpectedEntity(entity_id="a", predicted=unit("a", 1))
        run_layer(t7, T7Input(expectations=(e,), observed=frozenset({"a"})), f, datum())
        run_layer(t7, T7Input(), f, datum())
        run_layer(t7, T7Input(), f, datum())
        return len(run_layer(t7, T7Input(), f, datum()).output.absences)

    assert read(EMPTY) == 0
    assert read(field(alertness=1)) == 1


def _other(entity: str, resistances: float, pushed: float) -> OtherModel:
    return OtherModel(entity_id=entity, independence_evidence=IndependenceEvidence(resistances=resistances, env_pushed=pushed))


def test_t8_exploring_others_equal_in_resistance_are_told_apart():
    def rank(f: ModField):
        return run_layer(create_t8(), T8Input(others=(_other("a", 1, 0), _other("b", 1, 2))), f, datum()).output.rel_values

    assert rank(EMPTY)[0].comparison_basis == "resistance"
    deep = rank(field(exploration=1))
    assert deep[0].comparison_basis == "resistance+envPushed" and deep[0].entity_id == "b"


def test_t8_reads_weighed_evidence_as_a_number_not_only_an_integer():
    ranked = run_layer(create_t8(), T8Input(others=(_other("a", 0.5, 0), _other("b", 1.5, 0))), EMPTY, datum())
    assert ranked.output.rel_values[0].entity_id == "b"


def test_t8_closes_back_through_the_dispositions_below_it_read():
    run = run_layer(
        create_t8(),
        T8Input(
            others=(_other("a", 3, 0), _other("b", 1, 0)),
            interactions=(ObservedInteraction(a_id="a", b_id="b", observed_interaction="met"),),
        ),
        EMPTY,
        datum(),
    )
    v = run.contributions[0].params
    assert v[TRUST] == 0.25 and v[EXPLORATION] == 0.5


def test_appraisal_the_same_resistance_weighs_more_under_alertness():
    pred_errs = (PredErr(observed=None, predicted=unit("a", 1), delta=1.0, signed="-"),)

    def valence(f: ModField) -> float:
        return appraise(AppraisalInput(info_ref="c", pred_errs=pred_errs, field=f, edited_state="state")).valence

    assert valence(EMPTY) == -1
    assert valence(field(alertness=1)) == -1.5
    assert valence(field(alertness=0)) == -0.5


def test_forward_building_exploring_builds_more_situations():
    def built(exploration: float) -> int:
        cycle, glob = loop()
        signals = tuple(sig(e, 1) for e in "abcde")
        for _ in range(3):
            cycle.run(HostCycleInput(signals=signals))
        glob.restore({EXPLORATION: exploration}, glob.cycle())
        ref = cycle.run(HostCycleInput(signals=signals)).appraisal.info_ref
        m = re.search(r"\+(\d+)proj$", ref)
        return int(m.group(1)) if m else 0

    assert built(NEUTRAL) == 3
    assert built(1.0) == 5
    assert built(0.0) == 2


# ── through the driver, into the field ──

def test_the_layers_votes_reach_the_field_and_only_at_n_plus_1():
    cycle, glob = loop({"appraisalGain": 1.0})
    assert dict(glob.current().params) == {"appraisalGain": 1.0}
    cycle.run(HostCycleInput(signals=(sig("a", 1),)))
    p = glob.current().params
    assert all(k in p for k in AXES)
    assert p[TRUST] == 1 and p[EXPLORATION] == 1


def test_the_field_carries_dispositions_never_what_was_read():
    cycle, glob = loop({"appraisalGain": 1.0})
    cycle.run(HostCycleInput(signals=(sig("a", 1),)))
    cycle.run(HostCycleInput(signals=(sig("a", 2), sig("b", 1))))
    cycle.run(HostCycleInput())
    assert set(glob.current().params) <= {*AXES, "appraisalGain"}


def test_every_axis_stays_within_0_and_1_however_the_loop_runs():
    cycle, glob = loop()
    for i in range(12):
        signals = () if i % 3 == 2 else (sig(f"e{i % 4}", i), sig("x", i % 2))
        cycle.run(HostCycleInput(signals=signals))
        for name in AXES:
            v = glob.current().params.get(name)
            assert v is None or 0 <= v <= 1


def test_a_layer_that_saw_nothing_on_an_axis_leaves_it_as_it_was():
    cycle, glob = loop()
    cycle.run(HostCycleInput(signals=(sig("a", 1),)))
    before = glob.current().params[EXPLORATION]
    cycle.run(HostCycleInput())
    assert glob.current().params[EXPLORATION] == before
    assert glob.current().params[TRUST] == 0, "T1 alone voted: the region said nothing"


def test_the_driver_adds_nothing_of_its_own():
    cycle, glob = loop()
    cycle.run(HostCycleInput(signals=(sig("a", 1),)))
    assert "resistance" not in glob.current().params


def test_alertness_counts_what_the_host_says_can_alert_the_loop():
    # DEVIATION 8: an echo of the agent's own write never mismatches; counted, it
    # holds the vote down however often the world collides.
    from arc3.decisions import from_the_world
    world = InfoUnit(content={"channel": "arc3-frame", "value": 1}, ref_frame=None, t=0)
    echo = InfoUnit(content={"channel": "store", "value": 1}, ref_frame=None, t=0)
    assert from_the_world(world) and not from_the_world(echo)


def test_with_a_carry_the_field_before_blends_in_with_the_votes():
    # DEVIATION 9 (2026-10-18): with carry, an axis voted on keeps carry of the
    # field before; with none, dil-core's blend (the cycle's votes alone).
    from dil.loop.glob_mod import GlobModError, create_glob_mod
    plain, carried = create_glob_mod({TRUST: 0.2}), create_glob_mod({TRUST: 0.2}, carry=0.75)
    for glob in (plain, carried):
        glob.contribute(1, {TRUST: 1.0}, 1.0)
        glob.advance(1)
    assert plain.current().params[TRUST] == 1.0
    assert abs(carried.current().params[TRUST] - (0.75 * 0.2 + 0.25 * 1.0)) < 1e-12
    carried.advance(2)                       # no vote: the axis carries over unchanged
    assert abs(carried.current().params[TRUST] - 0.4) < 1e-12
    with pytest.raises(GlobModError):
        create_glob_mod(carry=1.0)
