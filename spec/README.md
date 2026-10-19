# spec/

The two documents this agent implements, kept here so a reader does not have to
look for them elsewhere.

| file | what it is | words |
|---|---|---|
| `DIL-protocol-v0.3.7.md` | **the protocol** — normative: the invariants, the eight layers, the store, conformance. What an implementation MUST do. | 10,953 |
| `DIL-en-v8.md` | **the specification** it was derived from — the reasoning, the sources, the convergences with existing work, the author's note. | 25,108 |

Read the protocol to check the code; read the specification to understand why
the protocol is shaped as it is. Section numbers cited in the code, in
`README.md`, `CLAUDE.md` and `LOG.md` (§6.4, §9, INV-5 …) are the protocol's.

## Where they come from

These are copies. The canonical versions live in
[dil-core](https://github.com/PloneMraz/dil-core), the reference
implementation, and are revised there.

Copied from dil-core byte for byte — the protocol on 2026-10-19 at commit
`d472e5344fb911a18e3b4fca5cd2b754f85e23eb`, the specification on 2026-10-04 at
`68d948db41d6be701b6acab9ed7e2e4d04b8015b`:

| file | last changed in dil-core | SHA-256 |
|---|---|---|
| `DIL-protocol-v0.3.7.md` | `d472e53`, 2026-10-19 | `1e3c14bbd203483bc4e71dc07653c062711aa949b1132d15f77cc77826b5e801` |
| `DIL-en-v8.md` | `68d948d`, 2026-10-04 | `5cc58a526094b0ae68b23907fd0e5b23c4b8050ea07314e3f794b4f49c9bcb95` |

To check a copy still matches: `sha256sum spec/*.md`. If dil-core publishes a new
version, it is copied here again and this table updated; the copies are never
edited in place.

Earlier copies were replaced by `git mv`, so their text stays in this
repository's history: v0.3.2 and v6 (dil-core `fe04f27`), then v0.3.3
(`3a4cfc8`) and v0.3.4 (`c7b544b`), on 2026-09-24, then v0.3.5 and v7 (`4f5da8f`,
`f8230de`), then v0.3.6 (`68d948d`, 2026-10-04). The code under `src/dil/`
implements v0.3.7, which adds reading memory (§6.3 T5, §9 *Reading memory*, §13)
and moves the tag schema to 4 for its `read` record; the store's claim stays
`0.3.5` (`dil.DIL_PROTOCOL_VERSION`), as dil-core's does, so an earlier store is
read and written on.
