"""When the cycle datum itself goes to `scar` (§9). Ported from dil-core 6c74f0c.

Since the region's return is a datum, the return that collided holds the scar.
The cycle datum collides only when what it carries does: an outcome it cast
(`projected → scar`), or a collision with no return of its own to hold the
scar, such as an absence, for which it stands. A cast that did not collide
returns to use (`projected → running`); with no cast the cycle datum stays
`running` when a return collides.
"""

from __future__ import annotations

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
from dil.store.decisions import FIT_FLOOR_PARAM
from dil.store.event_log import create_event_log
from dil.store.resist_event import EventRecord


def sig(entity: str, value: object) -> Signal:
    return Signal(source_id="ch", raw_payload={"entity": entity, "value": value}, t=1)


def loop(fit_floor: float):
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(), t4=create_t4(),
            t5=create_t5(), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0, FIT_FLOOR_PARAM: fit_floor}, 0),
        data=data, events=events, initial_emission=Emission(action="boot"),
    )
    return cycle, data, events


def run(cycle, *signals: Signal):
    return cycle.run(HostCycleInput(signals=tuple(signals)))


def cycle_moves(events, n: int):
    return [
        f"{r.from_}→{r.to}" for r in events.all()
        if getattr(r, "activity_kind", None) == "provenance" and r.datum_id == f"cycle-{n}"
    ]


def scars_at(events, n: int):
    return [r for r in events.all() if isinstance(r, EventRecord) and r.anchor.cycle == n]


def test_a_cast_outcome_that_collides_takes_the_cycle_datum_to_scar():
    cycle, data, events = loop(0.0)
    run(cycle, sig("a", 1))
    run(cycle, sig("a", 1))
    run(cycle, sig("a", 2))  # `a` was cast, and it changed
    assert cycle_moves(events, 2) == ["running→simulated", "simulated→projected", "projected→scar"]
    assert data.get("cycle-2").fixed.provenance == "scar"
    assert scars_at(events, 2)[0].datum_id == "signal-2-0", "the return holds the record"


def test_a_cast_that_did_not_collide_returns_to_use_though_another_return_collided():
    cycle, data, events = loop(0.5)
    for _ in range(3):
        run(cycle, sig("a", 1))
    run(cycle, sig("a", 1), sig("b", 1))
    run(cycle, sig("a", 1), sig("b", 2))
    assert cycle_moves(events, 4) == ["running→simulated", "simulated→projected", "projected→running"]
    assert data.get("cycle-4").fixed.provenance == "running"
    assert data.get("signal-4-1").fixed.provenance == "scar", "`b`'s return holds the scar"
    assert len(scars_at(events, 4)) == 1


def test_with_no_cast_a_return_that_collides_leaves_the_cycle_datum_running():
    cycle, data, events = loop(2.0)
    run(cycle, sig("a", 1))
    run(cycle, sig("a", 2))
    assert cycle_moves(events, 1) == []
    assert data.get("cycle-1").fixed.provenance == "running"
    assert data.get("signal-1-0").fixed.provenance == "scar"
    assert scars_at(events, 1)[0].datum_id == "signal-1-0"


def test_an_absence_has_no_return_so_the_cycle_datum_stands_for_it():
    cycle, data, events = loop(2.0)
    run(cycle, sig("a", 1))
    result = run(cycle)  # `a` falls silent
    assert result.absences >= 1
    assert cycle_moves(events, 1) == ["running→scar"]
    assert data.get("cycle-1").fixed.provenance == "scar"
    scar = scars_at(events, 1)[0]
    assert scar.event.mismatch_kind == "absence"
    assert scar.datum_id is None


def test_nothing_collides_a_cast_returns_to_use_and_without_one_nothing_moves():
    cycle, _, events = loop(0.0)
    run(cycle, sig("a", 1))
    run(cycle, sig("a", 1))
    assert cycle_moves(events, 1) == ["running→simulated", "simulated→projected", "projected→running"]
    bare, _, bare_events = loop(2.0)
    run(bare, sig("a", 1))
    run(bare, sig("a", 1))
    assert cycle_moves(bare_events, 1) == []
