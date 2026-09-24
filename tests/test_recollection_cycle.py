"""A recalled scar moves on the datum its record names, once. Ported from dil-core dc7a9a7.

Since the region's return holds the scar, a recalled scar is that return, not
the cycle datum. It moves `scar → running` while it is a scar, `[data]`
following the line; recalled again once it is back in use, it does not move.
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
from dil.loop.recollection import create_log_recollection
from dil.loop.types import Signal
from dil.store.data_store import create_data_store, to_running, to_scar
from dil.store.decisions import CONTEXT_ANCHOR_DEPTH
from dil.store.event_log import create_event_log
from dil.store.resist_event import ContextAnchor, ResistEvent, record_scar
from dil.store.tagging_gate import HostDatum, admit_host_data

SEEDED_AT = 7


def seen(where: str, outcome: str) -> Signal:
    return Signal(source_id="ch", raw_payload={"entity": "weather", "value": {"where": where, "outcome": outcome}}, t=1)


def where_of(unit) -> str:
    return str(unit.content.get("value", {}).get("value", {}).get("where", ""))


def test_a_recalled_scar_held_by_a_return_moves_on_that_datum_once():
    data, events = create_data_store(), create_event_log()
    # A store as a past run left it: the scar in [event], the scarred return in [data].
    held = to_scar(to_running(admit_host_data(HostDatum(
        payload="x", admitting_layer=1, open={"domain": "region", "source": "ch", "format": "object"},
    ), 1), SEEDED_AT), True)
    data.put("signal-7-0", held)
    events.append(record_scar(
        held,
        ResistEvent(
            source_id="weather", expected=None,
            received={"infoType": "raw", "channel": "ch",
                      "value": {"entity": "weather", "value": {"where": "hall", "outcome": "rain"}}},
            mismatch_kind="value-mismatch", t=1,
        ),
        ContextAnchor(cycle=SEEDED_AT, field_state={}, depth=CONTEXT_ANCHOR_DEPTH),
        datum_id="signal-7-0",
    ))
    recollection = create_log_recollection(events, key=where_of)

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
        recalled = recollection.recall(entity_id, observed)
        return recalled if recalled is not None else observed

    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3(), t4=create_t4(),
                      t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), recollection=recollection,
    )
    # Cycle 0 recalls the seeded scar, and the region contradicts it: a new scar
    # on this cycle's return. Cycles 1 and 2 recall that newer one, which moves
    # the first time only.
    for _ in range(3):
        cycle.run(HostCycleInput(signals=(seen("hall", "sun"),)))

    moves = [
        (r.datum_id, r.cycle_mark) for r in events.all()
        if getattr(r, "activity_kind", None) == "provenance" and r.from_ == "scar" and r.to == "running"
    ]
    assert moves == [("signal-7-0", 0), ("signal-0-0", 1)]
    assert data.get("signal-7-0").fixed.provenance == "running", "[data] follows the log"
    assert data.get("signal-0-0").fixed.provenance == "running"
