"""What the character may know beforehand, and the one door it comes in by.

The load-bearing properties: every item passes the tagging-gate on its own
merits; the runtime admits them as `prior` with no cycle-mark; and an item that
cannot be tagged honestly is refused and reported, never smuggled in.
"""

from __future__ import annotations

from dil.host import PreexistingItem
from dil.runtime.requisition import requisition
from dil.store.tagging_gate import HostDatum, admit_host_data

from arc3.host import declaration
from arc3.prior import DIRECTIVE, DOMAIN, PRIOR, RULES, ArcRules
from arc3.task import MIND_TASK, TASK_SOURCE


def _quotes(value):
    if isinstance(value, dict):
        if set(value) == {"text", "source"}:
            yield value
        else:
            for v in value.values():
                yield from _quotes(v)
    elif isinstance(value, list):
        for v in value:
            yield from _quotes(v)


def test_every_item_passes_the_gate_as_prior():
    for item in RULES:
        datum = admit_host_data(
            HostDatum(payload=item.payload, admitting_layer=item.admitting_layer,
                      open=item.open),
            now=1,
        )
        assert datum.fixed.provenance == "prior"
        assert datum.fixed.cycle_mark is None  # it has not run yet


def test_every_sentence_names_the_document_it_was_read_in():
    quotes = [q for item in RULES for q in _quotes(item.payload)]
    assert quotes
    assert all(q["source"].startswith("https://") for q in quotes)


def test_the_directive_is_the_one_sentence_every_model_is_given():
    assert [q["text"] for q in DIRECTIVE.payload["says"]] == [
        "You are playing a game. Your goal is to win."
    ]


def test_the_directive_names_what_a_frame_reports():
    """It must be written in what the host can sense, or the mind could never
    connect it to anything it sees."""
    assert DIRECTIVE.payload["objective"]["state"] == "WIN"
    assert DIRECTIVE.payload["ended_without"]["state"] == "GAME_OVER"
    assert DIRECTIVE.payload["toward"]["count"] == "levels_completed"


def test_the_host_declares_the_rules_as_preexisting_memory():
    pre = declaration("ls20").store.preexisting
    assert pre is not None
    assert [i.id for i in pre.scan()] == [i.id for i in PRIOR]
    assert [i.id for i in PRIOR] == [*(i.id for i in RULES), MIND_TASK.id], \
        "the rules, then what the mind is told (the earlier form's aim prior went with it)"


def test_what_the_mind_is_told_is_marked_as_this_projects_own_words():
    assert MIND_TASK.open["source"] == TASK_SOURCE == "dil-arc3"
    assert all(item.open["source"] != TASK_SOURCE for item in RULES), "the rules are quoted, not written here"


def test_the_runtime_admits_them_through_the_gate(tmp_path):
    got = requisition(declaration("ls20", store_root=str(tmp_path)), now=1)
    try:
        assert got.admitted == len(PRIOR)
        assert got.data.get(MIND_TASK.id).fixed.provenance == "prior"
        assert got.rejected == ()
        stored = got.data.get(DIRECTIVE.id)
        assert stored is not None
        assert stored.fixed.provenance == "prior"
        assert stored.fixed.cycle_mark is None
        assert stored.open["domain"] == DOMAIN
    finally:
        got.close()


def test_an_item_carrying_a_verdict_is_refused_not_smuggled(tmp_path):
    verdict = PreexistingItem(
        id="prior:bad",
        payload={"says": []},
        open={"domain": DOMAIN, "kind": "directive", "valence": "good"},
    )
    got = requisition(
        declaration("ls20", store_root=str(tmp_path), prior=ArcRules((verdict,))),
        now=1,
    )
    try:
        assert got.admitted == 0
        assert [r.id for r in got.rejected] == ["prior:bad"]
        assert got.data.get("prior:bad") is None
    finally:
        got.close()


def test_every_item_is_about_something_an_arrival_asks_with():
    """An item waits in the store until an arrival describes what it is about (T3's
    query): one whose description no channel asks with is never recalled. Until
    2026-10-21 the item about the world's things waited for "things", which no
    channel has sent since the host stopped computing things."""
    from arc3.observe import ACTIONS_OBJECT, LEVELS_OBJECT, STATUS_OBJECT, VISION_SENSE
    cues = [{"sense": VISION_SENSE}, {"object": STATUS_OBJECT}, {"object": LEVELS_OBJECT}, {"object": ACTIONS_OBJECT}]
    for item in RULES:
        assert any(all(item.open.get(k) == v for k, v in cue.items()) for cue in cues), item.id
