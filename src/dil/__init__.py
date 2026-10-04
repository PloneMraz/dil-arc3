"""DIL — the operating mechanism of this agent.

Not a library the host calls, and not a part sitting beside the other parts: it
is how the whole body runs. The host declares its faculties and DIL threads
through them; the self is what occurs while the loop runs, and the self is what
acts.

Built inside-out, the causal order fixed by the protocol (Invariants → Loop →
Self). Every ring exists: the invariants (`invariants/`), the loop (`loop/`),
the store (`store/`), the runtime that runs them (`runtime/`), what a host
declares (`host/`), and the conformance checks (`conformance/`, `precondition/`).
"""

__version__ = "0.0.1"

# Protocol this implementation is written against (`spec/`). It is pinned
# deliberately: the reference implementation may move on, and a second
# implementation that silently tracks a moving target can no longer be checked
# against anything. The store's claim is stamped with it (`store/substrate.py`).
# The text in `spec/` is v0.3.6, whose change from v0.3.5 is to the text alone
# (the whole store is the agent's memory), so the claim stays at 0.3.5, as
# dil-core's does.
DIL_PROTOCOL_VERSION = "0.3.5"
