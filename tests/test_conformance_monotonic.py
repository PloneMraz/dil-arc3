"""§13.4's monotonicity reads a scar by the cycle it happened in, not its datum's stamp.

Ported from dil-core cac2b40 (`conformance.test.ts`). Until 2026-10-21 the claim read
a scar's datum stamp — the cycle the datum ENTERED — as the cycle the record happened
in; since v0.3.5 a datum an expectation was (held_by) is scarred cycles after it
entered, so every store of this host read "not monotonic … accrual is suspect".
"""

from dil.conformance.checker import check_conformance
from dil.store.event_log import create_event_log
from dil.store.resist_event import ContextAnchor, ResistEvent, record_crystallization, record_scar
from dil.store.tags import FixedTags, TaggedDatum


def monotonicity_of(*scars: tuple[int, int]) -> str:
    """Each scar as (the cycle its datum was stamped, the cycle it was scarred)."""
    events = create_event_log()
    t = 1
    events.append(record_crystallization("cycle-0", 0, t))
    for stamped, scarred_at in scars:
        t += 1
        datum = TaggedDatum(payload={}, fixed=FixedTags(timestamp=t, cycle_mark=stamped, provenance="scar", floor_tag=5),
                            open={"domain": "mind", "kind": "hypothesis", "source": "mind"})
        event = ResistEvent(source_id="ch", expected=1, received=2, mismatch_kind="value-mismatch", t=t)
        events.append(record_scar(datum, event, ContextAnchor(cycle=scarred_at), f"d-{t}"))
    c4 = next(r for r in check_conformance(events).results if r.id == "4")
    return next(c for c in c4.claims if "non-decreasing" in c.claim).verdict


def test_a_held_by_scar_of_an_older_datum_is_no_step_back():
    # Cycle 9's return, then a hypothesis written at cycle 4 scarred at cycle 10.
    assert monotonicity_of((9, 9), (4, 10)) == "pass"


def test_cycles_that_go_back_stay_partial():
    assert monotonicity_of((9, 9), (3, 3)) == "partial"


def test_a_scar_of_a_datum_stamped_after_the_collision_stays_partial():
    assert monotonicity_of((12, 10)) == "partial"
