# spec/

The two documents this agent implements, kept here so a reader does not have to look for them elsewhere.

| file | what it is | words |
|---|---|---|
| `DIL-protocol-v0.3.9.md` | **the protocol** — normative: the invariants, the eight layers, the store, conformance. What an implementation MUST do. | 11,697 |
| `DIL-en-v9.md` | **the specification** it was derived from — the reasoning, the sources, the convergences with existing work, the author's note. | 25,168 |

Read the protocol to check the code; read the specification to understand why the protocol is shaped as it is. Section numbers cited in the code, in `README.md`, `CLAUDE.md` and `LOG.md` (§6.4, §9, INV-5 …) are the protocol's.

## Where they come from

These are copies. The canonical versions live in [dil-core](https://github.com/PloneMraz/dil-core), the reference implementation, and are revised there.

Copied from dil-core byte for byte on 2026-10-25 — the protocol at commit `c258f43a10dd2dccda177630d38d1dd588abc1bf`, the specification at `d95120d87736f92146c488743dbf590146b830bf`:

| file | last changed in dil-core | SHA-256 |
|---|---|---|
| `DIL-protocol-v0.3.9.md` | `c258f43`, 2026-10-25 | `90ecbaacf61c6e372f1c80a5e0de735b7e861027950aff61e502aee31e802ab3` |
| `DIL-en-v9.md` | `d95120d`, 2026-10-25 | `349bc3fb4429e95d7beea981e5b7e88fea07f4ad530e5adcde4c52bdfcc63e93` |

To check a copy still matches: `sha256sum spec/*.md`. If dil-core publishes a new version, it is copied here again and this table updated; the copies are never edited in place.

Earlier copies were replaced by `git mv`, so their text stays in this repository's history: v0.3.2 and v6 (dil-core `fe04f27`), then v0.3.3 (`3a4cfc8`) and v0.3.4 (`c7b544b`), on 2026-09-24, then v0.3.5 and v7 (`4f5da8f`, `f8230de`), then v0.3.6 and v8 (`68d948d`, 2026-10-04), then v0.3.7 (`d472e53`, 2026-10-19), then v0.3.8 and v9 (`d95120d`, 2026-10-25). The code under `src/dil/` implements v0.3.9: v0.3.7 added reading memory (§6.3 T5, §9 *Reading memory*, §13) and moved the tag schema to 4 for its `read` record; v0.3.8, with v9, corrected a wording only — the whole store is the agent's history, `[data]` its memory, `[event]` the record it reads and never alters; v0.3.9 adds reading the record — a view of `[event]` open to T5's rule every cycle, each read a `read-record` line (§9 *Reading the record*, §13) — and moves the tag schema to
5. The store's claim stays `0.3.5` (`dil.DIL_PROTOCOL_VERSION`), as dil-core's does, so an earlier store is read and written on.
