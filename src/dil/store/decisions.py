"""Declared DECIDE@IMPL choices for the experience store (protocol §10, §12).

The protocol leaves these open *on purpose*; a conforming implementation MUST
fill each and MUST declare the value it chose (protocol §12). This file is that
declaration: every representational and numeric choice the store makes is named
here, with its rationale, so nothing downstream is hardcoded silently.

These choices are for the host this agent controls. They are environment
decisions, not protocol law; a different host may declare differently without
changing the protocol. Where this implementation's declaration differs from
dil-core's, the difference is marked — it is a different host, so it is entitled
to differ, but not to differ silently.

Ported from dil-core against DIL protocol v0.3.3.
"""

from typing import Final

# The store schema version — bumped whenever the meaning or domain of a fixed tag
# changes. Provenance went from 3 values to 5 at v0.3.2 (prior/running/scar →
# prior/running/simulated/projected/scar), the change that motivates versioning.
# Because `[event]` is immutable — a written record is never edited — the log is
# self-describing from version 2 on: every persisted line is stamped with the
# SCHEMA_VERSION it was written under, so a reader interprets each record by its
# own version, and the DIL-CLAIM records the current one.
#   1 → the original 3-state provenance. PRE-VERSIONING: no per-line stamp,
#       hashed under the old version-less formula. Not part of the versioned
#       chain — see SCHEMA_VERSIONED_SINCE.
#   2 → v0.3.2's 5-state provenance graph. First versioned schema: stamped per
#       line, hashed with the version-inclusive formula.
#   3 → v0.3.3's 6-state graph (adds `nascent`), entries by origin (region
#       returns and the cycle datum enter at `running`), and the `revision` line.
SCHEMA_VERSION: Final = 3

# The first schema version under the self-describing, version-stamped chain — the
# boundary of the versioned `[event]` chain. A pre-versioning line is NOT
# verifiable by the current verifier and is refused, with an explicit version
# reason, both by the chain walker and — before a store is ever run — by the
# substrate claim check.
#
# DECIDE@IMPL policy, HONEST STATUS — not derivable from the protocol. §9 fixes
# that `[event]` is immutable and the one trust root, but not how a verifier
# treats logs written under an earlier, incompatible hash formula.
#
#   CHOSEN (B) — Draw a hard boundary. The verifier rejects a pre-versioning line
#     by version, and the substrate refuses a store stamped below the boundary as
#     a clean non-start, so the system never reaches the incoherent state of a
#     claim advanced over a store whose chain will not verify. The boundary is
#     ONE-TIME: the hash formula is frozen from version 2 on, so 2→3→… bumps stay
#     verifiable; only the pre-versioning era is cut off.
#
#   REJECTED (A) — A verifier branch that re-hashes pre-versioning lines under the
#     old formula. Its security cost is near-zero, but it permanently forks the
#     one trust-root verifier for a format no live store uses.
#
# This implementation has never written a pre-versioning line — it was born at
# version 2 — so the boundary costs it nothing at all.
SCHEMA_VERSIONED_SINCE: Final = 2

# DECIDE@IMPL tag F — store representation.
#
# DIFFERS FROM dil-core, deliberately: the reference declares SQLite via
# `node:sqlite`. This host runs on Python, so `[data]` is SQLite via `sqlite3`
# from the standard library — same engine, same synchronous interface, and here
# too it needs no third-party dependency. `[event]` is unchanged: append-only
# hash-chained JSONL.
STORE_REPRESENTATION: Final = (
    "[data] = SQLite (python sqlite3, stdlib) under store/memory/; "
    "[event] = append-only hash-chained JSONL under store/event-log/; "
    "RAM holds only bounded caches, never the store of record"
)
# Rationale (declared choice, not invented): the store-of-record lives on the
# host's requisitioned substrate, never in RAM. `[data]` (mutable present) is a
# SQLite table. `[event]` (append-only) stays JSONL + sha256 hash chain, the
# tamper-evident audit artifact. RAM is a bounded working cache only. The
# in-memory data store and list-backed `[event]` log are TEST FIXTURES.
#
# File-backed layout (the directory boundary IS the rollback boundary). One
# parent root, `store/`, named after the ring itself:
#
#   <deployment root>/store/
#     memory/      — [data] and restorable working state: the ONLY location a
#                    recovery/rollback rewrites (mutable by design)
#     event-log/   — [event] segments: append-only, records read-only forever;
#                    NEVER rolled back — it keeps recording through a rollback
#     commits/     — content-addressed markers: append-only; a rollback ADDS a
#                    fork marker, it never deletes one
#
# `event-log/` and `commits/` sit BESIDE memory/, not inside it: they are outside
# the loop's mutable reach, which is what makes them trustworthy as evidence
# about it. Store-kind is carried by location, not by a name prefix.

# DECIDE@IMPL tag F — index keys.
# Rationale: the two access paths the loop and an auditor actually need.
INDEX_KEYS: Final = ("source_id", "provenance")

