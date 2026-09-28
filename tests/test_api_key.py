"""An endpoint's API key goes into its request header and nowhere else.

Kept for after the competition (Plone, 2026-09-27): the endpoint names the
environment variable that holds the key, never the key. Here a real request is
sent to a local server, which is answered with a program; the key reaches the
server's header, and nothing the mind writes or keeps holds it. The model is
the language inducer, the mind's model with a served language model behind it.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from arc3.observe import FRAME_CHANNEL, STATUS_CHANNEL, admit, transducers
from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
from mind.mind import Mind, mind_rule
from mind.models.language import ModelEndpoint
from mind.models.language_inducer import LanguageInducer
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

KEY = "sk-test-0123456789-never-to-be-written"
PROGRAM = "def predict(grid, action, x=None, y=None):\n    return [row[:] for row in grid]\n"


def serve():
    seen: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            seen.append(self.headers.get("Authorization"))
            body = json.dumps({"choices": [{"message": {"content": f"```python\n{PROGRAM}```"},
                                            "finish_reason": "stop"}], "usage": {}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen


def test_the_key_reaches_the_header_and_nothing_the_mind_keeps(monkeypatch):
    monkeypatch.setenv("DIL_TEST_API_KEY", KEY)
    server, seen = serve()
    try:
        endpoint = ModelEndpoint(url=f"http://127.0.0.1:{server.server_port}/v1", api_key_env="DIL_TEST_API_KEY")
        inducer = LanguageInducer(ARC_ORGANS, endpoint)
        mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
        mind.receive("task", MIND_TASK.payload, None)
        data, events = create_data_store(), create_event_log()
        cycle = create_cycle(
            layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
                          t5=create_t5(predict=mind_rule(mind)), t6=create_t6(), t7=create_t7(), t8=create_t8()),
            glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
            initial_emission=Emission(action="boot"), admit=admit,
        )
        before = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
        after = [[0, 1, 0], [0, 0, 0], [0, 0, 0]]
        cycle.run(HostCycleInput(signals=(
            Signal(source_id=FRAME_CHANNEL, t=1, raw_payload={
                "entity": "frame", "before": [before], "grids": [after],
                "move": {"kind": "move", "actionId": 1, "x": None, "y": None}, "context": "action:1"}),
            Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
                "entity": "region", "context": "action:1", "affords": [1],
                "status": {"stateFrom": "NOT_FINISHED", "stateTo": "NOT_FINISHED", "levelsDelta": 0,
                           "depthDelta": 0}}),
        )))
    finally:
        server.shutdown()
    assert seen and all(h == f"Bearer {KEY}" for h in seen), "the key went out in each request's header"
    answers = [d for _, d in data.entries() if d.open.get("kind") == "thought"]
    assert answers and PROGRAM in answers[-1].payload["text"], "the answer came back and was kept"
    kept = json.dumps([(k, d.payload, d.open) for k, d in data.entries()], default=str)
    kept += json.dumps([repr(r) for r in events.all()])
    kept += json.dumps([repr(t) for t in mind.thoughts] + [repr(a) for a in inducer.answers])
    kept += repr(endpoint)
    assert KEY not in kept, "the key is in nothing the mind wrote, logged or keeps"


def test_a_missing_key_is_named_not_shown(monkeypatch):
    monkeypatch.delenv("DIL_TEST_API_KEY", raising=False)
    from mind.models.language import chat
    try:
        chat(ModelEndpoint(url="http://127.0.0.1:9/v1", api_key_env="DIL_TEST_API_KEY"), [])
    except RuntimeError as exc:
        assert "DIL_TEST_API_KEY" in str(exc)
    else:
        raise AssertionError("a request without its key must not be sent")
