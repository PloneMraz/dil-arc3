"""The mind reads its history (Plone, 2026-10-25; protocol v0.3.9, the record's view).

Two ways, both kept:

- a collision the record says came before — the region's scars on the step's
  source, whose return collided the same way, in the same situation, by the same
  kind of act — turns it for a choice longer each time, and the thought names
  those scars as `event:<seq>`;
- the recent steps it weighs the onlooker's word by, and the evidence an inducer
  is shown, are read from the record's seals and memory, the step in hand as it
  came — the same steps the mind kept, each read recorded.
"""

from __future__ import annotations

from types import SimpleNamespace

from arc3.decisions import situation_fit
from arc3.observe import FRAME_CHANNEL, STATUS_CHANNEL, admit, transducers
from arc3.organs import ARC_ORGANS
from arc3.task import TASK_CUE
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
from dil.store.resist_event import ReadRecordActivity
from mind.learning import Learning
from mind.models.grid import GridInducer
from mind.mind import mind_rule
from tests.test_arc3_learning_mind import create_mind, frame, lit, status


def learning() -> Learning:
    return Learning(GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})


def scar(seq: int, datum_id: str):
    return SimpleNamespace(seq=seq, record=SimpleNamespace(datum_id=datum_id))


class Record:
    """A record's view that answers `scars` with what it is given, and keeps what was asked."""

    def __init__(self, scars):
        self._scars, self.asked = scars, []

    def scars(self, source, purpose, limit=None):
        self.asked.append((source, purpose))
        return list(self._scars)


# ── direction 1 ──

def test_a_collision_the_record_says_came_before_is_counted_by_the_regions_scars():
    mind = learning()
    key = ("silence", "situation-a", ("kind",))
    # The returns of its earlier turns, once their ids came back.
    unit_a, unit_b = object(), object()
    mind._collided_unsettled = [(key, unit_a), (("silence", "situation-b", ("kind",)), unit_b)]
    ids = {id(unit_a): "signal-3-0", id(unit_b): "signal-5-0"}
    mind.recall_from(SimpleNamespace(id_of=lambda u: ids.get(id(u)), read=lambda *a: None))
    assert mind._collided == {"signal-3-0": key, "signal-5-0": ("silence", "situation-b", ("kind",))}
    record = Record([scar(40, "signal-5-0"), scar(31, "signal-3-0"), scar(12, "signal-1-0")])
    mind.read_record(record)
    mind.step_source = "frame"
    assert mind._repeats(key) == [31], "only the scar whose return collided this way here"
    assert record.asked == [("frame", "collisions")]


def test_without_a_record_or_a_source_nothing_came_before():
    mind = learning()
    assert mind._repeats(("silence", "s", ("k",))) == []
    mind.read_record(Record([scar(1, "signal-0-0")]))
    assert mind._repeats(("silence", "s", ("k",))) == [], "no source its steps come from yet"


# ── direction 2 ──

def test_the_recent_steps_read_from_the_record_are_the_ones_the_mind_kept():
    mind = create_mind()
    rule = mind_rule(mind)
    compared: list[tuple[list, list]] = []

    def watching(entity_id, window, observed, contribute=None, ask=None, write=None, test=None,
                 field=None, read=None, record=None):
        out = rule(entity_id, window, observed, contribute, ask, write, test, field, read, record)
        content = observed.content if isinstance(observed.content, dict) else {}
        if content.get("channel") == STATUS_CHANNEL and mind._seen:
            seen = [(s, u, r) for s, u, r, _ in mind._recent()]
            kept = [(s.before, s.act, s.after, r) for s, _, r in seen]
            read_back = [(s.before, s.act, s.after, r) for s, r in mind.learning.recent_from_record(seen)]
            compared.append((kept, read_back))
        return out

    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=watching, fit=situation_fit), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    grids = [lit(0), lit(1), lit(2), lit(1), lit(0), lit(2)]
    for i in range(len(grids) - 1):
        cycle.run(HostCycleInput(signals=(frame(grids[i], grids[i + 1], action=1 + i % 2), status(action=1 + i % 2))))
    assert len(compared) >= 4
    for kept, read_back in compared:
        assert read_back == kept
    lines = [r for r in events.all() if isinstance(r, ReadRecordActivity)]
    assert any(l.purpose == "evidence" for l in lines), "each step read from the record is a record read"
