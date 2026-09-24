"""The directive: recalled from the store, then read by the mind.

Until 2026-09-23 the signs the mind put on the region's answers were written in
its code. They now come from the directive, which is host data admitted as
`prior` and recalled by T3 when the region's status first arrives. These pin
both halves: the mind reads nothing into an answer without a directive, and the
directive reaches the mind by the protocol's road, not a side door.
"""

from __future__ import annotations

from arc3.mind import create_mind, mind_rule, region_valence
from arc3.observe import FRAME_CHANNEL, REGION_ENTITY, STATUS_CHANNEL, admit, transducers
from arc3.prior import DIRECTIVE, RULES
from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import STORE_CHANNEL, create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.tagging_gate import HostDatum, admit_host_data

WON = {"stateTo": "WIN", "levelsDelta": 0}
LOST = {"stateTo": "GAME_OVER", "levelsDelta": 0}
LEVEL = {"stateTo": "NOT_FINISHED", "levelsDelta": 1}
NOTHING = {"stateTo": "NOT_FINISHED", "levelsDelta": 0}


# ── the mind reads against the directive, and only against it ──


def test_with_no_directive_nothing_is_better_or_worse():
    """A character with no problem to solve has nothing to prefer."""
    for status in (WON, LOST, LEVEL, NOTHING):
        assert region_valence(status, None) == 0.0


def test_the_directive_says_which_answers_are_toward_and_which_away():
    d = DIRECTIVE.payload
    assert region_valence(WON, d) == 1.0
    assert region_valence(LEVEL, d) == 1.0
    assert region_valence(LOST, d) == -1.0
    assert region_valence(NOTHING, d) == 0.0


def test_the_mind_takes_up_a_recalled_directive_and_nothing_else():
    mind = create_mind()
    mind.take_return({"entity": "prior:world", "payload": {"says": []}, "open": {}}, None)
    assert mind.directive() is None
    mind.take_return({"entity": DIRECTIVE.id, "payload": DIRECTIVE.payload, "open": {}}, None)
    assert mind.directive() == DIRECTIVE.payload


def test_a_recalled_datum_is_read_not_predicted_as_an_other():
    mind = create_mind()
    rule = mind_rule(mind)
    from dil.loop.types import InfoUnit, RefFrame

    unit = InfoUnit(
        content={"infoType": "raw", "channel": STORE_CHANNEL,
                 "value": {"entity": DIRECTIVE.id, "payload": DIRECTIVE.payload, "open": {}}},
        ref_frame=RefFrame(bound_layer=3, ref=f"channel:{STORE_CHANNEL}"),
        t=1,
    )
    assert rule(DIRECTIVE.id, (), unit) is unit
    assert mind.directive() == DIRECTIVE.payload
    assert mind.frame_calls == 0 and mind.valence("action:1") is None, "it did not become an Other the mind predicts"


# ── end to end: status arrives, the directive is recalled, the mind reads it ──


def _status(t: int, status: dict) -> Signal:
    return Signal(
        source_id=STATUS_CHANNEL,
        raw_payload={"entity": REGION_ENTITY, "status": status, "context": "action:1"},
        t=t,
    )


def _store_with_rules():
    data = create_data_store()
    for item in RULES:
        data.put(item.id, admit_host_data(
            HostDatum(payload=item.payload, admitting_layer=item.admitting_layer,
                      open=item.open), 1))
    return data


def test_the_first_status_report_brings_the_directive_to_mind():
    mind = create_mind()
    data, events = _store_with_rules(), create_event_log()
    layers = Layers(
        t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
        t5=create_t5(predict=mind_rule(mind)), t6=create_t6(), t7=create_t7(),
        t8=create_t8(),
    )
    cycle = create_cycle(layers=layers, glob=create_glob_mod({}, 0), data=data,
                         events=events, initial_emission=Emission(action=None))

    cycle.run(HostCycleInput(signals=(_status(1, NOTHING),)))
    assert mind.directive() is None, "asked for this cycle, not yet arrived"

    cycle.run(HostCycleInput(signals=(_status(2, NOTHING),)))
    assert mind.directive() == DIRECTIVE.payload
    # A status report is about the region's status, its levels, and what may be
    # done next: what is about those came to mind; what is about seeing did not,
    # because nothing has been seen yet.
    def provenance(key: str) -> str:
        return data.get(f"prior:{key}").fixed.provenance

    assert {k: provenance(k) for k in ("directive", "levels", "cost", "actions",
                                       "seeing", "world")} == {
        "directive": "running", "levels": "running", "cost": "running",
        "actions": "running", "seeing": "prior", "world": "prior",
    }

    # From here the region's answers are read against it.
    cycle.run(HostCycleInput(signals=(_status(3, LEVEL),)))
    assert mind.valence("action:1") is not None and mind.valence("action:1") > 0

    # The first frame seen brings what the character was told about seeing. What
    # it was told about the world's things has no arrival that is about things
    # now — the host carries the frame, not things found in it — so it stays
    # where it was: not asked for is not recalled.
    grid = [[0, 0], [0, 0]]
    seen = Signal(source_id=FRAME_CHANNEL, raw_payload={
        "entity": "frame", "before": [grid], "grids": [grid],
        "move": {"kind": "move", "actionId": 1, "x": None, "y": None}, "context": "action:1"}, t=4)
    cycle.run(HostCycleInput(signals=(_status(4, NOTHING), seen)))
    cycle.run(HostCycleInput(signals=(_status(5, NOTHING),)))
    assert provenance("seeing") == "running"
    assert provenance("world") == "prior"
