"""(B): what the mind's model computes from, the mind reads from its memory
(Plone, 2026-10-05; DEVIATION 7, READ).

The whole store is the agent's memory. What came in a cycle is in hand in that
cycle; from the next it is read from the store through T5's view, each cycle's
reads are recorded in `[event]`, and what is written from what was read names
it among what it was built from.
"""

from __future__ import annotations

from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
from dil.conformance.checker import check_conformance
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
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from arc3.observe import FRAME_CHANNEL, admit, transducers
from mind.learning import Recalled
from mind.mind import Mind, mind_rule
from mind.models.grid import GridInducer
from mind.models.language_inducer import LanguageInducer
from tests.test_arc3_learning_mind import frame, lit, of_kind, run, status
from tests.test_language_inducer import RIGHT, STILL, Script, block


def loop(inducer=None, rule=None):
    mind = Mind(inducer or GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})
    mind.receive("task", MIND_TASK.payload, None)
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=rule or mind_rule(mind)), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    return mind, cycle, data, events


def reads(events) -> dict[str, list[tuple[int, str]]]:
    out: dict[str, list[tuple[int, str]]] = {}
    for r in events.all():
        if getattr(r, "activity_kind", None) == "read":
            out.setdefault(r.purpose, []).extend((r.cycle_mark, i) for i in r.read)
    return out


def written(events) -> dict[str, tuple[str, ...]]:
    return {w.datum_id: w.built_from for r in events.all() if getattr(r, "activity_kind", None) == "cycle-seal"
            for w in r.activity.written}


def three(cycle):
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    run(cycle, frame(lit(0), lit(1)), status())


def test_what_came_before_is_no_longer_held_but_read_from_the_store():
    mind, cycle, data, events = loop()
    three(cycle)
    model = mind.learning
    assert all(isinstance(held, Recalled) for held in model._raw.values()), "every state met is memory now"
    first = model._hypotheses[0]
    assert first.held is None and first.recall is not None, "its form is read from its datum"
    got = reads(events)
    assert any(i == first.datum_id for _, i in got["hypothesis"]), "computing with it, it read it"
    assert any(i == "signal-0-0" for _, i in got["state"])


def test_every_read_is_memory_and_the_trace_says_so():
    mind, cycle, data, events = loop()
    three(cycle)
    report = check_conformance(events)
    c6 = next(r for r in report.results if r.id == "6")
    claim = next(c for c in c6.claims if c.claim.startswith("every datum the agent read"))
    assert claim.verdict == "pass" and c6.verdict == "pass", c6.detail
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec


def test_what_it_chose_names_what_it_read_to_choose():
    mind, cycle, data, events = loop()
    three(cycle)
    choices = sorted((k for k, d in of_kind(data, "choice") if d.payload["cycle"] == 3), key=str)
    assert choices
    assert "signal-0-0" in written(events)[choices[-1]], "the state it stood in, read to choose"


def test_the_view_holds_memory_alone():
    seen: list = []

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, test=None, field=None,
             read=None):
        if (observed.content or {}).get("channel") == FRAME_CHANNEL:
            n = len(seen)
            seen.append((read.read(f"signal-{n}-0", "probe"),
                         read.read(f"signal-{n - 1}-0", "probe") if n else None))
        return observed

    _, cycle, _, events = loop(rule=rule)
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    assert seen[0] == (None, None) and seen[1][0] is None, "what arrives in a cycle is met in it, not recalled"
    assert seen[1][1] is not None and seen[1][1].payload["grids"] == [lit(1)], "what came before is memory"
    assert reads(events) == {"probe": [(1, "signal-0-0")]}


def test_the_recent_steps_are_read_only_when_the_model_looks_at_them():
    _, cycle, _, events = loop()
    three(cycle)
    assert "evidence" not in reads(events), "the exact inducer computes nothing from the steps before"
    script = Script(block(STILL), block(RIGHT))
    mind, cycle, data, events = loop(LanguageInducer(ARC_ORGANS, chat_fn=script))
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(2)), status())
    assert "#0 ACTION1" in script.shown[1][0]["content"], "shown the step before, read from the store"
    assert set(reads(events)["evidence"]) == {(1, "signal-0-0"), (1, "signal-0-1")}, "the step and its report"
    program = next(k for k, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program")
    assert {"signal-0-0", "signal-0-1"} <= set(written(events)[program]), "built from what it was shown"


def test_a_revision_of_its_tallies_alone_restores_nothing():
    inducer = GridInducer(ARC_ORGANS)
    restored: list = []
    real = inducer.restore
    # What it said of a step (a suspect, of where the aim may lie, is not said of one).
    inducer.restore = lambda payload: (payload.get("form") != "suspect" and restored.append(payload.get("act")),
                                       real(payload))[1]
    mind, cycle, data, events = loop(inducer)
    for _ in range(4):
        run(cycle, frame(lit(0), lit(1)), status())
        run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    revised = [r.datum_id for r in events.all() if getattr(r, "activity_kind", None) == "revision"]
    assert len(revised) > len(set(revised)), "each weighed again and again"
    assert len(restored) == len(set(map(str, restored))) == 2, "each restored once: its inducer said the same"


def test_the_program_the_model_reads_the_grid_with_is_had_back_from_memory(monkeypatch):
    import mind.models.language_inducer as language
    compiled: list = []
    real = language.compile_program
    monkeypatch.setattr(language, "compile_program", lambda code: (compiled.append(code), real(code))[1])
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=Script(block(RIGHT)))
    mind, cycle, data, events = loop(inducer)
    run(cycle, frame(lit(0), lit(1)), status())                        # it writes the program
    run(cycle, frame(lit(1), lit(2, 1)), status())
    run(cycle, frame(lit(2, 1), lit(1), action=2), status(action=2))
    run(cycle, frame(lit(1), lit(0, 1), action=2), status(action=2))
    run(cycle, frame(lit(0, 1), lit(1)), status())
    program = next(k for k, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program")
    assert inducer._seeing[0] is None and inducer._last[0] is None, "not held: had back from the mind's memory"
    assert any(i == program for _, i in reads(events)["hypothesis"]), "read from the store"
    revised = [r for r in events.all() if getattr(r, "activity_kind", None) == "revision" and r.datum_id == program]
    assert len(revised) >= 2, "weighed at every step, its datum revised"
    assert compiled == [RIGHT, RIGHT], "loaded when written, and once from its datum: its code never changed"