# DECIDE@IMPL tag F — [event] durability.
# Rationale: the in-memory [event] log is append-only with read-only records but
# dies with the process, so on its own it is not audit-ready after the run. A
# deployment that needs durability wires a JSONL file sink into the log; each
# appended record is mirrored to disk, flushed, one immutable line per record,
# with tags serialized in a fixed order. The default stays in-memory so tests
# need no filesystem. This provides DURABILITY; tamper-evidence at rest comes
# from the hash chain.
EVENT_DURABILITY: Final = (
    "in-memory by default; optional append-only JSONL file sink"
)

# DECIDE@IMPL tag F — write policy for the [event] log.
# Rationale: the [event] log is the audit trace (§9, §13). A selective-write
# policy could drop a record an auditor needs; the trusted artifact must keep
# every record. Selectivity, if ever wanted, belongs to [data], not [event].
EVENT_WRITE_POLICY: Final = "store-all"

# DECIDE@IMPL tag F — the open-tag registry beyond `domain`.
#
# The protocol fixes no vocabulary of open-tag keys: which keys exist beyond the
# mandatory `domain`, and what each means, is environment-specific and declared
# here. Protocol §9 sets a floor of at least three open tags per datum (one being
# `domain`), each describing a real dimension — a floor on honest description,
# not a quota to pad; a tag invented merely to reach the count, that does not
# describe the datum, fabricates data to fill a gap, which the loop forbids.
#
# For this host the registry is FREE-FORM: only `domain` is required (enforced at
# the tagging-gate); any other key is permitted so long as it is not a verdict.
OPEN_TAG_REGISTRY: Final = "free-form"

# Declared well-known keys for this host. Empty under the free-form choice. The
# shape is fixed so a deployment can fill it: key → human-readable definition.
OPEN_TAG_DEFINITIONS: Final[dict[str, str]] = {}

# DECIDE@IMPL tag F — store scope.
# Rationale: this host serves one agent. A private store MUST carry the
# resistance-retrieval channel, otherwise drift is certain (§10).
STORE_SCOPE: Final = "private"

# DECIDE@IMPL tag G — depth of the per-[event] context anchor.
# Rationale: each [event] anchors the *full* field-state of its cycle (not a
# minimal context-trace), so a third party can re-appraise an event under its
# original context with maximum fidelity (§8.5, §9). This trades storage cost for
# audit fidelity — the chosen trade for this host.
CONTEXT_ANCHOR_DEPTH: Final = "full-field-state"

# DECIDE@IMPL tag F — [event] log length policy and segmentation.
MAX_SEGMENT_BYTES: Final = 64 * 1024 * 1024
EVENT_LOG_SEGMENTATION: Final = (
    "daily segments `event-log-yyyymmdd.jsonl`, overflowing to `-002`, `-003`… "
    "when a segment would exceed MAX_SEGMENT_BYTES; records never split across "
    "files; the hash chain continues across segments"
)
# Rationale + law: the log itself has NO maximum length — records, once written,
# are never altered or removed (§9), so any "full → truncate" policy is flatly
# forbidden, and snapshots never license pruning pre-snapshot records. What IS
# managed is the single-file size: MAX_SEGMENT_BYTES (64 MiB — a tunable starting
# value, NOT derived; it bounds verify-time memory and keeps segments
# tooling-friendly) rotates to a new file. A closed segment is immutable and may
# be archived to cold storage (deployment-open, never deleted). An append failure
# (e.g. disk full) raises and halts the loop — a record is never dropped to keep
# running.

# DECIDE@IMPL tag F — durability sync policy of the persisted [event] log.
EVENT_SYNC_POLICY: Final = (
    "fsync per record (write-through): each appended line is flushed to disk "
    "before the write returns, so every record is durable the instant it is "
    "appended"
)
# Rationale (safe default, NOT derived): the sink fsyncs on every write, so no
# appended record is ever lost to a crash. A high-throughput deployment MAY batch
# the fsync to a cycle boundary, trading per-record durability for fewer syncs;
# that batching is deployment-open and deliberately not built here, so the
# default stays the one that loses nothing.

# DECIDE@IMPL tag F — tamper-evidence of the persisted [event] log.
EVENT_TAMPER_EVIDENCE: Final = (
    "sha256 hash chain over the JSONL sink lines: each line carries seq + prev + "
    "hash; verify_jsonl_sink detects any altered, removed, inserted, or reordered "
    "line; the chain resumes across restarts"
)
# Rationale + honest limits: sha256 via hashlib (stdlib, no dependency).
# Detection is relative to a trusted head — a party with full write access can
# rewrite the whole chain consistently, so a deployment anchors the sink's head()
# outside its own write reach. In-process tampering is out of scope by
# definition. This is NOT the §9 full-system commit/snapshot.

# DECIDE@IMPL — commit/snapshot cadence and retention (protocol §9: "the [event]
# log acts as a counter: after a set volume, a commit fires, snapshotting the
# entire system … into an immutable, content-addressed marker. Recovery is
# full-system. DECIDE@IMPL: events between commits; snapshots retained").

