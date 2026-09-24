# spec/

The two documents this agent implements, kept here so a reader does not have to
look for them elsewhere.

| file | what it is | words |
|---|---|---|
| `DIL-protocol-v0.3.2.md` | **the protocol** — normative: the invariants, the eight layers, the store, conformance. What an implementation MUST do. | 8,911 |
| `DIL-en-v6.md` | **the specification** it was derived from — the reasoning, the sources, the convergences with existing work, the author's note. | 24,586 |

Read the protocol to check the code; read the specification to understand why
the protocol is shaped as it is. Section numbers cited in the code, in
`README.md` and in `CLAUDE.md` (§6.4, §9, INV-5 …) are the protocol's.

## Where they come from

These are copies. The canonical versions live in
[dil-core](https://github.com/PloneMraz/dil-core), the reference
implementation, and are revised there.

Copied on 2026-09-24 from dil-core at commit
`fe04f2723eedaf780a490260140ef24acc92793d`, byte for byte:

| file | last changed in dil-core | SHA-256 |
|---|---|---|
| `DIL-protocol-v0.3.2.md` | `7c1dbf3`, 2026-07-23 | `72bea6cadef6802754a1baa48004c676b997cafcfde4cf113f40ec516c5a08f8` |
| `DIL-en-v6.md` | `015a9af`, 2026-07-23 | `acf355909eec99bfcd084ee5c3437ee43dc342c4ce45e7498302843bfb990a1c` |

To check a copy still matches: `sha256sum spec/*.md`. If dil-core publishes a new
version, it is copied here again and this table updated; the copies are never
edited in place.
