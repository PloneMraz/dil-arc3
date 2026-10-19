"""INV-5's accumulation, measured from the trace: a pass only for a ramp recurrence drives.

Ported from dil-core 817bf75 (`conformance.test.ts`). Until 2026-10-19 the measure
passed an entity whose confidence held a value below 1 and one at 1, in any order
and at any recurrence. Each series below is one entity's (recurrence, confidence)
readings, a cycle apart.
"""

from dil.conformance.checker import check_conformance
from dil.store.event_log import create_event_log
from dil.store.resist_event import record_crystallization, record_expectation


def accumulation_of(*series: tuple[str, list[tuple[float, float]]]) -> str:
    events = create_event_log()
    t = 0
    for entity, rows in series:
        for cycle, (recurrence, confidence) in enumerate(rows):
            t += 1
            events.append(record_expectation(f"cycle-{cycle}", cycle, entity, entity, confidence, recurrence, 0.0, t))
    events.append(record_crystallization("cycle-0", 0, t + 1))
    c4 = next(r for r in check_conformance(events).results if r.id == "4")
    return next(c for c in c4.claims if "accumulation observable" in c.claim).verdict


def test_confidence_rising_while_recurrence_stands_still_fails():
    assert accumulation_of(("weather", [(1, 0.5), (1, 1.0)])) == "fail"
    assert accumulation_of(("weather", [(3, 0.2), (3, 0.6), (3, 1.0)])) == "fail"


def test_confidence_falling_from_saturation_as_recurrence_climbs_fails():
    assert accumulation_of(("weather", [(1, 1.0), (2, 0.5)])) == "fail"


def test_recurrence_reset_fails():
    assert accumulation_of(("weather", [(0, 0.0), (1, 0.5), (2, 1.0), (0, 0.0)])) == "fail"


def test_a_genuine_ramp_passes_and_a_series_saturated_from_its_start_stays_partial():
    assert accumulation_of(("weather", [(0, 0.0), (1, 1 / 3), (2, 2 / 3), (3, 1.0), (4, 1.0)])) == "pass"
    assert accumulation_of(("weather", [(3, 1.0), (4, 1.0), (5, 1.0)])) == "partial"


def test_entities_of_different_histories():
    ramp = ("frame", [(0, 0.0), (1, 0.5), (2, 1.0)])
    thin = ("status", [(0, 0.0), (1, 0.5)])
    faked = ("remark", [(2, 0.4), (2, 1.0)])
    assert accumulation_of(ramp, thin) == "pass", "one entity's ramp, another not yet saturated"
    assert accumulation_of(thin) == "partial"
    assert accumulation_of(ramp, faked) == "fail", "a genuine ramp does not cover another entity's fault"


def test_recurrence_flat_with_confidence_flat_is_partial_not_a_pass():
    assert accumulation_of(("weather", [(0, 0.0), (0, 0.0), (0, 0.0)])) == "partial"
