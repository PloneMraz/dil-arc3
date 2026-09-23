"""Seeing individuals: following pieces, grouping by common fate, reading ahead.

The load-bearing properties, in order: a thing keeps its identity while it moves;
what happens to it reads the same wherever it happens; pieces that move together
become one thing — but only from evidence the PAST supplied (INV-8); and a thing
sees past its own parts to what actually lies ahead of it.
"""

from __future__ import annotations

from arc3.seeing import MIN_COMOVEMENTS, create_seeing
from tests.test_arc3_perceive import framed


def mover(row: int, col: int = 30, wall: bool = False):
    """A two-colour object — 9 on top, 12 underneath — optionally below a wall."""
    cells = {
        (row, col): 9, (row, col + 1): 9,
        (row + 1, col): 12, (row + 1, col + 1): 12,
    }
    if wall:
        for c in range(20, 42):
            cells[(5, c)] = 5
    return framed(cells)


def by_value(scene, value: int):
    return [t for t in scene.things if str(value) in t.entity.split("#")[0].split(":")[1].split("+")]


# ── identity ──


def test_a_thing_that_moves_keeps_its_identity():
    seeing = create_seeing()
    f0, f1, f2 = mover(30), mover(25), mover(20)
    first = {t.entity for t in seeing.look(f0, f1).things}
    second = {t.entity for t in seeing.look(f1, f2).things}
    assert first == second


def test_the_same_move_from_two_places_reads_as_the_same_change():
    here = create_seeing().look(framed({(30, 30): 9}), framed({(25, 30): 9})).things[0]
    there = create_seeing().look(framed({(12, 8): 9}), framed({(7, 8): 9})).things[0]
    assert here.change == there.change
    assert here.change.moved == (-5, 0)


def test_the_four_directions():
    start = framed({(30, 30): 9})
    for end, expected in (((25, 30), (-5, 0)), ((35, 30), (5, 0)),
                          ((30, 25), (0, -5)), ((30, 35), (0, 5))):
        scene = create_seeing().look(start, framed({end: 9}))
        assert scene.things[0].change.moved == expected


def test_a_contiguous_run_does_not_rematch_a_frame_it_has_already_seen():
    """The host passes the same Frame object as `now` then `prev`; its pieces
    keep the ids they were given rather than being matched afresh."""
    seeing = create_seeing()
    f0, f1, f2 = mover(30), mover(25), mover(20)
    seeing.look(f0, f1)
    assert seeing._ids_for(f1, ()) == seeing._last_ids


# ── grouping by common fate ──


def test_pieces_that_keep_moving_together_become_one_thing():
    seeing = create_seeing()
    frames = [mover(r) for r in (40, 35, 30, 25)]
    scenes = [seeing.look(a, b) for a, b in zip(frames, frames[1:])]
    assert any("9+12" in t.entity for t in scenes[-1].things)


def test_grouping_uses_only_evidence_the_past_supplied():
    """INV-8. Grouping learns from how pieces moved; the situation a thing is
    read in predicts how it will move. The cycle that supplies the deciding
    co-movement must still be read with the OLD grouping, or the answer would
    leak into the question."""
    seeing = create_seeing()
    frames = [mover(r) for r in (40, 35, 30, 25)]
    grouped = []
    for a, b in zip(frames, frames[1:]):
        grouped.append(any("+" in t.entity for t in seeing.look(a, b).things))
    # Co-movement reaches MIN_COMOVEMENTS during look #MIN_COMOVEMENTS; the
    # group is first visible in the look AFTER it.
    assert grouped[MIN_COMOVEMENTS - 1] is False
    assert grouped[MIN_COMOVEMENTS] is True


def test_one_occasion_of_moving_apart_vetoes_grouping():
    seeing = create_seeing()
    a = framed({(30, 30): 9, (40, 30): 12})
    b = framed({(25, 30): 9, (40, 30): 12})          # only 9 moves
    c = framed({(20, 30): 9, (35, 30): 12})          # both move, same way
    d = framed({(15, 30): 9, (30, 30): 12})          # again
    e = framed({(10, 30): 9, (25, 30): 12})
    for x, y in ((a, b), (b, c), (c, d)):
        seeing.look(x, y)
    assert not any("+" in t.entity for t in seeing.look(d, e).things)


def test_holding_still_together_is_not_evidence_of_being_one_thing():
    """Walls resting side by side for ever are not one object."""
    seeing = create_seeing()
    still = framed({(30, 30): 9, (40, 40): 12})
    for _ in range(MIN_COMOVEMENTS + 2):
        seeing.look(still, still)
    assert not any("+" in t.entity for t in seeing.look(still, still).things)


# ── what lies ahead ──


def test_a_thing_sees_the_wall_ahead_of_it():
    seeing = create_seeing()
    scene = seeing.look(framed({(30, 30): 9, (5, 30): 5}), framed({(25, 30): 9, (5, 30): 5}))
    nine = by_value(scene, 9)[0]
    assert "up:5" in nine.ahead


def test_the_edge_of_the_grid_is_something_to_meet():
    scene = create_seeing().look(framed({(0, 30): 9}), framed({(0, 30): 9}))
    assert "up:edge" in scene.things[0].ahead


def test_a_trailing_part_sees_the_wall_once_it_is_known_to_be_part_of_the_thing():
    """MEASURED: before grouping, a ray from the back part of a two-colour object
    stopped at its own front part and never saw the wall — 67% against the front
    part's 100%. Once the parts are one thing, the ray passes its own cells."""
    seeing = create_seeing()
    frames = [mover(r, wall=True) for r in (40, 35, 30, 25, 20)]
    scenes = [seeing.look(a, b) for a, b in zip(frames, frames[1:])]
    grouped = [t for t in scenes[-1].things if "9+12" in t.entity]
    assert grouped, "the parts were grouped"
    assert "up:5" in grouped[0].ahead


# ── coming, going, touching ──


def test_a_thing_that_arrives_appears_and_one_that_goes_vanishes():
    came = create_seeing().look(framed({}), framed({(10, 10): 9})).things[0]
    assert came.change.appeared and came.change.moved is None
    went = create_seeing().look(framed({(10, 10): 9}), framed({})).things[0]
    assert went.change.vanished


def test_only_things_still_there_are_present():
    scene = create_seeing().look(framed({(10, 10): 9, (40, 40): 3}), framed({(10, 10): 9}))
    assert len(scene.present) == 1


def test_contact_made_is_an_interaction():
    scene = create_seeing().look(
        framed({(10, 10): 9, (10, 20): 3}), framed({(10, 10): 9, (10, 11): 3})
    )
    assert [k for _a, _b, k in scene.interactions] == ["contact-made"]


def test_a_standing_contact_is_not_an_interaction():
    """Measured near-constant; it would have said nothing."""
    touching = framed({(10, 10): 9, (10, 11): 3})
    assert create_seeing().look(touching, touching).interactions == ()