# A commit fires after this many SCARS since the last commit.
COMMIT_EVERY: Final = 9
# Rationale (tunable, NOT derived): the cadence counts scars, not all records —
# state changes most when collisions are digested. Because activity records carry
# entity ids, not full observation content, replay between commits is PARTIAL: a
# marker is a real restore point, not a mere accelerator — hence a dense-ish
# cadence. Two declared valves: a quiet stretch produces no automatic commit (an
# intended property of scar-rhythm), and the daemon exposes a manual commit() for
# out-of-loop triggers.

# How the marker/payload repo retains snapshots.
SNAPSHOTS_RETAINED: Final = "all (nothing is pruned)"
# If a deployment prunes payloads, it MUST keep at least this many newest
# restore points.
MIN_SNAPSHOTS_RETAINED: Final = 9
# Rationale (tunable, NOT derived): MARKERS are never pruned by anyone — they are
# the audit DAG (parent-linked; deleting one holes the fork history). Retention
# governs snapshot PAYLOADS only: this host keeps all; a pruning deployment must
# keep ≥ MIN_SNAPSHOTS_RETAINED newest payloads so the roll-back depth covers a
# reader's detection lag. A pruned payload's marker remains — auditable, just not
# restorable. No pruning machinery is implemented here (keep-all).

# DEVIATION from dil-core, declared (Plone, 2026-09-24): dil-arc3 also commits at
# the close of every cycle in which the agent wrote a datum, so every version of
# what it wrote — the mind's program above all — is in a snapshot, tied by
# its marker to its place in `[event]`. dil-core keeps the scar rhythm alone:
# for an agent that writes often, a snapshot per write is too heavy a cost.
# The learning mind writes every cycle, and adds data rather than revising one:
# a snapshot per write made each cycle slower than the last and a 400-cycle
# store 2 GB (LOG.md), so a run with it keeps the scar rhythm alone (Plone,
# 2026-09-27; `Daemon(commit_on_write=False)`).
COMMIT_CADENCE: Final = (
    "every COMMIT_EVERY scars, at a cycle boundary; and, unless the host turns it "
    "off, at the close of every cycle in which the agent wrote a datum (dil-arc3; "
    "off for the learning mind); manual commit() and a fork marker at recovery"
)

# DECIDE@IMPL tag H — the building of situations in `simulated` (§6.2, §9).
#
# The protocol fixes only that selection among situations is a comparison of FIT
# against the store, never a scored standard (INV-8). It leaves open how many
# situations are built per cycle and what "fit" concretely measures.

# How many situations the loop builds from the store per cycle when it
# forward-builds.
H_COUNT: Final = 3

# The floor a situation's fit must clear before the loop builds from it — the
# second half of attention (INV-7), over SITUATIONS rather than over entities.
#
# 0 by default, which is the behaviour the loop always had: anything the store
# supports at all is material. The field's `fitFloor` raises it, and a raised
# floor means the loop builds only from what it is strongly supported on.
#
# WHY ATTENTION GOES HERE AT T5 AND NOT AT THE EXPECTATION ITSELF. Two more
# obvious readings are both unsafe, and reading the code said so:
#
#   - Scaling `Expectation.confidence` by the field. That number is written into
#     `[event]`, and §13.4 reads it as the accumulation signature: the checker
#     FAILS a run where "confidence did not rise though recurrence climbed",
#     calling it the reloading signature (INV-5). A shrinking attention gain
#     would report a healthy accruing loop as a faked one.
#   - Skipping low-confidence entities at T5 so no expectation is formed. Then
#     no PredErr is formed either, and whatever resistance that return carried
#     goes unregistered — §8.2's definition of pure Mode-A, installed on purpose.
#
# Neither touches this floor: every entity still gets its expectation, every
# return still meets it, every mismatch is still registered, and `confidence`
# stays a pure function of accrual. What the field shapes is only which of those
# expectations the loop bothers to BUILD FORWARD from — the selection H_COUNT
# was already making, now with a floor under it as well as a ceiling over it.
FIT_FLOOR: Final = 0.0

# The field parameter that raises the fit floor (INV-7, down-channel).
FIT_FLOOR_PARAM: Final = "fitFloor"
# Rationale (tunable, NOT derived): a small fixed starting value — enough for a
# fit-comparison to have alternatives to weigh, not a derived optimum. The loop
# builds situations only where there is store material to build from; H_COUNT is
# a ceiling, not a quota.

FIT_MEASURE: Final = (
    "consistency with [data]: a situation fits better when the store more "
    "strongly supports its cast outcome (accumulated recurrence/confidence for "
    "that entity)"
)
# Rationale + INV-8 boundary: fit is measured AGAINST the store's own [data] (the
# yardstick), never a foreign standard and never a good/bad verdict — it is
# consistency, not scoring-for-truth. It selects WHICH situation carries, blended
# and re-weighted each cycle like GLOB-MOD contributions (INV-7), never frozen
# (INV-2). This selection is UPSTREAM of and separate from the appraisal step,
# whose valence still comes from the modulatory field (INV-8), so measuring fit
# against [data] does not make the appraisal self-scoring. A store that leans
# makes situations lean the same way; the loop cannot detect its own lean — that
# is Mode-B's job (§1.1, §8), not forward-building's.
