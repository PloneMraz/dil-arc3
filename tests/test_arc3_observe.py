"""The bridge, and one finding it exposed.

The last test here is not a unit test. It pins a measured consequence of the
affordance reading in place, so it cannot quietly stop being true.
"""

from __future__ import annotations

import json

from arc3 import (
    GAME_CHANNEL,
    SELF_MOVE_CHANGE,
    Move,
    affordance_key,
    diff,
    game_transducer,
    observe,
)
from arc3.observe import effect_value
from dil.loop.layers.t3 import T3Input, create_t3
from dil.loop.layers.t4 import STRANGER, T4Input, create_t4
from dil.loop.types import ModField
from tests.test_arc3_effect import framed, marker


def noop_emit(*a, **kw):  # the layers here never emit
    raise AssertionError("no emission expected")


def a_transition(move: Move):
    prev, now = framed(marker(30, 30)), framed(marker(25, 30))
    return observe(prev, move, now, diff(prev, now), t=7)


# ── the affordance, and the collapse that is declared ──


def test_one_affordance_per_action_id():
    assert affordance_key(Move(1)) == "action:1"


def test_action6_coordinates_collapse_into_one_affordance():
    """Declared, not accidental: 4096 entities that each recur once would let
    nothing accrue. The cost is that action:6's expectation cannot stabilise."""
    assert affordance_key(Move(6, 1, 1)) == affordance_key(Move(6, 50, 20))


# ── what goes inward ──


def test_the_cycle_gets_one_signal_on_the_game_channel():
    host = a_transition(Move(1))
    assert len(host.signals) == 1
    assert host.signals[0].source_id == GAME_CHANNEL
    assert host.signals[0].t == 7


def test_the_payload_carries_the_effect_not_the_frame():
    """The unit is the affordance, so the grid must not be what travels."""
    payload = a_transition(Move(1)).signals[0].raw_payload
    assert set(payload) == {"entity", "effect", "game", "affords"}
    assert "grids" not in payload


def test_the_payload_is_json_shaped_so_t5_can_compare_it():
    """T5 compares expectations with json.dumps(sort_keys=True). A value that
    only serialises through default=str would make identical effects differ."""
    payload = a_transition(Move(1)).signals[0].raw_payload
    assert json.loads(json.dumps(payload)) == payload


def test_the_same_effect_twice_gives_equal_payloads():
    a = a_transition(Move(1)).signals[0].raw_payload
    b = a_transition(Move(1)).signals[0].raw_payload
    assert a == b


# ── the loop's own seam binds it, with no custom resolver ──


def test_t4s_default_resolver_binds_the_affordance():
    """The reason no ContextResolver had to be written: T3's transducer output
    already carries the `entity` key T4's declared default reads."""
    host = a_transition(Move(3))
    t3 = create_t3({GAME_CHANNEL: game_transducer})
    t4 = create_t4()
    units = t3.process(T3Input(signals=host.signals), ModField(), noop_emit).units
    bound = t4.process(T4Input(units=units), ModField(), noop_emit).bound
    assert [b.entity_id for b in bound] == ["action:3"]
    assert bound[0].entity_id != STRANGER


# ── the agency line ──


def test_the_move_is_reported_as_the_one_self_written_change():
    host = a_transition(Move(2))
    ids = [c.id for c in host.changes]
    assert ids == [SELF_MOVE_CHANGE, "action:2"]
    assert host.changes[0].value == {"actionId": 2, "x": None, "y": None}


def test_the_frame_change_is_reported_under_the_affordance_id():
    """T6 reads change.id as the entity id, so the affordance accrues
    independence evidence as an Other."""
    host = a_transition(Move(2))
    assert host.changes[1].value == effect_value(
        diff(framed(marker(30, 30)), framed(marker(25, 30)))
    )


# ── the measured consequence ──


def test_unexercised_affordances_register_as_absences():
    """MEASURED, and reported to Plone rather than patched around.

    T7 registers an expected entity that did not return as a negative PredErr.
    An affordance is not a source that returns on its own — it returns only when
    the agent uses it — and the agent uses one per cycle. So once N affordances
    have been seen, N-1 absences are recorded every cycle thereafter.

    On 159 real ls20 cycles this was 444 of 481 scars. On vc33, which affords a
    single action, it was 0 of 91 — and there the scar rate equalled the
    persistence miss rate exactly, which is what shows the mechanism itself is
    sound and the MAPPING is what produces the flood.
    """
    from dil.loop.layers.t5 import T5Input, create_t5
    from dil.loop.layers.t7 import ExpectedEntity, T7Input, create_t7

    t3 = create_t3({GAME_CHANNEL: game_transducer})
    t4 = create_t4()
    t5 = create_t5()
    t7 = create_t7()

    absences_seen = []
    for move in (Move(1), Move(2), Move(1), Move(2)):
        host = a_transition(move)
        units = t3.process(T3Input(signals=host.signals), ModField(), noop_emit).units
        bound = t4.process(T4Input(units=units), ModField(), noop_emit).bound
        t5out = t5.process(T5Input(bound=bound), ModField(), noop_emit)
        t7out = t7.process(
            T7Input(
                expectations=tuple(
                    ExpectedEntity(entity_id=r.entity_id, predicted=r.expectation.predicted)
                    for r in t5out.results
                ),
                observed=frozenset(r.entity_id for r in t5out.results),
            ),
            ModField(),
            noop_emit,
        )
        absences_seen.append(tuple(a.entity_id for a in t7out.absences))

    # The first cycle knows only action:1, so nothing is missing. From the
    # second on, the affordance not used this cycle is registered absent.
    assert absences_seen[0] == ()
    assert absences_seen[1] == ("action:1",)
    assert absences_seen[2] == ("action:2",)
    assert absences_seen[3] == ("action:1",)
