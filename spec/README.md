# spec/

The two documents this agent implements, kept here so a reader does not have to
look for them elsewhere.

| file | what it is | words |
|---|---|---|
| `DIL-protocol-v0.3.3.md` | **the protocol** — normative: the invariants, the eight layers, the store, conformance. What an implementation MUST do. | 9,656 |
| `DIL-en-v7.md` | **the specification** it was derived from — the reasoning, the sources, the convergences with existing work, the author's note. | 25,009 |

Read the protocol to check the code; read the specification to understand why
the protocol is shaped as it is. Section numbers cited in the code, in
`README.md` and in `CLAUDE.md` (§6.4, §9, INV-5 …) are the protocol's.

## Where they come from

These are copies. The canonical versions live in
[dil-core](https://github.com/PloneMraz/dil-core), the reference
implementation, and are revised there.

Copied on 2026-09-24 from dil-core at commit
`3a4cfc84fc3f6167899e3ac88c5c92bacbb9c711`, byte for byte:

| file | last changed in dil-core | SHA-256 |
|---|---|---|
| `DIL-protocol-v0.3.3.md` | `f8230de`, 2026-09-24 | `b80b9984c187fbd2e4a0588d99ca9c605fe5c60eb2dd6ead6cb17ee8652cfedc` |
| `DIL-en-v7.md` | `f8230de`, 2026-09-24 | `42c846795d84a304146a330d2761ff16f9f9292835a8c2136418cd870cb457c0` |

To check a copy still matches: `sha256sum spec/*.md`. If dil-core publishes a new
version, it is copied here again and this table updated; the copies are never
edited in place.

The previous copies (v0.3.2 and v6, from dil-core `fe04f27`) were replaced on the
same day by `git mv`, so their text stays in this repository's history. The code
under `src/dil/` still implements v0.3.2 until it is ported; `CLAUDE.md` records
when that lands.
