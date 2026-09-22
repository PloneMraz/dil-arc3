"""DIL — the operating mechanism of this agent.

Not a library the host calls, and not a part sitting beside the other parts: it
is how the whole body runs. The host declares its faculties and DIL threads
through them; the self is what occurs while the loop runs, and the self is what
acts.

Built inside-out, the causal order fixed by the protocol (Invariants → Loop →
Self). Only the first ring exists so far.
"""

__version__ = "0.0.1"

# Protocol this implementation is written against. It is pinned deliberately:
# the reference implementation may move on, and a second implementation that
# silently tracks a moving target can no longer be checked against anything.
DIL_PROTOCOL_VERSION = "0.3.2"
