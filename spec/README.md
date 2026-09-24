# spec/

The two documents this agent implements, kept here so a reader does not have to
look for them elsewhere.

| file | what it is | words |
|---|---|---|
| `DIL-protocol-v0.3.4.md` | **the protocol** — normative: the invariants, the eight layers, the store, conformance. What an implementation MUST do. | 9,890 |
| `DIL-en-v7.md` | **the specification** it was derived from — the reasoning, the sources, the convergences with existing work, the author's note. | 25,009 |

Read the protocol to check the code; read the specification to understand why
the protocol is shaped as it is. Section numbers cited in the code, in
`README.md`, `CLAUDE.md` and `LOG.md` (§6.4, §9, INV-5 …) are the protocol's.

## Where they come from

These are copies. The canonical versions live in
[dil-core](https://github.com/PloneMraz/dil-core), the reference
implementation, and are revised there.

Copied on 2026-09-24 from dil-core at commit
`c7b544b658138a493a6e5bad81cad88b5661ba95`, byte for byte:

| file | last changed in dil-core | SHA-256 |
|---|---|---|
| `DIL-protocol-v0.3.4.md` | `c2c0cd2`, 2026-09-24 | `831917da72914b0b26f8a4d67442587391bf6d5ecb31da83bd924a7253d5423a` |
| `DIL-en-v7.md` | `f8230de`, 2026-09-24 | `42c846795d84a304146a330d2761ff16f9f9292835a8c2136418cd870cb457c0` |

To check a copy still matches: `sha256sum spec/*.md`. If dil-core publishes a new
version, it is copied here again and this table updated; the copies are never
edited in place.

Earlier copies were replaced by `git mv`, so their text stays in this
repository's history: v0.3.2 and v6 (dil-core `fe04f27`), then v0.3.3
(`3a4cfc8`), all on 2026-09-24. The code under `src/dil/` implements v0.3.4.
