"""dil-arc3 commits at the close of every cycle in which the agent wrote a datum.

DEVIATION from dil-core, declared (store/decisions.py COMMIT_CADENCE): dil-core
commits on the scar rhythm alone. Here every version of what the agent wrote is
in a snapshot, and the marker ties that snapshot to its place in `[event]` — so
a revision, which leaves no content in the log (v0.3.3 §9), can be read back.
"""

from __future__ import annotations

from arc3.host import declaration
from dil.loop.cycle import HostCycleInput, Layers
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import WriteRequest, create_t5, persistence
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.runtime.commit import decode_snapshot_value
from dil.runtime.daemon import Daemon

TAGS = {"domain": "world-model", "kind": "program", "object": "frame"}


class Script:
    """A region that reports the same status for a fixed number of cycles."""

    def __init__(self, cycles: int) -> None:
        self.left = cycles
        self.t = 0

    def next(self):
        if self.left == 0:
            return None
        self.left -= 1
        self.t += 1
        return HostCycleInput(signals=(
            Signal(source_id="arc3-status", raw_payload={"entity": "region", "status": "playing"}, t=self.t),
        ))

    def deliver(self, response) -> None:
        pass


def test_every_cycle_that_writes_is_committed_and_each_version_is_in_its_snapshot(tmp_path):
    cycle_no = [0]
    plan = {
        1: WriteRequest(payload={"code": "v1"}, open=TAGS),
        3: WriteRequest(payload={"code": "v2"}, datum_id="written-1-0"),
    }
    last = [-1]

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
        if cycle_no[0] != last[0]:
            last[0] = cycle_no[0]
            if cycle_no[0] in plan:
                write(plan[cycle_no[0]])
        return persistence(entity_id, window, observed, contribute, ask, write)

    layers = Layers(
        t1=create_t1(), t2=create_t2(), t3=create_t3({}), t4=create_t4(),
        t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    clock = [1_800_000_000_000]

    def now():
        clock[0] += 1000
        return clock[0]

    daemon = Daemon(
        host=declaration("ls20", store_root=str(tmp_path)), source=Script(5), layers=layers,
        glob=create_glob_mod(), initial_emission=Emission(action=None), now=now,
        commit_every=10_000,  # far away: any commit here is the write cadence
    )
    daemon.start()
    for c in range(5):
        cycle_no[0] = c
        assert daemon.step()
    commits = daemon._commits

    markers = [commits.get_marker(h) for h in commits.list()]
    assert sorted(m.cycle for m in markers) == [2, 4], "one commit at the close of each cycle that wrote"
    held = {}
    for m in markers:
        state = commits.get_state(m.state_hash)
        entries = dict(decode_snapshot_value(state["data"]))
        held[m.cycle] = entries["written-1-0"].payload["code"]
    assert held == {2: "v1", 4: "v2"}, "each version of what was written is in a snapshot"


def test_a_recovery_keeps_what_was_on_its_way_to_t1(tmp_path):
    """The snapshot carries the driver's whole state, as dil-core's does: a
    datum written in the cycle before the commit still arrives after recovery."""
    cycle_no = [0]

    def make_layers(plan):
        last = [-1]

        def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
            if cycle_no[0] != last[0]:
                last[0] = cycle_no[0]
                if cycle_no[0] in plan:
                    write(plan[cycle_no[0]])
            return persistence(entity_id, window, observed, contribute, ask, write)

        return Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3({}), t4=create_t4(),
            t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        )

    clock = [1_800_000_000_000]

    def now():
        clock[0] += 1000
        return clock[0]

    first = Daemon(
        host=declaration("ls20", store_root=str(tmp_path)), source=Script(2),
        layers=make_layers({1: WriteRequest(payload={"code": "v1"}, open=TAGS)}),
        glob=create_glob_mod(), initial_emission=Emission(action=None), now=now,
        commit_every=10_000,
    )
    first.start()
    for c in range(2):
        cycle_no[0] = c
        first.step()
    marker = first._commits.head()
    first.stop()

    resumed = Daemon(
        host=declaration("ls20", store_root=str(tmp_path)), source=Script(1),
        layers=make_layers({}), glob=create_glob_mod(), initial_emission=Emission(action=None),
        now=now, commit_every=10_000, recover_from=marker,
    )
    resumed.start()
    cycle_no[0] = 2
    assert resumed.step()
    moved = [
        (r.from_, r.to) for r in resumed._events.all()
        if getattr(r, "activity_kind", None) == "provenance" and r.datum_id == "written-1-0"
    ]
    assert moved == [("nascent", "running")], "the write made before the commit arrived after recovery"


def test_a_snapshot_written_before_the_whole_driver_was_kept_still_restores():
    from dil.runtime.daemon import _driver_from_payload

    driver = _driver_from_payload({"cycle": 7, "lastEmission": {"kind": "respond"}})
    assert driver.cycle == 7
    assert driver.last_emission.action == {"kind": "respond"}
    assert driver.pending_writes == () and driver.pending_returns == ()
