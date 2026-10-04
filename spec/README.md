# spec/

The two documents this agent implements, kept here so a reader does not have to
look for them elsewhere.

| file | what it is | words |
|---|---|---|
| `DIL-protocol-v0.3.6.md` | **the protocol** — normative: the invariants, the eight layers, the store, conformance. What an implementation MUST do. | 10,479 |
| `DIL-en-v8.md` | **the specification** it was derived from — the reasoning, the sources, the convergences with existing work, the author's note. | 25,076 |

Read the protocol to check the code; read the specification to understand why
the protocol is shaped as it is. Section numbers cited in the code, in
`README.md`, `CLAUDE.md` and `LOG.md` (§6.4, §9, INV-5 …) are the protocol's.

## Where they come from

These are copies. The canonical versions live in
[dil-core](https://github.com/PloneMraz/dil-core), the reference
implementation, and are revised there.

Both copied on 2026-10-04 from dil-core at commit
`0b9c7668a63bc1032523272948808107d7b5c224`, byte for byte:

| file | last changed in dil-core | SHA-256 |
|---|---|---|
| `DIL-protocol-v0.3.6.md` | `0b9c766`, 2026-10-04 | `7c42b254cdec75a88b92d0ce9ed9dc16613bfbd2c4ef33c1f9fa6439e8027ecb` |
| `DIL-en-v8.md` | `0b9c766`, 2026-10-04 | `25e0c7dd2ac0dfe8bb28818e619885dda6be3fda1052e48c2deb647800a90b8e` |

To check a copy still matches: `sha256sum spec/*.md`. If dil-core publishes a new
version, it is copied here again and this table updated; the copies are never
edited in place.

Earlier copies were replaced by `git mv`, so their text stays in this
repository's history: v0.3.2 and v6 (dil-core `fe04f27`), then v0.3.3
(`3a4cfc8`) and v0.3.4 (`c7b544b`), on 2026-09-24, then v0.3.5 and v7 (`4f5da8f`,
`f8230de`). The code under `src/dil/` implements v0.3.6, whose change from v0.3.5
is to the text alone (the whole store is the agent's memory), so the store's
claim stays `0.3.5` (`dil.DIL_PROTOCOL_VERSION`), as dil-core's does.
