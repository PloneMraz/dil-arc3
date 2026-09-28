"""The directive: host data admitted as `prior`, recalled on a cue, read by the model.

It no longer reaches behaviour through a formula — the signs a formula put on
the region's answers were a want written in code, and want is the mind's, arising
in its thinking (Plone, 2026-09-25). What is pinned: the directive reaches the
store by the protocol's road, not a side door; T3 recalls it on a cue, and the
trace says so; and the model reads it only when it asks for it (Plone,
2026-09-27: nothing is poured into what the model reads).
"""

from __future__ import annotations

import pytest

from arc3.mind import UNSEATED, ModelEndpoint, create_mind, mind_rule
from arc3.observe import FRAME_CHANNEL, REGION_ENTITY, STATUS_CHANNEL, transducers
from arc3.prior import DIRECTIVE, RULES
from arc3.aim import MIND_AIM
from arc3.task import MIND_TASK
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

# The language model's earlier form is not seated: what goes through its seat is
# kept, not run (Plone, 2026-09-28; LOG.md).
unseated = pytest.mark.skip(reason=UNSEATED)

NOTHING = {"stateFrom": "NOT_FINISHED", "stateTo": "NOT_FINISHED", "levelsDelta": 0, "depthDelta": 0}
SAID = "You are playing a game. Your goal is to win."


class Listener:
    """A model that only records what it was shown."""

    def __init__(self):
        self.prompts = []

    def __call__(self, endpoint, messages):
        self.prompts.append(messages)
        return "", {}


@unseated
def test_a_recalled_datum_is_read_not_predicted_as_an_other():
    mind = create_mind(ModelEndpoint(), chat_fn=Listener(), task=MIND_TASK.payload, aim=MIND_AIM.payload)
    rule = mind_rule(mind)
    from dil.loop.types import InfoUnit, RefFrame

    unit = InfoUnit(
        content={"infoType": "raw", "channel": STORE_CHANNEL,
                 "value": {"entity": DIRECTIVE.id, "payload": DIRECTIVE.payload, "open": DIRECTIVE.open}},
        ref_frame=RefFrame(bound_layer=3, ref=f"channel:{STORE_CHANNEL}"),
        t=1,
    )
    assert rule(DIRECTIVE.id, (), unit) is unit
    assert mind.frame_calls == 0, "it did not become an Other the mind predicts"


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


@unseated
def test_the_first_status_report_brings_the_directive_to_mind_and_the_model_reads_it():
    model = Listener()
    mind = create_mind(ModelEndpoint(), chat_fn=model, task=MIND_TASK.payload, aim=MIND_AIM.payload)
    data, events = _store_with_rules(), create_event_log()
    layers = Layers(
        t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
        t5=create_t5(predict=mind_rule(mind)), t6=create_t6(), t7=create_t7(),
        t8=create_t8(),
    )
    cycle = create_cycle(layers=layers, glob=create_glob_mod({}, 0), data=data,
                         events=events, initial_emission=Emission(action=None))

    cycle.run(HostCycleInput(signals=(_status(1, NOTHING),)))
    cycle.run(HostCycleInput(signals=(_status(2, NOTHING),)))
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

    # When the mind next thinks, the model is not shown what T3 recalled: it did
    # not ask for it.
    grid, moved = [[0, 0], [0, 0]], [[1, 0], [0, 0]]
    miss = Signal(source_id=FRAME_CHANNEL, raw_payload={
        "entity": "frame", "before": [grid], "grids": [moved],
        "move": {"kind": "move", "actionId": 1, "x": None, "y": None}, "context": "action:1"}, t=3)
    cycle.run(HostCycleInput(signals=(miss,)))
    assert model.prompts and SAID not in model.prompts[-1][0]["content"]
    assert "What you recalled from memory" not in model.prompts[-1][0]["content"]

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


class Asker(Listener):
    """A model that asks its memory for the rules once, and otherwise writes nothing."""

    def __call__(self, endpoint, messages):
        self.prompts.append(messages)
        return ('ASK {"domain": "%s", "kind": "directive"}' % DIRECTIVE.open["domain"]) if len(self.prompts) == 1 else "", {}


@unseated
def test_what_the_model_asks_for_it_reads():
    model = Asker()
    mind = create_mind(ModelEndpoint(), chat_fn=model, task=MIND_TASK.payload, aim=MIND_AIM.payload)
    data, events = _store_with_rules(), create_event_log()
    layers = Layers(
        t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
        t5=create_t5(predict=mind_rule(mind)), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    cycle = create_cycle(layers=layers, glob=create_glob_mod({}, 0), data=data,
                         events=events, initial_emission=Emission(action=None))

    def miss(t, a, b):
        return Signal(source_id=FRAME_CHANNEL, raw_payload={
            "entity": "frame", "before": [a], "grids": [b],
            "move": {"kind": "move", "actionId": 1, "x": None, "y": None}, "context": "action:1"}, t=t)

    cycle.run(HostCycleInput(signals=(miss(1, [[0, 0]], [[1, 0]]),)))   # it thinks, and asks
    assert SAID not in model.prompts[0][0]["content"]
    cycle.run(HostCycleInput(signals=(miss(2, [[1, 0]], [[0, 0]]),)))   # the answer comes this cycle
    cycle.run(HostCycleInput(signals=(miss(3, [[0, 0]], [[1, 0]]),)))   # and is read at the next thought
    assert SAID in model.prompts[-1][0]["content"], "asked for, and so read"
