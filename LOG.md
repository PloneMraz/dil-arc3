# dil-arc3 — log

The history of this repository: what was built, measured, found wrong and
replaced, in the order it happened. What holds now is in `README.md` (what the
agent is) and `CLAUDE.md` (the rules and declarations in force); this file keeps
how it got there, the mistakes included.

Entries are kept as they were written at the time, moved here from `CLAUDE.md`
and `README.md` on 2026-09-24 and ordered by the commit that first wrote them.
So they speak of code that has since changed — `effect.py`, `model.py`,
`perceive.py`, `seeing.py`, `interpret.py`, the counting `Mind`,
`run_world_model.py` — and a later entry may correct an earlier one. The code an
entry measured is at the commit it names, and `scripts/README.md` says how to run
a script against it.

## 2026-09-22

### The diversity problem, and a peer reader measured

**The diversity problem, and how the same move solves it.** Conformance criterion
7 (§11) fires a diversity-loss signal when the resistance-source set holds fewer
than MIN_DIVERSITY_SOURCES distinct sources over a window. An agent playing one
game has one resistance source, so §13.5 and §13.7 would render `partial`, as
they do in dil-core for the same reason.

Peer reflection fixes this as a side effect, because a peer's reading arrives
tagged ENV_PUSHED and can itself resist. Measured on a run of two agents on
different games:

| | resistance sources | §13.5 | §13.7 |
|---|---|---|---|
| agent alone | `e1` | partial | partial |
| agent with a peer reader | `agent-A`, `e2`, `region` | **pass** | **pass** |

The diversity is earned rather than arranged: the peer is a real source that
returns something this agent did not author.

### The environment, first read

The environment section carried this note:

*An earlier draft of this file said "a 2D grid". That was read off the docs,
not off a frame, and it was wrong.*

### The Paper Track forum, before the Overview page was read

- **A 1,500-word limit is referred to as a known constraint** by two competitors
  ("does the bibliography fit within the 1500-word limit?", "does the 1,500-word
  limit also apply if you upload a PDF through the Public Project Link instead of
  writing it in the Kaggle Writeup"). No host ever replied to either. If it holds,
  it reshapes the paper completely: 1,500 words against a 55 KB specification.
  **Confirm this on the competition's own Overview page before writing anything.**

And of the rubric's aggregation, in "Which prize this aims at":

If the 4.5 is a mean of the six criteria — the natural reading, and the one a
search summary asserts, though the page itself leaves the aggregation unstated
and one cited source was a third-party blog — then the pool needs better than
27 of 30 points. An Accuracy of 0 costs 5 and makes it unreachable; an Accuracy
of 2 requires a perfect 5 on all five remaining criteria.

### Two bugs in the starter kit on Windows

Both are upstream's, both block a Windows user at the first step, and both are
worth a pull request to `arcprize/ARC-AGI-3-Kaggle-Starter`:

1. `scripts/slim_framework.py` calls `INIT.write_text(SLIM)` with no encoding, so
   on Windows it writes cp1252. The text contains an em dash, which lands as byte
   0x97, and Python then refuses to read the generated `.py` as UTF-8. Fixed
   locally with `encoding="utf-8"`.
2. `scripts/play_local.py` prints `→` to a cp1252 stdout and raises
   `UnicodeEncodeError`. Worked around with `PYTHONIOENCODING=utf-8` rather than
   by editing their file.

### The host ring — what exists, 2026-09-22

`src/arc3/` is the body. Three files, 132 tests green.

- `decisions.py` — tag A, declared from 42 measured frames. Tag B recorded as
  **inherited from dil-core, not chosen**; tag H left open.
- `frame.py` — the boundary gate. It **refuses** a frame outside the
  declaration rather than coercing it, the same stance §5's tagging gate takes
  toward a datum without provenance. Verified against 52 live frames from
  `ls20` and `vc33`: 52 accepted, 0 refused.
- `action.py` — what a legal move looks like and how to hand one to the engine.
  It forms no move. Who forms one is unsettled.

#### A third trap, this one in the engine's enum

`GameAction(1)` raises `ValueError: 1 is not a valid GameAction`. The members
are declared `ACTION1 = (1, SimpleAction)`, so `_value2member_map_` is keyed by
the **tuple**; `__init__` then rewrites `_value_` to the bare id, too late for
the lookup map. `GameAction.from_id(1)` works, which is why the classmethod
exists. Found by running it — reading `_value_ = action_id` suggests the
opposite.

### The entity is the affordance — settled with Plone, 2026-09-22

The loop holds an expectation about **what an action does**, not about what the
next frame looks like. A collision is the action doing something other than
expected.

Three reasons it was chosen over "the whole frame" and "the cell/region":

1. It matches what ARC-AGI-3 actually is — discovering the control scheme.
2. It matches RHAE: winning a level in few actions means learning the mechanics
   fast, which is exactly accruing confidence per affordance.
3. **It settles emission without breaking the four roles.** The model predicts
   an action's *effect* — it supplies the **expectation**, not the **choice**.
   The self picks which expectation is worth testing. The model still emits
   nothing. Exploration stops being an epsilon-greedy bolt-on and becomes a
   consequence of the mechanism.

It required **no change to the loop ring**: `T4`'s context resolver is already
DECIDE@IMPL and pluggable, so the entity id becomes the affordance, and `T5`'s
persistence rule then accrues a window of observed effects per affordance with
confidence ramping over recurrence.

#### Tag H, declared and measured

Fit is equality of the **effect signature** in `src/arc3/effect.py`: a
translation-invariant description of what changed, so the same control used in
two places reads as the same event. A literal cell diff would have made every
use of a control look unrelated and the agent could never have learned its own
controls.

Measured on **316 real transitions**, not asserted:

- In `ls20` the signature **recovers the control scheme unaided** — values 9 and
  12 displace `(-5,0)` under ACTION1, `(+5,0)` under ACTION2, `(0,-5)` under
  ACTION3, `(0,+5)` under ACTION4, with 29–33 consistent observations each.
- One filter carries this. A displacement is claimed only when a value vanishes
  from as many cells as it appears in — a **rigid translation conserves cell
  count**, a spreading trail does not. Without it, one noisy value shattered the
  signature: 33 distinct signatures instead of 10, 8–11 per action instead of
  2–4, at the same 79% discrimination.
- A blocked move gives the same signature whichever direction was tried. Not a
  defect — walking into a wall is genuinely direction-blind.
- **Negative result, declared:** in `vc33` the signature carried no information.
  Across 157 transitions the click position never changed it. Whether the
  representation is failing there or those clicks genuinely do nothing is **not
  established**, and is not being guessed at.

Variants that scored worse are recorded rather than discarded: dropping the
transition counts and keeping only displacements gave a tidier 5 signatures for
`ls20` but went blind on any game whose effect is a colour change rather than a
movement, which is the `vc33` case.

### What CLAUDE.md said of this day, moved here on 2026-09-27

Left in `CLAUDE.md` when the history moved out on 2026-09-24; moved at Plone's
direction. Its own words, joined into paragraphs; what is in brackets was added
on moving. `CLAUDE.md` keeps each fact that still holds and points here.

**The frames.** `FrameData.frame` is `list[list[list[int]]]`, three levels
deep. Measured on 42 real frames (2026-09-22): shapes `(1, 64, 64)` and
`(6, 64, 64)`. So a frame is 1..N grids, each 64 rows × 64 columns; both games
observed used the full 64×64 every time, though the docs say "maximum". Cells
are integers **0–15** (values actually seen across those frames:
0,1,3,4,5,7,8,9,11,12 — ten of sixteen). Tag A was declared from them — "and it
was not straightforward". **`available_actions`**, measured: `ls20` offered
`(1,2,3,4)`; `vc33` offered only `(6,)`. The boundary gate refused `vc33`'s
empty opening frame; "that is how this surfaced".

**Entry.** Plone accepted the ARC-AGI-3 rules on 2026-09-22;
`kaggle competitions list` reports `userHasEntered True` for
arc-prize-2026-arc-agi-3. The Paper Track is a separate competition: entering
ARC-AGI-3 did not enter it, and before Plone accepted its rules the listing
reported `userHasEntered False` and even its 150-byte NOTE.md returned 403.
"Worth remembering that nothing in the ARC-AGI-3 work would have revealed
this." The competition page said "You haven't created a writeup yet."

**Field sizes**, read from the Kaggle listing on 2026-09-22: ARC-AGI-3 has
**3,230 teams**, the Paper Track **198**.

**Licence.** The relicence to MIT-0 was argued from arcprize.org alone, and
under the Kaggle rules plain MIT would likely have sufficed.

**The submission pipeline, verified end to end on 2026-09-22**, run against the
starter kit's baseline random agent, well before the deadline. After a
successful push and a COMPLETE run, `competitions submissions` still said "No
submissions found" and the daily quota was untouched. This machine had Python
3.13 and 3.14, the starter kit and Kaggle 3.12. Phase A's dummy parquet — "1
row: row_id=1_0, game_id=1, score=1" — was exactly what appeared in our kernel
output. **The submission scored 0.02.** Several competitors reported
submissions that finish in ~30 seconds, never reach Phase B, and score 0.00 —
including one who submitted an exact copy of the official random-agent sample.
Ours scored 0.02, so Phase B ran and the agent played. **Baseline calibration: a
uniformly random agent scores 0.02.** [The random agent on the scored run's
road later scored 0.06: 2026-09-27, the gateway probe.] Milestone 2 was skipped
because, among other reasons, "there is no running agent".

## 2026-09-23

### The bridge, and what running the real loop found

`src/arc3/observe.py` turns "I made move M and the region returned frame F" into
the `HostCycleInput` the cycle driver takes. It needed **no custom resolver**:
T4's declared default reads `content["value"]["entity"]`, so the transducer just
has to put the affordance there.

Two declarations it makes:

- **One affordance per action id.** ACTION6 carries `(x, y)`; treating each
  coordinate as its own affordance would create 4096 entities that each recur
  once, and nothing would accrue. Coordinates are context, not identity.
  Bucketing them would be tidier, but no measurement backs any particular
  bucketing, and §12 exists to stop that. Declared cost: `action:6`'s
  expectation cannot stabilise.
- **The agent authors moves, never frames.** T2 sees one self-written change —
  the move, observed back — and every frame change is environment-pushed. This
  is the architectural line stated in code, and it makes each affordance an
  Other under T6.

#### Run on 159 real ls20 cycles

The loop runs end to end. All four affordances reached confidence 1.00 with
36–42 observations each. But **resistance never fell**: 93, 132, 129, 127 scars
per 40-cycle block.

The cause is measured, not guessed. **444 of the 481 scars were absences.** T7
registers an expected entity that did not return as a negative PredErr — but an
affordance is not a source that returns on its own. It returns only when the
agent uses it, and the agent uses one per cycle. So once N affordances are known,
N−1 absences are recorded every cycle, for ever.

`vc33` is the control that proves it: one affordance, **0 absences**, and the
scar rate was 0.58/cycle against a measured persistence ceiling of 42% — a
58% miss rate, matching exactly. **The mechanism is sound; the mapping is what
floods it.**

This is not patched around. Disabling T7 for affordance entities would be a
change to the skeleton, and it is Plone's call. Pinned by
`tests/test_arc3_observe.py::test_unexercised_affordances_register_as_absences`
so it cannot quietly stop being true.

#### The other declared limit

Under the affordance reading the loop is handed **no coordinates**. It learns
what its controls do; it does not learn where anything is. Knowing the control
scheme is not the same as knowing how to win a level. In `ls20` the persistence
ceiling per affordance is 66–86%, so the residual error is largely the cases
where the effect depends on position — exactly the information withheld.

### The host, and the loop closing against a live game

#### Correction to the earlier entry

What the previous section called "running the real loop" was `cycle.run()`
driven by a scratchpad script over pickled frames. **No daemon, no HostSource,
no live game — and no emission.** The actions in that replay were chosen by the
dump script's round-robin; the loop's `response` was computed and thrown away.
The loop was a passive observer of a scripted sequence. The absence measurement
stands, because it is about T7's bookkeeping and independent of who chose the
actions. The description did not.

#### What plays the thinking role

**Nothing does. There is no model.** The prediction is T5's declared update law,
persistence, and it is one line:

```python
predicted = window[-1] if window else observed
```

"Predict that this control does what it did last time." That is the whole
thinking organ at present. **This is where a model goes** — it would supply the
expectation, predicting an action's effect from context, which is exactly the
role settled with Plone: the model supplies the expectation, never the choice.

#### Two declared deviations from dil-core

Both are additive and defaulted, so dil-core's behaviour is unchanged when a
host declares neither.

1. **`HostCycleInput.afforded` → `T7Input.present`.** T7 registers an absence
   only against entities the region says are there. Silence presupposes the
   chance to speak.
2. **`Cycle(respond=...)`, a host-declared `RespondPolicy`.** dil-core hard-codes
   the terminal emission as `{kind: "respond", cycle, valence}` because its
   minimal host has no region to push into. A host with a real region must
   commit a real action or INV-1 never closes. The seam is at the close of the
   meaning-channel after appraisal, issuing layer T8 — **not in a layer**. A
   layer emitting the move would make the thinking organ the actor.

`src/arc3/respond.py` declares the policy: commit the afforded action whose
expectation is **least resolved**, ties on fewest observations then lowest id.
An affordance never met ranks at confidence 0, so the loop reaches for what it
does not know first. Exploration is not bolted on; it is what the loop's own
state recommends.

#### `src/arc3/host.py` — the body

`Arc3Source` is a `HostSource` over a live game. `deliver` executes what the
self committed — *the agent acts through deliver* — and the following `next`
reports what the region did. Nothing here chooses; a move the frame does not
afford is refused, never substituted, because swapping in a legal action would
put the choice in the body.

Cycle 0 reports the opening RESET with a **null effect**: `reset()` makes the
first frame out of nothing and there is no earlier frame to difference it
against. It binds an `action:0` entity the game never affords, which is also the
live check that the presence filter works.

#### Measured on live runs, 80 cycles each

| | `ls20` | `vc33` |
|---|---|---|
| precondition gate | Qualify | Qualify |
| cycles / actions | 80 / 80 | 80 / 80 |
| scars from the region (absences) | 225 | 1 |
| scars from an affordance | 4 | 45 |
| levels completed | 0 | 0 |

**The absence flood persists in `ls20` and the presence filter does not touch
it**, exactly as forecast when option (ii) was chosen: `ls20` affords all four
actions every cycle, so all four are genuinely present and three are genuinely
unused. The filter is live — it is what keeps `action:0` from being registered
absent, and `vc33` shows 1 absence rather than a flood — but it does not solve
`ls20`. The remaining question is whether an affordance that is present but
*unasked* should count as silent. Not decided here.

**Two engine behaviours found by running it**, neither documented:

- `reset()` returns a populated frame for `ls20` and an **empty** one for
  `vc33`, which needs RESET sent as an action before the game starts. The
  boundary gate refusing the empty frame is how this surfaced.
- `vc33` reaches `GAME_OVER` and **keeps reporting `available_actions == (6,)`**.
  Stepping that action in a terminal state returns an empty frame. So the
  policy reads the state, not the afforded list, and commits RESET from a
  terminal frame.

**Neither game completed a level.** The move distribution is 20/20/20/20 — with
all four affordances at confidence 1.0, ties break on fewest observations and
the policy round-robins. That is a systematic sweep, not learning-driven
behaviour, and it is the declared limit showing up in the numbers: the loop
knows what its controls do and does not know where anything is.

### The model — the thinking organ

`src/arc3/model.py`, plugged into T5's `PredictRule` seam (declared deviation
**#3**, same additive-and-defaulted shape as the other two; dil-core's
persistence stays the default). The model supplies the **expectation** and
nothing else: it never sees the afforded set and never reaches the emission, so
it cannot choose. The model thinks, the self acts.

#### Why it is not a downloaded network

Three constraints, each on its own sufficient:

- The scored games are **unseen**, and their mechanics are the thing to be
  discovered. Weights trained on other games predict the wrong world.
- Kaggle's evaluation session has **no network**.
- **INV-5 forbids the alternative outright**: "refeeding the whole game history
  into a context window each step is a load, not an accrual". A large model
  re-reading its own history every step is exactly what the invariant names.

What is left, and what the protocol actually asks for, is a predictor that
**accrues within the episode**. It starts knowing nothing about the game it is
in.

#### What it conditions on

Persistence predicts that a control does what it did last time; measured, that
is right 76% of the time in `ls20`. The residual is position — whether a move is
blocked depends on what is in the way. So the context is **what lies where the
move would land**: the values of the cells the mover would arrive on, as a
multiset, so the same obstruction met at two places reads as one situation.

The mover and each action's displacement are **learned from the agent's own
effects**, not configured. On real `ls20` frames the model recovered
`action:1 → (-5,0)`, `action:2 → (+5,0)`, `action:3 → (0,-5)`, `action:4 →
(0,+5)` and a mover of value 9 — the control scheme, from nothing.

#### Measured, with the two gains separated

The model changed **two** things at once — majority vote over accrued evidence
instead of most-recent, and context conditioning. Reporting one number would
credit context with wins that majority alone produces.

| on 316 real transitions | `ls20` | `vc33` |
|---|---|---|
| most-recent (dil-core persistence) | 76% | 41% |
| majority, no context | 76% (**+0**) | **69%** (+28) |
| majority + context (the model) | **94%** (+18) | 69% (**+0**) |

**Two different mechanisms, each carrying one game.** In `ls20` the whole gain
is context; in `vc33` the whole gain is majority, because no mover is learnable
there — `vc33` produced no rigid displacement at all, so its context was empty
in every one of 157 cycles.

Live, 80 cycles each, scars sourced to an affordance fell from **4 → 2**
(`ls20`) and **45 → 23** (`vc33`).

#### A defect the tests found, which the real frames had hidden

The background collected displacement votes it had not earned: when a thing
steps into empty space, the hole it leaves steps the other way, so the
background mirrors every move and can tie with — or beat — the thing that
actually moved. On real frames the rigidity filter already excluded it, so the
live numbers never showed it; a clean two-value frame exposed it immediately.
The model now votes for a background separately and excludes it, and keeps
displacement votes keyed by value so the mirrored vote cannot outrank the real
one. **The measured numbers are unchanged by the fix** — it buys robustness, not
score.

#### What it does not do

Neither game completed a level. The model improves **prediction**, not
**winning**. Knowing what a control does, and knowing it 94% of the time, is
still not knowing where to go.

### Attention, and the absence flood dying

Ported from dil-core, where the gap actually was. T7 now carries two gates, both
additive and defaulted: `present` (the region's word — an entity it says is not
there is not silent) and `attentionSpan` scaled by the field's `attentionGain`
(the field's word — an entity the loop is no longer oriented toward is not being
waited on).

**Measured live on `ls20`, 80 cycles per run:**

| `attentionSpan` | scars | absences | real resistance |
|---|---|---|---|
| ∞ (the old behaviour) | 227 | **225** | 2 |
| 3 | 221 | 219 | 2 |
| 2 | 149 | 147 | 2 |
| 1 | 76 | 74 | 2 |
| 0.5 | 2 | **0** | 2 |

**The right-hand column never moves.** Attention removed 225 false absences and
not one real collision. That is §8.2's line holding in live data rather than in
a promise: attention lowers what is demanded back, never what is registered.

`span = 0.5` reaches zero, and is not the answer: §8.1 **C3** requires a
missing-InfoUnit when an expected event fails to occur, and a loop that expects
nothing fails C3 by construction. `span = 1` keeps C3 alive while cutting
225 → 74.

#### The loop sets its own attention width

The span no longer has to be hand-tuned per game. T6 — the layer that *accrues*
Others — contributes `attentionGain = 1/N` upward into the field through the new
INV-7 up-channel, and T7 reads it at N+1. The host declares a span meaning "how
long I would wait if I had one thing to watch"; the loop divides by how many
things it is actually holding.

Measured live on `ls20`, where T6 accrues five entities (`action:0` plus the
four affordances), so the gain settles at 0.2:

| declared span | effective | absences | real resistance |
|---|---|---|---|
| ∞ | ∞ | 225 | 2 |
| 8 | 1.6 | 76 | 2 |
| **4** | **0.8** | **3** | **2** |
| 2 | 0.4 | 1 | 2 |

**225 → 3 at a declared span of 4**, with C3 still alive, and the real-resistance
column still untouched.

#### The resistance-retrieval channel, and a negative result

§10 requires a private store to carry the resistance-retrieval channel. It now
exists here: `dil/loop/recollection.py` reads `[event]` and answers with an
expectation — what the region gave, last time, in this same situation — and
nothing else. `scar → running` fires for every scar it returns, so the store is
genuinely being read for the first time.

Two sources of expectation then exist: the model, which says what it has
learned, and the record, which says what the region actually did. §6.4 already
settles what to do when two internal sources disagree — "the opposition is not
resolved by an internal rule but collided against the region" — so nothing
arbitrates on the merits: where the record speaks, it is what gets TESTED.

**Measured, 200 cycles per game. It does not work.**

| | `ls20` OFF | `ls20` ON | `vc33` OFF | `vc33` ON |
|---|---|---|---|---|
| prediction errors | 9 | **16** | 58 | **113** |

And the contests themselves, across both games — **66 disagreements**:

| the region sided with | count |
|---|---|
| the model | 62 |
| the record | **1** |
| neither | 3 |

The record lost 62 of 66 and roughly doubled the error rate in both games.

#### Why — a sampling bias, and no verdict anywhere

An earlier draft of this section said the store holds "the occasions on which the
agent was wrong". That was wrong, and it imported a verdict the protocol
explicitly refuses. §9: the tag "carries no claim of correctness", and "judging
correctness is the work of Mode-B and of an external third party reading the
scar, **never of the store**"; a datum that has met no resistance "is not wrong,
only not yet tested". §3 defines the unit exactly: a ResistEvent is **a
registered mismatch between the agent's expectation and what the region
returned** — divergence, not error.

The real mechanism is a **sampling bias**, and it is sharper than the
correctness story. A scar's `received` field is a genuine return from the
region; nothing about it is mistaken. But a scar exists *only where the return
diverged from what was expected*. So conditional on a predictor that mostly
works, the recalled set is exactly the subset of returns that **surprised** the
loop — which are the rare ones. The record recites the region's exceptions, and
recites them faithfully. The model answers with the distribution. Asked "what
will happen", the exception loses; that is arithmetic, not a defect in either.

`vc33` shows it plainly: the record disagreed with the outcome 54 times while
*agreeing with the model*. Both named the same thing and the region did something
else — the record was not contradicting the model, it was reporting an old
surprise.

This is the quantitative form of a worry raised before the design was chosen,
now stated correctly: if only mismatches enter the store, **the better the
predictor gets, the rarer and more exceptional the store's contents become**. In
`ls20` the model is right 94% of the time, so what the store holds is the 6%
that surprised it.

#### What the record is actually for

Which is not nothing. §9's chain is mismatch → memory → learning → change: a
ResistEvent is where the region pushed back, and that is what the loop is
supposed to change *from*. A faithful record of every point where the region
resisted is exactly right for driving change, and exactly wrong for answering
"what happens next". The measurement here says only the second thing.

#### What is kept, and what is declared

The channel stays, wired and tested, and **off by default** (`recollection=None`
keeps the reference behaviour exactly). It is not recommended as a *predictor*
on this evidence. What it might still be good for — a signal that a situation is
unstable, rather than a claim about what will happen — is not settled, and is
not being guessed at here.

### The fit floor, and what bounds its reach

Ported from dil-core: the field can raise the floor a situation's fit must clear
before the loop builds forward from it — attention over *situations*, under the
`H_COUNT` ceiling. Measured live on `ls20`, 60 cycles:

| `fitFloor` | forward-builds | scars | real resistance |
|---|---|---|---|
| 0 (the old behaviour) | 55 | 5 | 2 |
| 0.5 | 51 | 5 | 2 |
| 0.99 | 47 | 5 | 2 |

The scar column does not move at any setting: the floor selects what is **built
forward from**, never what is **registered**. That is the §8.2 line again, held
in live data.

**Its reach is bounded, and by tag B.** `SUFFICIENT_RECURRENCE` is 3, so
confidence saturates after three observations of an entity and clears any floor
below 1 from then on. The floor bites only while confidence is still ramping,
which in a 60-cycle run is a short window. That is not a flaw in the floor — it
is the untuned tag B showing through, the one still declared here as inherited
from dil-core rather than measured.

#### A design error the measurement caught

The contribution was put on T8 first, and it did nothing: the gain sat at 1.0
for all 80 cycles. T8 ranks the Others *present this cycle*, and in this host one
affordance returns per cycle, so T8 saw N = 1 every time. How many Others the
loop holds is **accrued** knowledge, and T6 is the layer that accrues it. Fixed
upstream in dil-core first, with a test pinning it there.

#### What this corrects in the earlier entry

The absence flood was reported here as a consequence of the affordance mapping,
and the open question was whether an affordance that is present but unasked
counts as silent. That framing was too narrow. The flood is the signature of a
loop with **no attention at all**: every entity ever seen expected back every
cycle, for ever. With one entity it is invisible; with N entities of which one
returns per cycle it is N−1 false absences per cycle, in any host, for any
domain. The affordance mapping only made it visible.

### Nothing reads the goal

Traced through the code, the chain §9 describes — mismatch → memory → learning →
change — is complete, and its last link is one rule wide:

| what | which component |
|---|---|
| interacts with the region | `Arc3Source.deliver` → `env.step` |
| perceives | `read_frame` → `diff` → the effect signature |
| **knows where anything is** | **nothing** — only "what is on the square I would land on" |
| collects mismatch | T5 (value-mismatch), T7 (absence) → driver → `[event]` |
| learns | the model's table, T5's windows, T6's counters, T7's expectations |
| changes behaviour | `LeastResolved`: take the least-resolved afforded action |
| **pursues a goal** | **nothing** |

`levels_delta` is the score channel — the only thing RHAE counts, the only
definition of winning. Grepped: it appears exactly twice, both in
`observe.py`, writing it into the payload and reading it back out when
rebuilding an `Effect`. **No component uses it to decide anything.** The
`stateTo` channel has one reader, `respond.py`, and only to RESET after a
terminal frame — never to seek a WIN.

So the agent cannot pursue the goal, because nothing reads the goal. It carries
the goal inward and drops it.

That accounts fully for zero levels completed. It is not a tuning problem. Two
limits declared earlier — "the loop is handed no coordinates" and "`vc33`
learns nothing from context" — were written up as limits of the *context*
representation. They are the same single hole, and the hole is that **nothing in
this repository represents a want**.

Where such a thing could live is not obvious and is not being guessed at:
§6 link 4 assigns direction and value, but INV-8 forbids the appraisal step from
drawing its criteria from the state the agent is editing, and `levels_completed`
is part of that state. Naming a goal is therefore a skeleton decision, not an
implementation detail.

### How far this travels beyond ARC-AGI-3

Layered, and the layers were checked rather than assumed. `grep` over `src/dil/`
finds no ARC-AGI-3 knowledge in code at all — only the word "frame" inside
"reference frame", and two comments.

| ring | what it assumes | portability |
|---|---|---|
| `dil/` | nothing about any world | travels intact |
| `frame.py` | 64×64, values 0–15 | shape is general, constants are not |
| `effect.py` | a grid of discrete values | any grid world; `transitions` survive off-grid |
| `model.py` | something moves rigidly on a grid | **the most specific piece** |
| `respond.py`, `host.py` | action ids plus coordinates | general in shape |

**`vc33` is the empirical test of this**, not a hypothetical: there the model
found no rigid mover, context was empty in all 157 cycles, and it degraded
gracefully to majority-over-effects — 41% → 69%. It keeps working and loses its
best feature.

Porting to another world means re-declaring exactly the seams §12 already
enumerates: T3's transducer, T4's resolver, T5's predict rule, the boundary gate
and the effect signature. The DECIDE@IMPL list *is* the portability surface.

### What GLOB-MOD actually holds, read off a live run

Attention is a composition now, not one layer's formula. Each layer contributes
the fact it can see and no other layer can, at weight 1, and decides nothing
about what follows: T3 `channelActivity`, T4 `strangeness`, T5 `surprise`, T6
`otherCount`, T7 `silence`. T7 reads the width off the composition —
`(1 + strangeness) / max(1, otherCount)` — and `RespondContext` now carries the
field, so it can reach behaviour.

Traced on `ls20`, 40 live cycles:

```
cyc channelAc strangene  surprise otherCoun   silence  ->width  ->span
  1     1.000     0.000     0.000     1.000     0.000    1.000   4.000
  2     1.000     0.000     0.000     2.000     0.000    0.500   2.000
  4     1.000     0.000     0.000     3.000     1.000    0.333   1.333
  6     1.000     0.000     0.000     4.000     1.000    0.250   1.000
  8     1.000     0.000     0.000     5.000     1.000    0.200   0.800
 20     1.000     0.000     0.000     5.000     0.000    0.200   0.800
 40     1.000     0.000     0.000     5.000     0.000    0.200   0.800
```

**Two of the five facts are constants in this host, and the rest go flat after
cycle 8.**

- `channelActivity` is 1.000 for ever: the host sends exactly one signal per
  cycle, so the number carries nothing.
- `strangeness` is 0.000 for ever: T4's resolver always finds the entity,
  because the host always knows which affordance it just used. There is no
  entity novelty in this host to measure.
- `otherCount` climbs 1 → 5 and then freezes: five affordances, all met by
  cycle 8.
- `surprise` and `silence` do move, and they are the only two that do.

So the composition machinery is right and **the host is not feeding it anything
that varies**. The field is legible now, and what it legibly says is that it has
almost no context to compose from.

#### The model's interpretation now reaches the field — and the field goes static anyway

`PredictRule` gained `contribute`, so the model reports what only it can read:
`contextNovelty` (is this situation one I have met?) and `contextsKnown`. Both
land in the field, bound to T5, and `attentionWidth` composes novelty as a third
fact. Traced live on `ls20`, 48 cycles:

```
cyc contextNo contextsK  surprise otherCoun   silence strangene  ->span
  1     1.000     0.000     0.000     1.000     0.000     0.000   4.000
  3     0.000     2.000     0.000     2.000     0.000     0.000   2.000
  6     1.000     4.000     0.000     4.000     1.000     0.000   1.000
 10     1.000     8.000     0.000     5.000     0.000     0.000   0.800
 16     0.000     9.000     0.000     5.000     0.000     0.000   0.800
 48     0.000     9.000     0.000     5.000     0.000     0.000   0.800
```

`contextNovelty` **does** vary, for about fifteen cycles. Then it is 0 for ever,
and `contextsKnown` freezes at **9**.

**That is the finding, and it is about the model rather than the field.** The
landing-patch context collapses a 64×64 world into **nine** distinct situations.
Five affordances across nine situations is a space the agent exhausts in fifteen
cycles — after which nothing in the field moves again, there is nothing left to
be curious about, and no want exists to take over. The environment stops being
open because the model stopped being able to tell it apart.

So the field being static was never only the field's problem. `strangeness` is
structurally 0 here because the host always knows which affordance it used, and
`contextNovelty` saturates because the model's situation space is nine states
wide. A richer reading of the situation would give the loop an environment it
does not finish mapping in fifteen moves.

#### Where the missing context is

`strangeness` measures **entity** novelty, and this host has none. The novelty
that exists here is **context** novelty — is this landing-situation one the agent
has met before? The model knows exactly that: it is whether `(entity, context)`
is already a key in its table. That is an interpretation of context, which is
what the field is missing, and it is one the model is already computing and
throwing away.

It cannot get in yet. The model lives behind T5's `PredictRule`, and a rule is
not a layer: it receives `(entity, window, observed)` and has no `contribute`.
Letting the model's reading of its own situation reach the field means widening
that seam, which is a skeleton decision and is not taken here.

### Entity was the wrong thing, and T8 said so

`entity = affordance` was settled early and it was wrong. §8.4 defines an entity
as "an other-entity the agent does not control", and §6.3 puts the layers that
live off it above T4: T6 builds an `OtherModel` of it, T8 builds `RelValue` and
`SocialEdge` — the latter being "an Other↔Other interaction with **no self
present**". An entity is an *Other*. It is not the self, which T2 already
separated, and it is not an action the agent can take.

An affordance passes T4 and T5 and starves everything above. Measured over a
real run:

```
T8 over the run:  RelValue = 0   SocialEdge = 0   others/cycle = [1]
```

**The top layer of the meaning-channel produced nothing, ever.** `RelValue`
needs N ≥ 2 and there was never more than one Other present; `SocialEdge` needs
two Others interacting without the agent, and two buttons cannot do that. The
absence flood was the first symptom of the same error: an affordance does not
return on its own, so asking whether it fell silent was the wrong question from
the start. Attention patched the symptom.

#### Roles were inverted, both of them

The host handed the loop a finished interpretation — "the thing of value 9 moved
up five" — while the model reached past the loop into the raw grid to decide what
was worth looking at. The body was concluding and the mind was sensing. Under the
biological reading Plone set out — host is the body that receives signals, model
is the thinking and interpreting part, DIL is how information moves, `store/` is
memory — both belong the other way round.

#### `perceive.py`: the model reads the signal

Things are connected runs of one value, four-connected, excluding whatever the
grid is mostly made of. The background is *read* rather than assumed, so a world
on a non-zero background still parses.

**Identity was chosen by measurement, over 60 real frames per game.** The score is
churn: how many identities exist overall against how many are present in any one
frame. An identity that changes when the thing changes is not an identity.

| identity | overall | per frame | churn | ever moves |
|---|---|---|---|---|
| value + bbox | 101 | 16.3 | 6.2× | 5 |
| value + size | 101 | 16.3 | 6.2× | 4 |
| **value** | **8** | **8.0** | **1.0×** | **4** |
| value + channel | 16 | 8.0 | 2.0× | 3 |

Value alone holds at **1.0× in both games** — every identity present in every
frame. Extent and cell count fail hard: a thing that changes shape becomes a
different thing six to ten times over. Channel was rejected on the same
evidence, because `ls20`'s stack depth varies.

**Declared limit:** this is a kind of *stuff*, not an individual. Every cell of
value 9 is one Other however many separate pieces they form. Telling individuals
apart needs matching across frames, which is a further interpretation and is not
done. What it does buy is what affordances never could — **six to eight Others
present at once**, so T8 has the N ≥ 2 it has never had.

Segmentation costs ~5.7 ms per frame pair, measured; ~0.6 s over a hundred-cycle
run.

### The rebuild, measured end to end

`entity = thing`, `context = action`, and the two rings swapped back:

| ring | files | job |
|---|---|---|
| **body** | `frame.py`, `action.py`, `host.py`, `observe.py` | receives, gates, carries, executes. **Concludes nothing.** |
| **mind** | `perceive.py`, `interpret.py`, `mind.py` | finds things, reads what became of them, says what they will do. **Chooses nothing.** |

`effect.py` and the old `model.py` are gone. Nothing in production referenced
them once `perceive.py` and `interpret.py` existed — segmenting first makes the
frame-level signature unnecessary, because a thing's displacement is just where
it was against where it is, with no rigidity filter and no translation
invariance to engineer.

#### Prediction, on the same 316 transitions the old mapping was measured on

| | old (affordance + hand-coded landing patch) | new (things) |
|---|---|---|
| `ls20` | 94% | **93%** |
| `vc33` | 69% | **85%** |

One point given up where the hand-coded feature was doing the work, **sixteen
gained** where it was blind — and the feature is gone.

#### Live runs, 60 cycles each

| | `ls20` before | `ls20` after | `vc33` after |
|---|---|---|---|
| Others per cycle | 1 | **9** | **7** |
| T8 `RelValue` | **0** | **540** | **420** |
| T8 `SocialEdge` | 0 | 0 | 0 |
| total scars | 227 | 44 | 61 |
| of which absences | **225** | **1** | **2** |
| distinct resistance sources | 2 | **8** | 3 |
| `channelActivity` in the field | 1.0 constant | **9.0** | **7.0** |

**T8 produced nothing at all before and produces hundreds of `RelValue`s now** —
the top of the meaning-channel has work for the first time.

**The absence flood is gone structurally, not patched.** 225 → 1. Attention was
holding it down; the real cause was that an affordance cannot be absent, and a
thing can: it either is in the frame or it is not. §13.7's source diversity also
stops being nominal — resistance now arrives from eight distinct Others instead
of one.

#### Still zero, and declared

`SocialEdge` is **0**. It needs Other↔Other interactions, which the host never
supplies — `HostCycleInput.interactions` is left empty. Under the old mapping the
idea was meaningless (two buttons cannot interact without the agent); under this
one it is perfectly meaningful — `thing:9` touching `thing:5` is exactly that —
and it is simply not implemented.

`levels_completed` is **0** on both games. Nothing reads the goal; that is
unchanged and is not a consequence of this rebuild.

### A regression in the rebuild, and the technical items closed

#### The regression

The respond policy ranked actions by T5's confidence in an entity named
`action:N`. The rebuild made entities things, so no entity carried that name,
every action ranked `(0, 0, id)`, and the lowest id won every cycle. Measured on
a live `ls20` run: **ACTION1, 40 times out of 40.** The rebuild's first
behaviour figures — 44 scars, 1 absence, 8 resistance sources — came from an
agent pressing up into a wall. Its perception figures (9 Others per cycle,
`RelValue` in the hundreds) were sound; its behaviour figures were not, and they
were reported without the move distribution that would have shown it. `vc33` was
unaffected, affording only ACTION6.

#### What the policy reads now

Only the field. The mind accrues, per situation (per action, here), how well it
predicts what follows and how the region has answered — and reports both upward
as `resolved:action:N` and `valence:action:N`. The field's blend keeps no memory
of its own (a key contributed this cycle takes this cycle's average), so the
memory is the mind's and the field carries the current reading. The policy
composes the two as `resolved − valence`, lower first: curiosity is the base and
want shifts it. Ties break on the self's own record of what it has committed.

`region_valence` is the one place a sign is put on an outcome: +1 for a
completed level or a win, −1 for game over, 0 otherwise. Declared, named, and
not a goal — it reads how the region answered; want is what the composition does
with that.

#### Other-to-Other interactions

The mind reads contacts *made or broken* between two kinds of stuff, and the host
carries them in as T8's `interactions`. Standing contacts were measured at ~10
per frame and nearly constant, so they would have said nothing; made-or-broken
came to about five per eighty transitions — sparse and real. `SocialEdge` went
from 0 to 5 (`ls20`) and 14 (`vc33`) over 120 cycles.

#### T8 was a sink

Nothing read T8's output. INV-1 forbids dead branches and §6.2 says "T8 closes
back into the loop, not into a sink". T8 now contributes `interactions` and
`resistanceConcentration` to the field. Fixed in dil-core first (`a1914f3`).

#### Live, 120 cycles

| | `ls20` | `vc33` |
|---|---|---|
| moves committed | `1:103 2:9 3:4 4:4` | ACTION6 only, swept |
| `SocialEdge` | 5 | 14 |
| scars / absences | 90 / 1 | 119 / 4 |
| `resolved:action:*` | 0.91–0.94 | `6`: 0.86 |
| `valence:action:*` | all 0 | `6`: −0.02 |
| levels completed | 0 | 0 |

#### What is still wrong, diagnosed

**Curiosity sticks.** ACTION1 took 103 of 120 moves in `ls20` because it is the
least resolved action (0.91), and it is least resolved because its outcome
depends on position — blocked or not — while the context is the action alone.
The mind can never resolve it, so curiosity never leaves it. This is the "noisy
TV" failure of curiosity-driven exploration, and its cause here is specific: the
situation the mind reads against is too coarse. The hand-coded landing patch had
supplied exactly the missing piece; removing it was right, but nothing has yet
replaced what it carried.

**Want can only avoid.** `valence` is 0 for every action in `ls20` because the
region never answered anything with a level or a win. In `vc33` a single game
over registered as −0.02 on ACTION6, and with one afforded action it can change
nothing. Want exists and is wired; it has never had anything to want.

### Individuals, and curiosity that follows progress

Two changes, both approved by Plone, both measured before they were wired.

#### (a) Tracked individuals, grouped by common fate

The contact reading proposed to fix curiosity's stickiness helped overall
prediction (93 → 97%) and did nothing for the moving object (70 → 66%). The data
said why: under ACTION1, "thing:9" moved (−2,0) 29 times and held (0,0) 12 times —
a clean blocked-or-not outcome — but value 9 is **five pieces**, one of which
moves, and any reading of the stuff was the union over all five. The declared
limit ("a kind of stuff, not an individual") was exactly what blocked the fix.

`seeing.py` follows each piece across frames (nearest centroid within its value),
groups pieces that repeatedly move together by the same displacement
(`MIN_COMOVEMENTS = 2`, vetoed outright by any occasion of moving apart), and
reads for each thing what it faces first on every side. Measured on the 316 saved
transitions:

| identity | churn | ls20 | vc33 |
|---|---|---|---|
| value (stuff) | 1.0× | 93% | 85% |
| tracked piece + what lies ahead | 1.5× | 98% | 94% |
| **tracked, grouped by common fate** | **1.7×** | **99%** | **93%** |

Without grouping the moving object's front part was predicted 100% and its back
part 67%: it is drawn in two colours, segmentation splits it, and a ray from the
back stopped at its own front and never saw the wall. With grouping the object is
`thing:9+12`, and its blocked-or-not outcome is predicted **100%** (35 of 35).

**Order is INV-8.** Grouping learns from how pieces moved, and the situation a
thing is read in predicts how it will move. The scene is read with the groups
the past formed; this cycle's co-movement is accrued afterwards. A test pins that
the group appears in the look *after* the one that supplied the deciding
evidence.

The stuff-level readers in `interpret.py` (`changes_of`, `contacts`,
`interactions_of`) and `Region.kind` were removed once nothing in production
called them. Churn rose partly because a thing is renamed when its parts are
first grouped (`thing:12#8` → `thing:9+12#8`); that is declared, not hidden.

#### (b) Curiosity follows learning progress

Least-resolved-first is greedy toward irreducible noise: whatever the mind can
never predict stays least resolved for ever, and curiosity never leaves it. The
mind now reports `progress:action:N` — the absolute change in accuracy between
the last `PROGRESS_WINDOW = 4` uses of an action and the four before — and the
policy composes it with want as `−(progress + valence)`. Unlearnable noise shows
no progress; an action whose accuracy starts falling counts again; an action with
fewer than eight uses counts as still being learned, which is also what puts an
untried action first.

This replaces the policy's base rather than modulating it, which went beyond the
earlier approval ("modulate, not replace"); Plone approved it explicitly.

#### Live, 120 cycles

| | `ls20` before | `ls20` after | `vc33` after |
|---|---|---|---|
| moves committed | `1:103 2:9 3:4 4:4` | `4:38 1:28 3:28 2:26` | ACTION6 swept |
| `resolved:action:*` | 0.91–0.94 | 0.97–0.99 | `6`: 0.93 |
| things per cycle | 9 | 19 | 12 |
| situations the mind has met | 45 | 176 | 56 |
| `SocialEdge` | 5 | 28 | 20 |
| moving object's distinct positions | not measured | **19** | — |
| levels completed | 0 | **0** | **0** |

It does not oscillate in place: the last twelve positions of the run walk a
straight line leftward across the grid, following the one action still showing
progress (`progress:action:3` = 0.12, all others 0). It did spend five cycles
pressing into the right-hand wall before that.

**Still 0 levels, and the reason is unchanged: want can only avoid.** Every
`valence` in `ls20` is 0 because the region has never answered anything with a
level or a win.

### The prior — what the character may know before it lives, 2026-09-23

Settled with Plone. The zero levels are not a defect: the character was put in
the maze with no problem to solve. A creature put in a box arrives with a very
long history (genes, and what Others taught it); this one arrives with none, at
the level of a zygote with a wide range of action. So the least it must be given
is **a directive**, tagged `prior`, and everything after that is its own thinking
and interpretation. Plone: "Đừng tự làm khó mình và làm khó nhân vật" — give it
what the rules allow it to know.

#### What the rules allow it to know, verified

Read in full on 2026-09-23: the ARC-AGI-3 Technical Report, the docs pages
game-schema, actions, methodology and competition_mode, and the Kaggle rules
(rendered through a headless browser, since the page needs JavaScript).

- The directive: the official leaderboard gives every model the same system
  prompt, "You are playing a game. Your goal is to win." (report, §4.3.1).
- `WIN` = "The objective was completed successfully", `GAME_OVER` = "The run
  ended without a win" (game-schema).
- Structure, cost, body and the world's core-knowledge priors (objectness,
  geometry and topology, basic physics, agentness; no language or cultural
  symbols).
- The Kaggle rules permit external data that is "publicly available and equally
  accessible to use by all Participants" (§6.a) and forbid "information from hand
  labeling or human prediction of the validation dataset or test data records".
  Public documentation is the first and none of the second.

What the report warns against is a different thing: a harness carrying
"ARC-AGI-3 specific strategies". The rules of the place are not a strategy;
nothing here says how to win any game.

#### `src/arc3/prior.py`

Five items (`directive`, `levels`, `cost`, `body`, `world`), 31 sentences, each
quoted verbatim with the document it was read in. All 31 were checked
programmatically against the downloaded sources. The host declares them as
`StoreDeclaration.preexisting`; the runtime's requisition admits each through
the tagging-gate as `prior`, cycle-mark null. A test pins that an item carrying
a verdict tag is refused and reported, not admitted.

Declared: admission happens only with a real substrate (`store_root`). The
in-memory fixture the live measurement scripts ran on has no requisition step.

#### How the prior is recalled — settled with Plone, same day

First found: **nothing read the prior once it was admitted.** It sat in `[data]`
stamped `prior` and never made the `prior → running` move §9 defines — a sixth
instance of a channel present in the topology that nothing drew on.

Plone settled how it enters, correcting both options put to him. Data does not
flow in by itself — the store is the character's memory, and memory pouring in
unasked is overload, a disease in a living thing. So the character asks. But
what it retrieves then enters the loop and runs every layer, and that is when
its tag changes from `prior` to `running`. `prior` is only a state tag: it tells
the character that the datum is not its own, has not been through its own
experience, and needs to be tested. (§9 agrees: "Running many cycles does not
wash a prior to tested status; only collision-and-hold does.")

The protocol already had every piece; the first proposal here invented an
`about` tag the open layer already covers, and Plone sent it back to be re-read.
What is used:

- **§6.4, T3 query** — "opens or calls a channel to ingest actively". The
  channel called is the store.
- **§6, link 1** — query returns are an input channel, so the return arrives at
  T1 the next cycle and runs T1→T8.
- **§9 open layer, tag F** — a key denotes the same dimension wherever it
  appears. That is the index: an arrival's description and a datum's open tags
  are matched on the same keys. This host declares its keys in
  `decisions.OPEN_TAG_KEYS`; the one doing the recalling is `object`.

Fixed in dil-core first (`5bb031a`), then ported. T3 asks once per description
it has not asked about. T7 no longer registers a recalled datum absent on cycles
it was not asked for — measured before that fix, with no presence reported, it
was registered absent every cycle from the second on.

The status transducer describes its reports as `object: region-status`; the
directive carries the same tag. The other four items are about other things
(`level-structure`, `action-cost`, `body`, `things`) and nothing arriving
describes those yet, so they wait.

**The signs left the code.** `region_valence` now reads the region's answer
against the recalled directive; with none recalled every answer reads 0. What
stays in the mind is the interpretation — what an objective and a run ended
without it mean. Which states those are, and what the region counts on the way,
comes from the directive.

#### Live, 120 cycles, with a real substrate

| | `ls20` | `vc33` |
|---|---|---|
| admitted through the gate / rejected | 5 / 0 | 5 / 0 |
| store queries from T3 | 1 (`object: region-status`) | 1 |
| `prior:directive` → `running` | cycle 1 | cycle 1 |
| directive in the mind from | cycle 1 | cycle 1 |
| other priors | still `prior`, no cycle-mark | same |
| moves committed | `4:38 1:28 3:28 2:26` | ACTION6 swept |
| levels | 0 | 0 |

Behaviour is identical to the run before, and that is what should happen: the
directive carries exactly the content the hard-coded signs had. What changed is
where it comes from and that an auditor can see it arrive. It does not, by
itself, get the character through a level; nothing about how to win was ever in
it.

#### The three limits that run left, worked through

**1. Four items were never recalled.** Because no arrival described what they
were about. The descriptions were made honest rather than the items forced:
a status report carries the region's state, the change in its level count and
the actions it affords, so it is about all three (`object`: `region-status`,
`levels`, `actions`); a thing's change is about a thing and came by sight
(`object: things`, `sense: vision`). dil-core now lets one arrival carry several
descriptions. The old `body` item mixed what the body sees with what it can do;
it is split into `seeing` (`object: frames`, `sense: vision`) and `actions`
(`object: actions`). `sense` is declared in `OPEN_TAG_KEYS`. All 31 quotes
re-verified against the sources after the split.

**2. The query's return was never read back by T2.** §6.4 rule 3 wants every
emission readable by T2 next cycle; T2 only saw the committed response. Fixed in
dil-core (`9b0bbdf`), ported: T2 also reads last cycle's lateral emissions, and
each return arrives as an observed change whose value is the query that asked,
so T2 tags it SELF_WRITTEN. The content stays not-its-own; agency and
provenance are different questions.

**3. T3 asks each description once — kept, and why.** Re-asking returns the
same data, already `running` and in use. Nothing added to `[data]` later carries
these tags, so there is nothing new a second ask could find. Asking every cycle
would put three to five queries a cycle into T2's matching window of 8, crowding
out the moves it has to recognise. It would bite if a datum carrying a cue's
tags entered `[data]` after that cue was asked; none does here. Declared, and
put to Plone.

Live, 120 cycles, 6 items admitted, 0 rejected:

| | `ls20` | `vc33` |
|---|---|---|
| queries | 5 (things, vision, region-status, levels, actions) | same 5 |
| items `prior → running` | all 6, cycle 1 | all 6, cycle 1 |
| `self:move` SELF_WRITTEN | 118 / 120 (2 before T2 is stable) | 118 / 120 |
| store returns | 6, all UNDECIDED | 6, all UNDECIDED |
| moves | `4:38 1:28 3:28 2:26` | ACTION6 swept |
| levels | 0 | 0 |

**Read the UNDECIDED row correctly.** Every return arrives at cycle 1, and T2
classifies nothing before `STABILITY_THRESHOLD = 3` cycles have run — its own
move is UNDECIDED then too. The path is closed and tested (with a threshold of
1 the return is SELF_WRITTEN); in a live run it simply never has a return to
close on after cycle 2. The threshold is tag B, inherited, untuned.

**What is still true:** the mind reads one of the six — the directive, whose
payload is structured. The other five are sentences. They run the layers and are
in use as data, but nothing in this mind can read English, so they change no
expectation.

### What a third party can read of the prior, 2026-09-23

Measured by reading a live run's `[event]` log directly, not through this code:
the five T3 queries were there and `prior:directive` moved `prior → running` at
cycle 1 — but **960 of 960 layer-exit lines were the cycle datum's**. The
recalled datums ran T1→T8 and left no path; their floor-tags stayed at 1; their
tags lived only in mutable `[data]`. So a reader could see that *something named
`prior:directive` began to run*, and not what class of data it was, nor that it
came through the gate — which §13.6 asks a third party to confirm from traces.

Re-reading §9 settled the fix and ruled out the first proposal. Writing each
prior's CONTENT into `[event]` at admission would put uncontested information
into the agent's memory — the log is also what recollection reads — and §9 keeps
the trail complete "without letting uncontested information into the agent's
memory". Admission is not an edge of the provenance graph, so the protocol does
not ask for it to be logged. What it does ask: "every layer a datum exits MUST
be recorded", no pass-through layers, and an open layer that makes the log
"auditable by data class". Plone chose (b): the path, and the tag set, never the
content.

Fixed in dil-core (`d358902`), ported: a recalled datum's exits are recorded
under its own id, its floor-tag is stamped as it passes, and the cycle's activity
record carries its full tag set (fixed and open). A cycle that recalls nothing
writes exactly what it wrote before. The checker gained two trace claims — a
recalled datum's path covers T1→T8 (C3), and every datum leaving `prior` shows a
gate-admissible tag set in that cycle's record (C6, §13.6) — and a test pins that
a datum appearing from `prior` with no tags in the trace fails.

Live, 120 cycles each, read from the JSONL:

| | `ls20` | `vc33` |
|---|---|---|
| layer-exit lines | 960 cycle + 8 × 6 recalled | same |
| recalled tag sets in the cycle-1 record | 6, floor-tag 8 | 6 |
| directive text anywhere in the log | 0 | 0 |
| hash chain | ok, 4 082 records | ok, 3 284 |
| conformance | 5 pass, 1 partial (C4, by design), 1 unverifiable (C2) | same |

C2 is unverifiable only because the gate result was not handed to the checker;
the run itself qualified. C4's partial is §7: continuity is attributable only by
a third party.

## 2026-09-24

### Direction C: can an open model write the world model? First measurements, 2026-09-24

Settled with Plone: the mind's thinking can be done by an open model that writes
an **executable world model** — a program `predict(grid, action) -> grid` — which
DIL then tests against the region, as data in the store, expectation → mismatch →
scar → rewrite. The model thinks; it does not choose. Before any architecture,
the question measured is whether a model that can run offline writes such a
program at all. Probe: `scripts/wm_probe.py`, on the 159 recorded `ls20`
transitions (80 train, 79 held out), scored by **exact** match of the whole 64×64
grid. Baseline "nothing changes": 0/159 — every step changes at least two cells.

| where | model | mode | runs | best program, train / held out |
|---|---|---|---|---|
| this machine, CPU + GTX 1050 Ti | Qwen3.6-35B-A3B, IQ4_XS | no thinking | 1st | **64/80 / 60/79 (76%)** |
| this machine | same | no thinking | 2nd | 1/80 / 0/79 |
| Kaggle RTX Pro 6000, vLLM | Qwen3.6-27B-FP8 | no thinking | 2 | 0/80 / 0/79 both |
| Kaggle RTX Pro 6000, vLLM | Qwen3.6-27B-FP8 | thinking | 2 | no program: every round hit the 16,384-token cap inside its reasoning |

What the numbers say, and do not:

- **The capability exists and is not reliable.** One run wrote a program exact on
  76% of transitions it had never seen; its 35 misses were almost all movement,
  the step counter being right. The next run with the same model and data wrote
  one right once in 80. Two runs cannot give a rate.
- **The 27B dense model did worse here than the 35B-A3B MoE**: six programs, all
  loading and running, none exact once. Four runs are not enough to rank models
  either.
- **Thinking needs a far larger budget.** 26–44k characters of reasoning per round
  never reached code within 16,384 tokens.
- The first local run's two failed rounds were the probe's fault — a 4,096-token
  cap, and each revision seeing the whole transcript. Fixed before the next runs:
  the probe keeps the best program and shows only it and its failures.

The pipeline itself is proven: the notebook checked all 80 model files (30.9 GB)
against Hugging Face's published hashes, installed vLLM 0.19 offline, served
65k-token contexts with a 199k-token KV cache (≈11 full-length requests at
once), and generated about 33 tokens/s per stream with four streams. The run used
0.48 h of the 30 h weekly GPU quota; the RTX machine was not charged at more than
wall-clock time. Locally the same probe costs 25–45 minutes a run.

#### Run 2 on Kaggle: the 35B-A3B MoE, FP8, 2026-09-24

Same probe, same data, `Qwen3.6-35B-A3B-FP8` (the official release, mirrored,
all 56 files checked against Hugging Face before serving — the check asserts, and
the server that runs after it did start). Eight runs at once, four without
thinking and four with, three rounds each, up to 45,000 output tokens a round.

| run | best program, train / held out | note |
|---|---|---|
| no thinking 0 | 7/80 / 3/79 | |
| no thinking 1 | **78/80 / 75/79 (95%)** | round 0 already 63/80 / 58/79 |
| no thinking 2 | **78/80 / 75/79 (95%)** | round 0 63/80 / 58/79; round 1 fell to 0, round 2 recovered |
| no thinking 3 | 0/80 after round 0 | then refused: 20,537 prompt + 45,000 output = 65,537 tokens, one over the 65,536 context |
| thinking 0 | 12/80 / 0/79 | 33–40k chars of reasoning a round |
| thinking 1 | 2/80 / 0/79 | |
| thinking 2 | 0/80 / 0/79 | one round hit the 45,000 cap |
| thinking 3 | 0/80 / 0/79 | one round hit the cap after 100,141 chars of reasoning |

What this adds to run 1:

- **Two independent runs reached the same 95% held out with different code.**
  Both programs are rules, not lookup tables, and state the same two: the 5×5
  object (two rows of 12 over three of 9) moves five cells in the action's
  direction only if every target cell is 3, and the bar on rows 61–62 advances one
  column per action. Why the last 4 held-out transitions miss has not been looked
  at.
- **Still not reliable**: of the three no-thinking runs that finished, two reached
  95% and one 4%. Across both machines, 3 of 6 no-thinking runs of this model
  wrote a program above 75% held out. That is a count, not a rate.
- **Thinking made it worse, not slower-but-better**, with the budget nearly
  three times run 1's: 0–2 of 79 held out in every thinking run. The reasoning
  produced code, and the code was wrong.
- The refused run was the builder's fault: the context was fixed at 65,536 while
  the output cap was raised. It now sizes the context as
  `max(65536, max tokens + 24,576)` unless told otherwise.

Cost: 0.33 h of GPU quota (0.49 h used before, 0.82 h after, of 30 h a week).
Downloading the outputs was cut off by the local 600 s timeout; every probe's log
is present, but the notebook's own log was not downloaded.

#### What the thinking runs got wrong, read off their programs

The reasoning itself cannot be read: the probe kept only its length, not its
text, so whether the model tried to run the grid by hand in its reasoning is
unknown. Fixed for later runs — the log now keeps the reasoning whole, and the
temperature used. What can be read is every program, and
`scripts/compare_programs.py` re-scores each one and says where its wrong cells
are:

| log | round | train | held | wrong cells per miss | misses only in the bar |
|---|---|---|---|---|---|
| thinking 0 | 1 | 12 | 0 | 49.2 | 7 |
| thinking 3 | 1 | 0 | 0 | **17.1** | **64 of 80** |
| no thinking 1 | 0 | 63 | 58 | 52.4 | 1 |
| no thinking 1 | 2 | 78 | 75 | 70.0 | 1 |

- **Most thinking programs fitted the examples literally.** Coordinates copied from
  them — a start at (40, 34), the bar at column `13 + step`, fixed tracks at
  columns 34–38 and rows 45–49, clamps at rows 20–40; one kept its own position in
  state across calls instead of reading it from the grid; three described the
  10×5 region that changes (old place plus new) as a "wave" to paint, not as an
  object that moves. None checked whether the target cells were free — the rule
  the 95% programs have.
- **One came within a line of the no-thinking result.** Thinking 3, round 1, found
  the 5×5 object by its pattern and moved it five cells; 64 of its 80 train misses
  are only in the bar, because it took the first column where rows 61 and 62 are
  equal and not 3 to be the marker — column 0, value 4, not the 11s. Its other 16
  misses are as many as the no-thinking round-0 programs have without the
  blocked-move check. The round that should have fixed it hit the 45,000 cap
  after 100,141 characters of reasoning and wrote no code.
- **The comparison was not run as Qwen recommends, for either mode.** Every run
  sent temperature 0.2 and nothing else, and the server was started with
  `--generation-config vllm`, which by vLLM's engine-argument documentation loads
  no generation config and uses vLLM's defaults instead of the model's. The
  Qwen3.6-35B-A3B-FP8 model card recommends, for thinking on precise coding tasks,
  `temperature=0.6, top_p=0.95, top_k=20, presence_penalty=0.0`; for non-thinking,
  `temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5`; and an output
  length of 32,768 tokens for most queries, 81,920 for competition-level
  problems. "Thinking made it worse" holds for these settings only.

### Direction C, placed in the loop (Plone, same day)

The world-model probe (`scripts/wm_probe.py`) ran **entirely outside dil-arc3**:
it imports nothing from `src/`, its transitions came from a scripted agent in
`dump_frames.py`, and its score-and-rewrite loop was the probe's own. It recorded
no mismatch, no ResistEvent, no scar and no `[event]` line, so it is evidence
only that an open model *can* write such a program — not evidence about this
agent, and nothing the paper's claim can rest on. It also poured 80 transitions
into one prompt, the load INV-5 names. Its measurements stay as a feasibility
result; the next ones run inside the loop.

- **A program the model writes is `running` data** — the character's own, from
  running — not `prior`.
- **There is no trigger for rewriting it, and no constant to declare.** The model
  sits at the **mind**: it is the thinking. When its expectation meets the region
  and does not hold, the loop registers the mismatch, the ResistEvent and, where
  it holds, the scar; adjusting is what thinking does with that. If it does not
  adjust, the mismatch recurs. Rewriting is the consequence of mismatch, not a
  step scheduled by the host.
- **The mind reads by asking; nothing is poured into it.** It has the right to
  read anything in the store, and it chooses what: meeting a problem, it goes to
  memory for what bears on that problem. Only T3 could query the store, and only
  about what had just arrived, so this was a gap — fixed in dil-core first
  (`1e2d826`) and ported: T5 hands its rule `ask(cue)`, which emits a store query
  and nothing else, traced to T5 with register ↔, answered at T1 next cycle. The
  settled line narrows from "the mind does not emit" to **"the mind does not
  act"**: the one thing it sends out is a question to its own memory, and that
  question is in `[event]`.
- **What the region returns is data, and the scar is on it** (Plone, same day;
  cost accepted). dil-core kept no return as data: its one datum per cycle was
  the driver's cycle datum (payload a signal count, `domain: cycle`), which went
  to `scar` on any collision, so the tag sat on a counter and the mismatch did
  not say what it was a mismatch with (§3: "A `scar` has collided with resistance
  and held"). First built here as a host option, then, at Plone's direction,
  fixed in dil-core as a gap of the mechanism (`276f30a`) and ported back: each
  return enters `[data]` through the tagging-gate as `signal-<cycle>-<i>`, runs
  as `running`, leaves a line at every layer it exits, its tags (never its
  content) go into the cycle's activity record under `admitted`, and when the
  expectation about it fails **that datum** moves `running → scar`, the scar
  record embedding and naming it (`datumId`). The cycle datum still stands for
  the cycle, and for an absence, where nothing returned. The host declares the
  tags (`AdmitPolicy`; the reference `admit_return` tags `domain: region`,
  `source`, `format`); `arc3.observe.admit` uses this host's vocabulary —
  `domain: observation`, `kind`, `source`, and the channel's own `object` and
  `sense` values. The checker covers the returns' paths (C3) and gate entry
  (C6), and reads the flow mode from the cycle seal, since it is the cycle's.
- **Memory is what the store held before the cycle that asks** (Plone, option
  (a)). T3 asks after the cycle's returns are admitted, so at first 19 of cycle
  0's own arrivals came back as "recalled" — the character recalling what it is
  seeing. A query is now answered without the data admitted in the cycle that
  raised it. In dil-core too (`276f30a`), with a mutation check.

  Live, `ls20`, 60 cycles (`scripts/run_prior.py ls20 60 [admit]`): moves,
  positions and scars identical to a run before any of this; 1,142 returns kept
  (1,122 `running`, 20 `scar`); 20 of 20 scar records name their datum; 0
  returns recalled as their own memory; the 6 priors still recalled at cycle 1;
  12,364 `[event]` records; conformance unchanged (C1, C3, C5, C6, C7 pass, C4
  partial, C2 unverifiable). `run_prior.py` had counted absences as scars
  sourced `region`, which is the status entity's name too; it now counts them by
  `mismatch_kind` (0 here) — earlier absence counts from that script need
  re-checking.

### Protocol v0.3.3: `nascent`, entries by origin, `write`, revision (Plone, same day)

Discussed and settled with Plone, then written into the law in dil-core
(`f8230de`, protocol v0.3.3 and specification v7, copied into `spec/`), migrated
there (`44309b7`) and ported here:

- **`prior` is what its definition says**: host data existing before the loop
  ran. Region returns and the cycle datum are not that; they pass the
  tagging-gate at `running`, told apart by `domain`, their entry being their
  tag set in the cycle's record. The first port had admitted them as `prior`
  and moved them at once — a mislabel of this session's own making.
- **`nascent`** — the name chosen to keep clear of "self" and of T2's
  SELF_WRITTEN — is the second one-way entry: a datum the agent writes anew,
  bearing the cycle-mark of the cycle that wrote it. It arrives at T1 the next
  cycle, is SELF_WRITTEN at T2, runs every layer, and moves `nascent → running`.
- **A revision is not an entry**: the content of a held datum changes, its
  provenance does not, T2 reads it SELF_WRITTEN the next cycle, and `[event]`
  gets a bare `revision` line with no content. The content is read from the
  commit snapshot. This is what a rewritten world-model program is.
- The predict rule has **`write`** (anew, or with `datum_id` to revise), and a
  **cue may carry `provenance`**, so the mind can ask what collided.
- DEVIATION from dil-core, declared (Plone: too costly for a full agent, right
  for this one): **dil-arc3 also commits at the close of every cycle in which
  the agent wrote a datum**, so every version of the program is in a snapshot
  tied by its marker to its place in `[event]` (`COMMIT_CADENCE`; tested).
  `CycleResult.written` carries the count for the daemon.
- A bug the commit test caught on the way: a written datum's arrival carried its
  fixed tags as a dataclass, which the snapshot could not store; it now takes
  the store-return form.
- **A pre-existing gap, fixed the same day (`f1b4491`)**: the Python daemon's
  snapshot payload kept only the driver's `cycle` and `lastEmission`, not
  pending returns, `recalled`, `last_lateral` or `pending_writes`, so a recovery
  from a commit dropped whatever was on its way to T1. It now keeps the whole
  driver state, as dil-core does; snapshots in the old form still restore. A
  recovery test failed before the change and passes after.

Live, `ls20`, 60 cycles after the port: moves, positions, scars and recall
identical to before; `[event]` 11,162 records, 1,202 fewer than before — exactly
the 1,142 region returns' and 60 cycle datums' `prior → running` lines v0.3.3
drops; conformance unchanged. 267 tests.

### When the cycle datum scars, and which datum a recalled scar is (Plone, same day)

The deferred item from dil-core's README, settled with Plone and fixed there
first (`6c74f0c`, `dc7a9a7`), then ported:

- **The cycle datum goes to `scar` only when what it carries collides**: an
  outcome it cast (`projected → scar`), or a collision with no return of its own
  to hold the scar — an absence, a return the host kept out, a store arrival —
  for which it stands. A cast that did not collide returns to use
  (`projected → running`) even when another return collided; with no cast it
  stays `running`. ResistEvents and scar records are unchanged.
- **A recalled scar is the datum its record names**: since the return holds the
  scar, recollection now reports that datum (`cycle-N` only for an absence), and
  the driver moves it `scar → running` once, while it is a scar, with `[data]`
  following the line. Before, it recorded the move for `cycle-N` on every
  recall and never touched `[data]` — a gap opened when the scar moved onto the
  return.
- Left open, in both repositories: a store arrival that mismatches (a revised
  datum arriving against persistence's "nothing changed") is not tied to its
  own datum; the cycle datum stands for it. This mind returns store arrivals as
  they are, so it does not arise here.

Live, `ls20`, 60 cycles: behaviour identical; 12 cycles had a collision and in
none did the cycle datum go to `scar` — every one of its 59 casts ended
`projected → running`. The three situations it casts (`H_COUNT = 3`, the most
confident) never collided; every collision was on another thing's return, which
holds the scar (20 of 20 records name it). 275 tests.

### Every record takes the clock when it happens (Plone, same day)

Found by reading back the first live run with the model in the loop: dil-core
read the clock once per cycle and stamped every record and datum in it with
that reading. Seventeen minutes of thinking inside T5 showed nowhere in
`[event]` — every line of the cycle bore its start — and the program the model
wrote bore that time too, though written at the end. §9 asks for "each
transition as it occurs" and a timestamp "when the datum is first stamped".
Fixed in dil-core (`9073ddf`) and ported: every record takes the clock when it
is appended, region returns and written data when they enter, the cycle datum
keeps its cycle's start, and the seal adds `closedAt`. Tests with a ticking
clock, two mutations caught in dil-core. 283 tests.

Still not in the log, by the law as it stands: a thought the mind does not keep
changes no datum, so it leaves no line beyond the query it asked with; the time
it took shows only as the gap between T4 and T5.

### First live run with the model in the loop, this machine (2026-09-24)

`scripts/run_world_model.py ls20 10` (renamed `run_game.py` since), Qwen3.6-35B-A3B IQ4_XS on llama.cpp
(CPU + GTX 1050 Ti), no thinking, temperature 0.2. Store:
`scripts/data/wm-ls20-cobmhzp2/` (git-ignored). Code as of `949883e` — the run
started before the per-record clock, so its `[event]` still stamps each cycle
with one time.

- **The loop worked end to end, and the log shows it.** The frame's expectation
  failed in 9 of 10 cycles (cycle 0 is the RESET, which changes nothing); each
  failed frame is the datum that went to `scar`, named by its record. The mind
  asked the store 9 times, `{"kind": "frame", "provenance": "scar"}`, from T5.
  The first program entered at `nascent` (`written-1-0`) and moved to `running`
  the next cycle; 2 commits; 2,319 `[event]` records; conformance as before
  (C1, C3, C5, C6, C7 pass, C4 partial, C2 unverifiable).
- **The thinking did not find the game.** 9 thoughts; the first program was kept
  because there was none, though it explained 0 of the 1 transition it had; the
  8 after it explained 0 of 1–7 and were not kept, so no revision. 5,971 s for
  10 cycles, almost all of it the model (262–1,057 s a thought).
- **The scoring is not the cause**: the program that reached 95% on Kaggle
  scores 153/159 on the recorded `ls20` transitions through the mind's own
  `score()`.
- **Why so little evidence**: memory answers what the store held before the
  cycle that asks, the answer arrives the next cycle, and it reaches T5 after the
  frame has been predicted; so a transition seen at cycle k is evidence from
  about k+3. After 10 cycles the model had seen at most 7, against the 24 the
  probe showed at once. The local model is also the weaker one: the same model
  and quantisation wrote 1/80 in the probe's second local run.
- Open, for Plone: shortening that lag touches the driver's signal order or has
  the mind hold what it has just seen until memory can answer — both near the
  line "memory is the store".

### What a written datum was built from, and the mind's short-term perception (Plone, same day)

Plone rejected reordering the driver so memory answers before the region
returns ("why would the mind read memory before anything has come back?") and
chose (b) with the trace closed:

- **Short-term perception is T5's window**, already in the law (§6.1
  `Expectation.built_from: history_window`; the baseline window is
  `BASELINE_WINDOW = 16`). The world-model mind had ignored the `window` its rule
  receives; it now thinks from what the store answered, what the window holds of
  the frame, and the transition in front of it. No new mechanism, no new constant.
- **A written datum records what it was built from** — protocol v0.3.4, written
  with Plone and fixed in dil-core first (`c2c0cd2`), ported here. Every write
  carries `built_from` (units or ids; `()` for nothing held), the driver maps
  units to their data across cycles (a weakref-keyed map; `InfoUnit` now has a
  weakref slot) and records ids only in the cycle's `written` entries; an
  unknown id, a unit from no datum, or a write that says nothing is refused; the
  checker fails a written datum naming data with no recorded entry. The mind's
  `built_from` is exactly the evidence the model was shown. With it a reader
  follows data → program version → expectations → scars → revision.

287 tests.

### One mind, and it is the model (Plone, 2026-09-24)

The run that put the model in the loop had wrapped it around the older mind
instead of replacing it: the frame went to the model's program, everything else
— "things" a computation of the grid had found, and the region's status — to the
counting mind, and only the counting mind's readings reached the field the self
chooses from. Plone: two brains in one body is off the design — which of them
would the self crystallize from? One mind; use the model and nothing muddled.

- **Removed**: `perceive.py`, `seeing.py`, `interpret.py` (the computation of the
  grid into things) and the counting `Mind` with `predict_rule`, with their tests.
  Their code is at `b7b64d3`; the scripts that measured them run there.
- **The host takes in and computes nothing**: two signals a cycle — the frame
  (both grid stacks and the move, as returned) and the region's status. Frame
  datums are tagged `sense: vision`; a status is about the region's status, its
  levels and its actions.
- **The one mind** (`src/arc3/mind.py`, formerly `world_model.py`): the model and
  its program predict the frame; the status keeps the standing expectation (it
  stays as it was — the absence of an understanding, not a second one); what the
  region says is read against the recalled directive. Per action it reports to
  the field `resolved`, `progress` and `valence`, all from the program's hold on
  the frame and the region's answers — what `respond.py` reads, unchanged.
- **Terminology, settled with Plone**: seeing is the eye's, computing is the
  brain's. The host is the eye — it takes the signal in; the mind computes and
  interprets. Never name a computation of the mind with a verb of the senses: the
  old `seeing.py` did that, and the misname hid a second mind inside the host.
- Consequence to watch: nothing that arrives is about "things" now, so the prior
  item about the world's things is never recalled; the one about seeing is, on the
  first frame.

Offline check before any GPU: three cycles, the mind asked the store on each
mismatch, the field carried its readings per action, conformance unchanged, 156
`[event]` records for three cycles (468 for two before, most of them the thing
data). 234 tests.

### The counting mind, as `README.md` described it until 2026-09-24

Moved from `README.md` when the history left it. The README's status said:
"**Until 2026-09-24 there were two minds**: a counting mind over "things" a
computation of the grid had found, which chose the moves, and the model's
program beside it for the frame. Nothing said which of the two the self
crystallized from." Of the roles it said they were settled deliberately,
"because getting them the wrong way round was the first real mistake this
project made — and running two minds at once was the second"; and of seeing:
"An earlier build computed "things" from the grid inside the host's path and
named that seeing — the name was wrong, and the computation was a second mind."

Its section on the counting mind, whose code is at `b7b64d3` (the scripts that
measured it run there, `scripts/README.md`):

It is **not a downloaded network**, for three reasons each sufficient alone:

- the scored games are unseen, and their mechanics are the thing to be
  discovered, so weights trained on other games predict the wrong world;
- Kaggle's evaluation session has no network;
- INV-5 rules out the alternative in so many words — "refeeding the whole game
  history into a context window each step is a load, not an accrual".

What is left, and what the protocol actually asks for, is a predictor that
**accrues within the episode**. It starts each game knowing nothing about it.
There are no weights, no gradients, and no third-party dependencies at all —
`dependencies = []` is a requirement, not a boast, because an accelerated Kaggle
session has no network to install from.

It works in four steps, all of them cheap:

1. **Perceive** — pieces are connected runs of one value, four-connected,
   excluding whatever the grid is mostly made of. The background is *read*, not
   assumed, so a world on a non-zero background still parses.
2. **See individuals** — each piece is followed from frame to frame, and pieces
   that keep moving together, by the same displacement, are learned to be one
   thing. Nothing is configured: a two-colour object is recognised as one object
   because its parts always move as one.
3. **Read the situation** — for each thing, what it faces first on every side, at
   any distance: another thing, or the edge of the grid. No distance constant, and
   nothing about what any action does.
4. **Predict** — associate (thing, action, situation) with what the thing then
   did, and answer by majority. Report upward, per action, how fast that is being
   learned and how the region has answered it.

#### Identity was chosen by measurement

A thing has to stay the same thing while it persists, or expectation can never
match. Four readings were scored against 60 real frames per game by *churn* —
how many identities exist overall against how many are present in one frame:

| identity | churn | prediction `ls20` / `vc33` |
|---|---|---|
| value + bounding box | 6.2× | — |
| value + cell count | 6.2× | — |
| value — a kind of stuff | 1.0× | 93% / 85% |
| **tracked piece, grouped by common fate, read with what lies ahead** | **1.7×** | **99% / 93%** |

Stuff held identity perfectly and hid the thing that mattered. In `ls20`, value 9
is five separate pieces, one of which moves; every reading of "the 9s" was
swamped by the four that never move. Tracking individuals costs some churn —
partly because a thing is renamed when its parts are first grouped — and buys
this: the moving object's blocked-or-not outcome, predicted **100%**.

The grouping step is there because of a second measurement. Before it, the
object's front part was predicted 100% and its back part only 67%: the object is
drawn in two colours, segmentation splits it, and a ray cast from the back part
stopped at its own front part and never saw the wall.

#### Its measurements

Prediction accuracy, over the same 316 real transitions from two games.

| | `ls20` | `vc33` |
|---|---|---|
| actions as entities, one hand-written feature | 94% | 69% |
| kinds of stuff as entities, context = action | 93% | 85% |
| **tracked things, context = action + what lies ahead** | **99%** | **93%** |

The first row is the architecture this replaced, which made an *action* the unit
of experience. Its one strong number came from a feature written by hand for
this game; the feature is gone, and nothing is given up for it.

Live runs, 120 cycles each:

| | `ls20` | `vc33` |
|---|---|---|
| things perceived per cycle | 19 | 12 |
| Other-to-Other interactions (`SocialEdge`) | 28 | 20 |
| scars recorded | 54 | 101 |
| of which absences | 4 | 4 |
| moves committed | `4:38 1:28 3:28 2:26` | ACTION6 only, swept |
| distinct positions the moving object reached | 19 | — |
| **levels completed** | **0** | **0** |

Two earlier versions of this table are gone, and why is worth keeping. One came
from runs where the agent pressed a single key every cycle — a regression in how
it chose moves. The next came from an agent that acted on whatever it understood
least and took one action 103 times in 120. Their perception figures were sound;
their behaviour figures described an agent stuck, and they were replaced rather
than footnoted.

#### How curiosity chose

It follows **learning progress**, not ignorance. Going for whatever is least
understood sticks to irreducible noise — the "noisy TV" failure of
curiosity-driven exploration — because noise never becomes understood.
Following how fast understanding is *changing* instead, noise that cannot be
learned shows no progress, and curiosity leaves it on its own. Measured, one
action's share of moves fell from 103/120 to 38/120.

### The run script and the Kaggle notebook renamed away from "world model"

With one mind there is no separate world model to name. `scripts/run_world_model.py`
became `scripts/run_game.py` (its stores `run-<game>-*`), and the Kaggle notebook
the builder makes became `dil-arc3-run` (`48eaa27`). The notebook already running
under the old slug, `dil-arc3-world-model-run`, keeps it.

### History moved out of `README.md` and `CLAUDE.md`

At Plone's request: the README says what the agent is, `CLAUDE.md` holds the rules
and declarations in force, and every entry above moved here unchanged.

### Stale declarations brought to the one mind, and a rule for history

Found while moving the history, fixed at Plone's request:

- The hard constraint said "Never modify `dil-core`. This repo *imports* it."
  Neither held: `src/dil/` is a Python port, and every gap in the mechanism has
  been fixed in dil-core first, at Plone's direction. It now says so.
- `src/arc3/decisions.py` still declared the entity as "affordance" and tag H as
  equality of an effect signature in `effect.py`, a file removed in the rebuild.
  It now declares the frame and the region as the entities, and the frame's fit
  as exact equality of the predicted and returned grid (the last of each stack).
- `src/dil/runtime/reflection.py` called the tag E reader "unresolved"; it was
  written at 19:13 on 2026-09-22 and tag E was settled at 23:31 the same day (a
  peer agent, `peer.py`). It now says so, and that the live run does not wire a
  peer yet.
- `CLAUDE.md` gained the rule: history goes in `LOG.md`; `README.md` and
  `CLAUDE.md` say only what holds now.

### The one mind's first run on Kaggle

Kernel `dil-arc3-world-model-run` v2, code `13d5f9c`: `ls20`, 60 cycles,
Qwen3.6-35B-A3B-FP8 on vLLM 0.19, RTX Pro 6000, no thinking, temperature 0.2, at
most 12,288 tokens a thought. Outputs in `scripts/data/kaggle/dil-run/output/`
(git-ignored): `run.txt`, the notebook log, the vLLM log, and the whole store.

- **Time.** Notebook 1,136 s: the 56 model files (37.5 GB) checked against
  Hugging Face's hashes in 76 s, no problem; vLLM ready 195 s after it started;
  the game 746 s. By wall time that is about 0.32 h of GPU quota — not read from
  Kaggle's quota page.
- **The notebook's log said nothing for those 746 s.** Cell 7 sent the run's
  lines only to `run.txt`, so a run in progress could not be told from a hung
  one. Fixed in the builder afterwards (`d5ce8b3`): each line now reaches the log
  as it comes.
- **The program.** `written-1-0` entered at `nascent` at cycle 1 and moved to
  `running` at cycle 2; it was revised at cycles 2, 3, 4, 21 and 35 — six
  versions, five bare `revision` lines. Each written entry in its cycle's seal
  names what it was built from: 2, 3, 4, 5, 21 and 24 datum ids. 31 thoughts,
  3.9–76.3 s each; two stopped at the 12,288-token cap with no code.
- **The frame.** The expectation failed on every cycle from 1 to 21, then on 10
  of the last 38 (33, 35, 38, 39, 41, 42, 43, 46, 48, 50). Version 5 held for 11
  cycles in a row (22–32), version 6 for the last 9 (51–59).
- **Keep-best held a program that was slipping.** Version 6 explained 22 of the
  24 transitions shown at cycle 36 and 16 of 24 by cycle 51; no candidate
  explained more, so none was kept.
- **What the mind ended with** names fixed 5×5 blocks by coordinate (rows
  40–49, columns 29–43) and swaps them by action, reading a cursor from row 61. It
  does not find the object, as the probe's 95% programs did.
- Moves `1:13 2:21 3:15 4:11`; 0 levels; the game ended `NOT_FINISHED`.
- `[event]`: 6,341 records, 12 commits; conformance C1, C3,
  C5, C6, C7 pass, C4 partial, C2 unverifiable. Store queries: 31 from T5 (the
  mind, every one `{"kind": "frame", "provenance": "scar"}`) and 4 from T3.
- **Read off `[event]`: 42 of the 45 status scars are the agent's own move.**
  The status payload carries `context: action:N`, and the standing expectation
  repeats the whole payload, so every change of move was registered as the region
  resisting. The other 3 differ in what the region reported (`status`). The
  cycle datum's cast collided on 49 cycles (`projected → scar`), including the 11
  in which only the status scarred. Not fixed; put to Plone.

### The status stops colliding on the agent's own move (Plone, same day)

Approved by Plone after the Kaggle run above. The mind's standing expectation of
the region's status now holds what the region reported last and takes the
`context` — the action just taken, the self's act — as it is
(`mind.standing_status`). A test pins it: a change of move leaves no scar; a
change in what the region says still does. It fails on the old code.

Live, `ls20`, 8 cycles on this machine with no model reachable (every frame
misses): 0 status scars across moves `1:2 2:2 3:2 4:2`, against 42 of 45 on
Kaggle.

**What the fix uncovered.** On Kaggle, C5 and C7 passed because those false
status scars were a second resistance source. With them gone the frame is the
only one: 12 cycles give C5 `partial` ("1 distinct resistance source") and C7
`fail` ("diversity-loss established from traces: only 1 distinct source(s) over
the last 8 records"). The earlier passes were earned by the defect. The declared
remedy is tag E's peer reader, which the live run does not wire yet.

The notebook builders also give every cell an `id`: Kaggle's log warned that a
cell without one "will become a hard error in future nbformat versions". The
built notebook validates under nbformat with warnings raised as errors. The other
lines in that log — `frozen modules` from the debugger, `SyntaxWarning` from
`mistune` and `nbconvert` — come from Kaggle's own packages, not from this code.

## 2026-09-25

### The peer reader wired, and the peers echo (Plone: wire it, then test C7)

Tag E's mechanism had never run in this repository: no test touched `peer.py`,
and the measurement that gave §13.5/§13.7 `pass` with a peer (2026-09-22) came
from a scratchpad script no longer here. Wiring it found three things wrong:

- **It dropped presence.** `PeerReflectingSource.next()` rebuilt the cycle's
  input without `afforded`, so behind a peer T7 would have lost the region's
  word on what is there.
- **A reading was a dataclass**, which `[data]` and a snapshot cannot hold. It
  is plain data now (`reading_payload`).
- **"Read-only" was a type, not a fact.** `ReadableEventLog` is a Protocol;
  handing a peer the log would have handed it `append`. `read_only` is a view
  that reads and holds nothing to write through, and it reads late, so each
  agent can be given the other's view before either store exists.

The host keeps readings as data (`domain: reflection`, `kind: peer-reading`),
declares the reflection transducer for `peer-reflection`, and
`scripts/run_game.py --peer GAME` runs a second agent — its own mind, its own
store — beside the first, each reading the other. Tests pin the three fixes, the
bound of two readings per peer per cycle, and that an agent alone establishes
diversity-loss. Taking out the presence fix fails one test, taking out the
plain-data fix fails two.

Live on this machine, `ls20` with `vc33` as its peer, 12 cycles each, no model
reachable, real stores (3 commits each, readings in the snapshots):

| | `ls20` | `vc33` |
|---|---|---|
| scars from the frame | 11 | 11 |
| scars from the peer's readings | 18 | 19 |
| of which about the peer's own frame | 7 | 7 |
| of which about a reading this agent sent | **11** | **12** |
| C5 / C7 | pass / pass | pass / pass |

**The peers echo.** A reading collides with the standing expectation (nothing
predicts what a peer will say next), that collision is a scar in this agent's
log, and the other peer reads it back as a new collision to report. Already at
12 cycles most readings are about readings, and the supply grows faster than
the two a cycle that are read. So C7's `pass` here is partly earned by the peers
reflecting each other, not by the region. Not settled; put to Plone.

### The peer was a retelling; the reader is an onlooker (Plone, same day)

Plone, on the peer: what B passed to A was A's own recorded collision, told back
— "đơn thuần là kể lại" — and so a mechanism built to get past C7. The idea of
the protocol is a real difference of view: A does not think it is stumbling, B
thinks it is and says so; a contribution with no claim of being right, and a
mismatch between A and B, not B describing A's mismatch with the region. Read
against the text it holds: §8.3 wants a source that "resists the lens itself,
mismatching in a way the agent cannot re-author", and §8.4 calls a compliant
source "useless however much it supplies"; a collision the agent recorded is
one it authored. The literal phrase "a collision read into coordinates" is what
`collision_coordinates` was built from, in dil-core too; that is left to Plone.

Settled with Plone: B need not be an agent or have a mind. An Other is a
position (§2), and a B-source may be "a hard third party … so long as it can
resist" (spec, DECIDE@IMPL-D). B is `src/arc3/onlooker.py`, a separate piece of
code that judges the agent's behaviour and not the region: it sees the moves
committed and whether the level moved, nothing else, and says "repeating" (the
same move 4 times, level unchanged; the 4 not measured) or "back-and-forth"
(x y x y), pointing at the cycle the pattern began. The agent expects it to say
nothing; a change of stance collides, and the scar is on the remark's datum.
`--peer` is gone from the run; `peer.py` stays as ported, unused, its plumbing
tests kept and the test that asserted C7 passing through it removed.

Tests: the two remarks, their stable coordinate, a level or a RESET clearing
them, clicks at different places being different moves; in the loop, a mismatch
only at each change of stance (cycles 4, 8 and 10 of a scripted run), every
remark kept as data. 243 tests.

Live, `ls20`, 60 cycles, no model reachable: the policy cycles the four moves
(15 each), the onlooker never objects, and C7 is `fail` with it as without it
("only 1 distinct source(s) over the last 8 records"). Replaying the Kaggle
run's 60 moves past it: it would have said "repeating" at cycle 44 (ACTION1 since
cycle 40), taken it back at 45, and said it again at 56 (ACTION2 since 52). What
C7 renders with the model in the loop is not yet measured.

### Reflection fixed in dil-core, ported; the peer removed (Plone, same day)

Approved by Plone: the retelling was in dil-core's mechanism too. There,
`formReading` required a reading to address a recorded scar and
`collisionCoordinates` listed only scars, so any reader built on it could only
hand the agent a collision it had authored. Fixed in dil-core (`3a186b4`,
changelog `2404e98`, 365 tests): a reading points at a cycle the agent's trace
recorded, with or without a scar, and carries the reader's own view; a cycle
the trace never recorded is refused; `traceCycles` replaces
`collisionCoordinates`; tag E redeclared. The protocol's own phrase in §8.4, "a
collision read into coordinates", is left as it is.

Ported to `src/dil/runtime/reflection.py` with four tests (this repository had
none for it). `peer.py`, built wholly on the retelling, was removed with its
tests. 244 tests.

### `reflection.py` is not used here, and a line said it was

Asked by Plone what `reflection.*` does, a check found nothing in this
repository calling it: the onlooker sends its remark through the host's own
transducer, and cannot use `form_reading`, which reads the agent's log to check
the cycle — a log the onlooker, by design, never sees. The tag E header in
`src/dil/runtime/decisions.py` had said "the mechanism a reading enters by is
`reflection.py`", which was false; corrected. `recollection.py` still carried the
old "a collision read into coordinates" wording, fixed in dil-core but missed in
the port; corrected. Plone chose to keep `reflection.py` so that `src/dil/`
stays a faithful port of dil-core, declared as not used by this host.

### The onlooker's first run on Kaggle, with the model in the loop

Kernel `dil-arc3-run` v1 (code `18d39e6`, packed before the reflection port,
which it does not use): `ls20`, 60 cycles, the same model and settings as the
v2 run above. Outputs in `scripts/data/kaggle/dil-run/output-onlooker/`.
Notebook 1,101 s — the model files checked in 55 s, vLLM ready in 195 s, the
game 748 s — about 0.31 h of GPU quota by wall time, not read from Kaggle's
page. The notebook's log now showed each cycle as it ran.

- **The run is the v2 run again, move for move.** The 31 thoughts (which
  transition, scores, adoption, completion tokens), the final program and the
  moves `1:13 2:21 3:15 4:11` are identical; only seconds differ. At temperature
  0.2 with vLLM's defaults the model answered the same prompts the same way, so
  a third party re-running this notebook should get this trace. Neither change
  since v2 reaches behaviour: the status expectation does not feed the policy,
  and nothing reads the onlooker.
- **Scars by source**: frame 31 (the same cycles as v2), region 3, onlooker 3.
  The status scars fell from 45 to 3, and the 3 are the region's own word: the
  stack depth went 0 → 5 → −5 → 0 over cycles 43–45.
- **The onlooker spoke three times**, as the replay predicted: at cycle 44,
  "repeating" ACTION1 since cycle 40; at 45 it took that back; at 56, "repeating"
  ACTION2 since cycle 52, held to the end. Each change of stance is one scar on
  its remark.
- **C5 pass, C7 pass**: "3 distinct sources over the last 8 records" — region
  44, onlooker 44, region 45, onlooker 45, frame 46, 48, 50, onlooker 56. Every
  source is real and none is manufactured, but the pass is thin: it rests on the
  frame going quiet after cycle 50 and the onlooker objecting at 56. A run in
  which the agent kept varying its moves while the frame kept colliding would
  render `fail` again.
- **Registered, and inert.** Nothing reads the remarks — not the mind, not the
  respond policy — so the onlooker's objection at cycle 56 was followed by four
  more ACTION2s. §8.4 names three conditions for a return to re-lean the store:
  deliberate (met — it is registered), accumulated and long-run (not met — no
  reader). Put to Plone with the gap between what the mind learns and what the
  self does.

### Every datum that meets a mismatch is scarred; the mind reads what it chooses (Plone, same day)

Plone, on where behaviour changes: not in choosing but in reading, learning and
changing. The run showed the mind reading one thing only — 31 queries, all the
same fixed cue for scarred frames — thinking only when the frame failed, and
its program never scarred: `written-1-0` sat at `running` for 60 cycles through
five revisions. Settled with Plone, and done as one package:

- **Protocol v0.3.5** (dil-core `4f5da8f`, changelog `fdbe46e`, 370 tests):
  `scar` is a tag on every datum that meets a mismatch. A mismatch has two
  sides; an `Expectation` now names the held data it is, `held_by` — the
  observation persistence repeats, or a datum the rule names, such as a
  program — and each moves to `scar` with its own record of the same
  ResistEvent. Evidence in the window the expectation is not, met nothing (Plone:
  "Khung hình cũ có gặp mismatch không? Nếu không thì tại sao lại dính tag?"). A
  scar used again returns to `running`. A mismatch with the agent's own revision
  coming back from the store scars no expecting side — found by dil-core's
  revision test, which would otherwise have scarred a datum for being revised.
  The checker's C6 checks it. Ported here with five tests; spec copied.
- **The mind reads what the model chooses.** The fixed cue is gone: the model
  puts `ASK {...}` lines in its answer, by any tag key and `provenance`, and each
  is a store query from T5; answers are the evidence of its next thought.
- **Any mismatch sets it thinking**: the frame, the region's status, or the
  onlooker's change of stance — at most once a cycle; the model is shown what
  the onlooker says.
- **The program predicts what the region returns**: the next grid and, when it
  says so, the status fields; an expectation the program made is the program's
  (`held_by`), so the program scars when it fails and returns to `running` when
  used again. A standing expectation is the observation it repeats.
- **Declared gap**: the cycle the program first comes back, T5 meets the frame
  before the store arrival that tells the mind its datum's id, so that one
  expectation is not attributed.

Tests pinned one scar per mismatch in five places here and five in dil-core;
each now pins both sides. 252 tests. On 12 live `ls20` cycles with no model
reachable the run holds together: 11 frame scars, the mind thinking on each,
C5 `partial` and C7 `fail` as before.

### The v0.3.5 mind's first run on Kaggle

Kernel `dil-arc3-run` v2, code `1d30b8d`, `ls20`, 60 cycles, the same model and
settings. Outputs in `scripts/data/kaggle/dil-run/output-v035/`. Notebook 2,199 s
(game 1,838 s, 2.5 times the last run) — about 0.61 h of GPU quota by wall time,
not read from Kaggle's page.

- **The mechanism ran as designed and the trace shows it.** The program
  `written-1-0` circulated between `running` and `scar` on almost every cycle:
  53 scars of its own, each followed by `scar → running` when used again.
  Recalled scarred frames returned to use 39 times. The model chose what to read
  — 24 queries over 7 cues, frames, statuses, its own program, and from cycle 37
  the onlooker's remarks — and the mind thought on the onlooker once (cycle 43).
  Conformance: C1, C3, C5, C6 (with the `held_by` check), C7 pass; C4 partial,
  C2 unverifiable.
- **Prediction was far worse.** The frame expectation held on 4 of 59 cycles,
  against 28 in the runs before; the best candidate reached 20 of 24 once (cycle
  39) and slid back. The first program was already worse — 1 of 2 against 2 of 2,
  in the same first situation — and the earlier runs had repeated exactly, so
  the change in the prompt (the status report, the `ASK` instructions) is the
  likely cause. One run does not show it.
- **The onlooker's objection changed nothing.** From cycle 41 it said
  "back-and-forth" (ACTION3/ACTION4 since cycle 38) and the agent alternated 3
  and 4 to the end. Every `resolved` and `progress` reading in the field was 0
  or near it, so the respond policy's tie-break alternated — the very pattern the
  onlooker named. The scar on the program does not yet reach the self in any
  form that tells one action from another.
- One thought failed to load: the model indented its whole code block
  (`IndentationError`).
- 0 levels; moves `1:13 2:13 3:14 4:20`.

### The prompt, measured: the plain prompt back on the v0.3.5 mechanism

Kernel `dil-arc3-run` v3, code `d41e1dd`, `--prompt plain`: the prompt of the
runs before, word for word (checked against `48eaa27`), programs scored on the
grid alone; every v0.3.5 mechanism in place. Outputs in
`scripts/data/kaggle/dil-run/output-plain/`. Notebook 1,718 s, game 1,352 s.

| | v2 (old mind, old prompt) | full prompt, v0.3.5 | plain prompt, v0.3.5 |
|---|---|---|---|
| frame expectation held, of 59 | 28 | **4** | **36** |
| first thought: held / candidate, tokens | 0/2 → 2, 7,089 | 0/2 → 1, 7,466 | 0/2 → 1, 7,911 |
| program versions | 6 | 6 | 4 |
| scars: frame / region / onlooker | 31 / 45 / — | 108 / 4 / 10 | 44 / 6 / 14 |
| C7 | pass | pass | pass |

- **The fuller prompt is the likely cause of the collapse**: with the same
  mechanism, the plain prompt held the frame on 36 of 59 cycles against 4. One
  run each; not a rate.
- **The runs are not deterministic across sessions, and an earlier entry said
  they were.** The first prompt, rebuilt from each run's stored frames, is the
  same byte for byte (same SHA-256) for v2 and this run, yet the first answer
  differed (7,089 against 7,911 tokens). The v2 and onlooker runs had matched
  move for move; that was two sessions agreeing, not a guarantee. "A third party
  re-running this notebook should get this trace" is withdrawn: re-running gives
  the same kind of trace, not the same one.
- The onlooker objected at cycle 40 ("repeating" ACTION1 since 36) and the mind
  thought on it twice; moves `1:16 2:15 3:14 4:15`; 0 levels.
- Two thoughts failed on an indented code block (`IndentationError`), as in the
  run before.

### What the mind is told becomes a prior; the mind proposes, the self answers (Plone, same day)

Two corrections from Plone, done as one package with the neutral prompt:

- **The prompt is a prior.** "Bản chất prompt cũng có khác gì datum có tag
  'prior' đâu." The words the model was given lived in code: in no store, under
  no tag, in no `[event]` line, in no program's `built_from` — a side door. They
  are now `prior:mind-task` (`src/arc3/task.py`), admitted through the
  tagging-gate with the rules, tagged `source: dil-arc3` because they are this
  project's words and not the competition's. The mind asks for them at its first
  arrival; a thought that comes before they arrive waits for them; every program
  names them in `built_from`.
- **Neutral, with the aim.** The scored games are unseen and all of them are
  played, so the words name no kind of game or mechanic — the old hint "what
  moves, how far, what blocks it" was written while looking at `ls20`. They give
  the aim, to get through the levels, and the task that serves it. The grid's
  size is read from the frame. The game's report shows only when it is news (a
  level, a change of state); asking memory is one sentence. Built on the plain
  prompt, which measured well; the full prompt is removed.
- **The mind proposes; the self answers.** "Mind đâu hành động, nó chỉ tính
  toán, tìm ra hướng đi, có kỳ vọng và đề xuất hướng đi, rồi self tạo ra hành vi
  để đáp ứng đề xuất đó thôi." Earlier text here said the mind "chooses nothing"
  and that a model picking the move breaks INV-8; that conflated proposing with
  acting. The model now also writes `propose(grid)`; each cycle the mind runs it
  on the state the game stands in and reports `proposed:action:k` (and ACTION6's
  cell) to the field. The self answers a proposal the region affords before
  curiosity and want; with none, it chooses as before. What judges a proposal is
  the region's return, which scars the program when it does not hold — the mind
  never scores its own proposal.
- A code block indented as a whole now loads (two thoughts were lost to it).

258 tests. Six live cycles with no model: the mind asked `{"domain":
"mind-task"}` at cycle 0 and its waiting thought ran at cycle 1, when the task
arrived.

### The mind commands as T5's test; the body carries out; nothing weighs for it (Plone, same day)

Three corrections from Plone, done as one package:

- **Curiosity, want and expectation arise in the mind's thinking; they are not
  written.** "Chỉ cần model tư duy theo đúng chỉ thị thì 'curiosity',
  'expectation' và 'want' sẽ là hệ quả, không cần phải gắn cứng." Gone: the
  per-action `resolved`, `progress` and `valence` readings the mind computed,
  `region_valence`, and the policy that composed them (`−(progress +
  valence)`).
- **The self is located nowhere.** §2: "Host, self, and agent are one motion at
  three descriptive levels, not three entities"; §7: "The self is not a part the
  host supplies". `respond.py` had been called the self's policy. The word is
  gone from `src/arc3` and its scripts, except Python's `self` and the protocol's
  `SELF_WRITTEN` (Plone approved both); `self:move` is now `agent:move`. `src/dil`,
  a port of dil-core, keeps the protocol's own vocabulary.
- **The body carries out what the mind commands.** "Cơ thể thu nhận dữ liệu từ
  môi trường, mind đọc và xử lý dữ liệu đó rồi có kỳ vọng, tò mò và mong muốn,
  rồi kiến tạo hành vi, ra lệnh cho cơ thể, cơ thể thực hiện lệnh." And: "Khi
  mind chưa xuất lệnh, cơ thể có thể đơ để đợi."

**A defect found on the way.** The proposal of the run before went to the field,
and a contribution to the field takes effect at the next cycle (INV-7): the
mind proposed from cycle N's grid and the move was made at cycle N+1, on another
grid. The four-game notebook running with it (kernel `dil-arc3-run` v5) was
cancelled at Plone's word; its behaviour meant nothing. §6.4 already had the
road: "T5 emits a *test*: an action that pushes to the region to see whether the
return matches the Expectation just built." Done in dil-core first (`a8ef7ce`,
changelog `f7d912c`, 373 tests; no protocol change): the predict rule may call
`test(action)`, recorded from T5 with register ↔, handed to the host as
`CycleResult.tests`. Ported, with `RespondContext.tests` so link 5 sees the
cycle's own tests (a deviation, declared).

- `src/arc3/command.py` replaces `respond.py`: the body commits the mind's last
  T5 test if the region affords it (RESET always), RESET at cycle 0 (§4, start-up
  is the host's), and otherwise waits — a `wait` reaches no engine, nothing comes
  back, and the run ends. No action is made up in the mind's place.
- The mind commands when the region has said all it says in a cycle; it sees
  what the region offers. With no command it can give, it thinks again while
  the body waits, at most `MAX_WAIT_THOUGHTS = 2` (declared, not measured).
- The model is replaceable: the endpoint takes `extra` for whatever the served
  model needs (Qwen's `enable_thinking`), and the mind knows no model.
- The plain prompt and `--prompt` are gone: a mind that writes no `propose`
  gives no command, and the body would stand still at cycle 1.

242 tests. Six live cycles with no model reachable: RESET at cycle 0; at cycle
1 the mind had no program, thought twice for a command, the model failed both
times, and the body stood still.

### Four games under the command design: one move, repeated (2026-09-25)

Kernel `dil-arc3-run` v6, on `e846c19`; the dataset was checked served (77 files,
`src/arc3/command.py` among them) before the notebook was pushed. Qwen3.6-35B-A3B,
no thinking, 60 cycles a game; ar25 and sk48 were drawn at random from the unseen
games. Read back from each game's store (`[event]` and `[data]`), since the run's
own summary broke (below).

| game | cycles | what was committed | cells the moves changed | thoughts | levels | wall |
|---|---|---|---|---|---|---|
| ls20 | 60 | RESET, ACTION3 ×58, ACTION1 ×1 | 52 for three steps, then 2 (the step bar) | 25 | 0 | 1,245 s |
| vc33 | 52 | RESET, ACTION6 (32,1) ×50, wait | 1–2 each step | 23 | 0 | 973 s |
| ar25 | 60 | RESET, ACTION6 (20,16) ×59 | 0 every step | 2 | 0 | 63 s |
| sk48 | 60 | RESET, ACTION6 (28,50) ×59 | 0 every step | 2 | 0 | 74 s |

- **Every game: one command, repeated.** `propose(grid)` reads the grid alone,
  so on a grid that returns the same, it returns the same.
- **Where nothing moved, nothing was surprising, so nothing was thought.** In
  ar25 and sk48 the program expected the click to change nothing, and it
  changed nothing: 60 of 60 frames held, no frame scar, two thoughts in 60
  cycles.
- **The onlooker's objection changed nothing.** It said "repeating" on 51–55
  cycles; its stance changed, and so scarred, twice a game. The mind thought
  on it, but a candidate is adopted only when it predicts better, and a
  candidate that predicts as well is not adopted however differently it would
  act.
- **vc33 ended as declared.** After 50 clicks the state was `GAME_OVER`. The
  mind commanded no RESET, the body stood still, and the run ended at cycle 51.
- Some thoughts ran to the 12,288-token cap and returned no code (ls20 and
  vc33).
- C5 and C7 pass on ls20 and vc33. They are partial on ar25 and sk48: one
  resistance source, 2 collisions < window 8. C4 is partial on all four when
  checked from the durable log ("cycle-marks not monotonic"); not examined yet.
- **Fixed:** `run_game.py`'s summary read every T5 emission as a store query,
  and a test emission has no `cue`. `KeyError` came after the per-cycle lines,
  so the summary lines after it were lost in all four games.

About 45 minutes of kernel (08:45–09:30 push to complete); GPU quota not checked.

### The onlooker's objection can be met by acting otherwise; `propose` reads the steps (Plone, same day)

Two changes Plone approved after the four-game run, and a defect found while
making them:

- **Adoption.** When the mind thinks because the onlooker changed its stance, a
  candidate that predicts as well as the held program, and can command, is kept.
  The objection is to how the agent acts, and it is met by acting otherwise; before
  this change a program had to predict *better*, so an objection could never
  change a move.
- **`propose(grid, steps)`.** The program reads the steps the mind has just seen,
  as well as the grid: its short-term perception (`BASELINE_WINDOW = 16`). Each
  step gives the grid before, the action, the grid after, and the state and
  levels the region reported. On a grid that does not change, a program can now
  act on what it has already tried. A `propose(grid)` still runs. The prior's
  words (`prior:mind-task`) now describe `steps`, and name nothing else new.
- **Defect: the program could not propose RESET.** `run_propose` accepted ACTION1–7
  only, although the body and the prior both offer RESET (0). This is part of
  why vc33 stood still after `GAME_OVER`. Fixed: 0 is accepted, and so is
  `"RESET"`. A cell given with an action other than ACTION6 is dropped, not
  refused; before, the body refused the whole move and waited.

245 tests.

### Qwen3.8-Flash-Next NVFP4 on Kaggle, with the onlooker's adoption and `propose(grid, steps)` (2026-09-25)

**Serving.** The model is `RadixArk/Qwen3.8-Flash-Next-NVFP4` at `7b71922`, as
copied to Kaggle (`keithtyser/qwen3-8-flash-next-nvfp4`). All 419 files
(135,253,622,894 bytes) were checked against Hugging Face's hashes, in 159 s. The
vLLM is the image built for this model (`vllm/vllm-openai:qwen38-flash-next`,
`0.1.dev20073+g8e685d198`), from its layers on Kaggle, each checked against the
runtime manifest; extraction took 118 s. The PLE n-gram embedding is kept in host
memory (`VLLM_PLE_CPU_OFFLOAD`). The gate that selects its FP8 loader under an
NVFP4 config is this project's own, written against the stock file's hash. How to
run it came from a public notebook (Tufa Labs' Duck harness as served by
keithtyser), not from the model card, whose command uses eight GPUs.

- The machine: one RTX PRO 6000 (97,887 MiB) and 176 GB of RAM, 174 GB of it
  available.
- **I first concluded that it could not fit, and that was wrong.** I had assumed
  every weight on the GPU.
- **Two kernels failed before it served.** v7: the lookup for `libcuda.so.1`
  read `ldconfig` only, and found nothing. v8: the weights took 81.8 GiB, loaded
  in 603 s; at a 0.92 share that left 2.29 GiB of KV cache, short of the 2.37 GiB
  one 64K request needs. Fixed by setting the KV cache outright, at 5 GiB.
- v9 ran. Four games, 60 cycles each, no thinking, temperature 0.2. The kernel ran
  from about 12:12 to 13:05. The GPU time of all three kernels was not read from
  Kaggle's quota page.

**This run changed the model and the mind at once**, so what changed below cannot
be put on either one alone.

| game | commands | frames held | thoughts | levels | end | wall |
|---|---|---|---|---|---|---|
| ls20 | ACTION1 ×13, then ACTION2/ACTION1 alternating (38 + 21) | 46/60 | 21 | 0 | NOT_FINISHED | 480 s |
| vc33 | ACTION6 ×50, sweeping x 60–63, y 24–28 (18 cells), then a wait | 25/52 | 29 | 0 | GAME_OVER, the body stood still | 413 s |
| ar25 | ACTION4 ×59 | 48/60 | 13 | 0 | NOT_FINISHED | 201 s |
| sk48 | ACTION4 ×58, ACTION1 once | 24/60 | 37 | 0 | NOT_FINISHED | 750 s |

- **The program predicted its own loop.** In ls20, from cycle 20 to 50 every frame
  held while the piece moved up and down. There was no mismatch, and so no
  thinking, and the loop went on. `predict` meets the region; `propose` states no
  expectation of what the move will reach, so the aim, which lives only in the
  prior, never meets a mismatch.
- **The onlooker's adoption worked where it applied.** ls20 at cycle 6: the
  candidate predicted 5/5, the same as the held program, and was kept. At cycle
  56 it was 15/15 against 15/15, and was kept. At cycle 59 it was 8 against 15,
  and was not.
- **Where it did not apply: at most one thought a cycle.** In ar25 the
  onlooker's stance changed at cycle 5, a cycle whose thought was already
  counted as "frame", so the "predicts as well" rule did not apply. The stance
  then held for 55 cycles, and held stances do not collide. From cycle 13 the
  moves changed nothing, the program expected nothing, and there were no more
  thoughts.
- **vc33: the program now explores, and still did not reset.** It clicked a 4×5
  block of cells in order, three times over, until `GAME_OVER`. It then commanded
  ACTION6, which vc33 still offers in a terminal state. The mind checks a command
  against what the region offers; the body also refuses a non-RESET move in a
  terminal state. So the mind thought it had commanded, and the body waited. The
  steps `propose` read said `GAME_OVER`; the program did not act on it.
- ls20's four status mismatches (cycles 8, 15, 51, 52) are `depthDelta ±5`, the
  frame's stack changing depth, not levels.
- **Five thoughts did not load.** Four were "unterminated triple-quoted string"
  at line 2 of `<world-model>`, and one was prose inside the block. The model's
  raw answer is not kept, so why is not known. The suspect is `extract_code`
  pairing fences wrongly when the answer holds more than one.
- The model asked the store once in four games (ar25: scarred remarks, running
  frames).
- C7 fails on ar25 and sk48 (one resistance source over the last 8), and passes on
  ls20 and vc33. C4 is partial on all four, not examined.

### What a command is for meets the region; the answer is kept; mind and body agree on the game's end (Plone, same day)

Four changes Plone approved after the Flash-Next run:

- **`want`.** `propose` may return `(action, x, y, want)`: cells of the next grid
  and fields of the region's next report that the action is for. `want` joins
  the program's expectation of the step the command makes. When the grid comes
  as `predict` said but the wanted cells do not, or the report differs only in
  what was wanted, the mind thinks on `want`. A candidate that predicts as well
  and can command is then kept. The prior describes the form and names no
  strategy.
- **The onlooker's change of stance is thought on in its own right**, even in a
  cycle already thought in. In ar25 it came in a cycle whose thought was
  counted as "frame", and the rule for the onlooker never applied.
- **Every answer is kept whole** as the mind's datum (`domain: mind`,
  `kind: thought`), built from what the model was shown: the text, what was kept,
  the note, and the reasoning when the model gives one. It is evidence for a
  later thought only when the model asks for it.
- **A command the body would not carry out is no command.** The mind now
  refuses, as the body does, any action but RESET once the game has ended. vc33
  still offers ACTION6 after `GAME_OVER`; the mind took that as a command, and
  the body waited.

And one fix on a suspicion. A code fence now closes a block only at the start of
a line, so a fence inside a docstring no longer cuts the program. Four thoughts
had been lost to "unterminated triple-quoted string" at line 2. That this was
the cause is not confirmed; the answers were not kept then, and they are now.

249 tests.

### The mind holds an aim; the onlooker stands in the world; standing still is a cycle (Plone, same day)

After the Flash-Next run, Plone asked why a mind given an aim held no expectation
of reaching it. The aim was words in the prompt, read only while the model
thought, and never made an expectation the loop held. Worse, the standing
expectation of the region's report was "as before": `levelsDelta 0`, not getting
through. Each step that got nowhere matched.

- **The mind always holds an expectation of reaching an aim** — whatever aim the
  task it receives has (Plone: not the levels of this game). The words are the
  mind's own prior, `prior:mind-aim` (`src/arc3/aim.py`), apart from the
  environment's task, and name no environment. When the task states no aim, the
  mind works one out and says it is its inference. The program writes `GOAL =
  {aim, source, reached_when, within}`. When the aim falls due it joins the
  program's expectation of that step; not reached then, or reached sooner, the
  mind thinks on `goal`. A program with no `GOAL` the region could show reached
  commands nothing.
- **Where a regress stops** (Plone warned of one): the mind thinks only on what
  comes from outside, or while the body waits; an aim must ground out in what
  comes back; standing still is said by the onlooker each moment, and costs the
  run's budget.
- **The onlooker is in the world, not in the host.** It had been a wrapper around
  the body's source, in `src/arc3/`, and read the level count and knew RESET.
  Now `src/world/` is what lies outside the agent: the region and the Others who
  see it act. The host touches the region and hears the Others on its own
  channel; it does not know what they are. The onlooker knows no game: acts are
  opaque. Its remarks are "standing still" (said anew each moment it lasts),
  "repeating", "back-and-forth".
- **A cycle the body stood still in is a cycle.** It had ended the run, so no
  Other could ever speak to a stalled agent. Now the host reports only what it
  hears, and T7 counts no absence of the region. The mind commands after the
  onlooker, and the body goes by the frame it stands on. Such cycles count
  against the budget and cost no action.

254 tests.

### A path to a scored submission (Plone, same day)

Plone: a submission is allowed each day, and two have gone unused. A submission
is a measurement on the hidden games. Nothing had been submitted but the starter
kit's random agent, because the notebook played only the offline games; a
scored rerun plays through the gateway.

- `scripts/run_competition.py` plays every game the arcade offers on one
  scorecard, each made once, `--concurrency` at once, with a deadline, as the
  official harness does. Each game runs in its own process (`run_game.py
  --remote`), reaching its game through `world/remote.py`: one arcade, one
  process, plain data both ways.
- The notebook's run cell waits for the gateway in a scored rerun. Otherwise it
  plays the chosen games offline and writes the placeholder submission.
- Checked here: two offline games at once through the served region, the
  scorecard closed; the deadline stopping a running game and starting no other.
  With no model reachable, each game stood still for 5 of its 6 cycles, the
  onlooker saying so each time.
- **Not checked, and only a scored rerun can check it:** the gateway, the
  scorecard driven from several processes' requests, and whether ~110 games fit
  in 9 h at 4 at once.

256 tests.

### "world-model" out of the live code (Plone, same day)

Plone asked why "world-model" was still in the code. It had stayed from
2026-09-24 (`13d5f9c`, "One mind, and it is the model"), when the program was
still called a world model. I had said I would rename the compile label and had
not done it.

- The program's datum is now tagged `domain: mind` (was `world-model`), beside the
  mind's answers (`domain: mind, kind: thought`). Stores from earlier runs keep the
  old tag.
- The label the program is compiled under, which shows in its errors, is
  `<program>` (was `<world-model>`).
- Kept: the fixtures in the tests ported from dil-core, which use dil-core's own
  words (`built-from`, `held-by`, `time`, `write`); and the probe scripts of
  2026-09-24 (`wm_probe.py`, `compare_programs.py`, `build_probe_run.py`), which
  name what that experiment was.

256 tests.

### The prompt said the game offered an action the mind refused (vc33, kernel running)

Read from vc33's report in the aim run, before the kernel finished. `GAME_OVER` came
at cycle 51. For the 9 still cycles after it the mind thought 27 times, "no
command" and the onlooker's nudge. Each time the model answered ACTION6, 1,626
tokens, the same answer. The prompt had said both "The game now offers: ACTION6
(and RESET, 0)", the game's own list, which vc33 keeps after the end, and "Your
propose gave no action the game can take now". The mind refused ACTION6 as the
body does, and told the model the list that allowed it. Now, once the game has
ended, the prompt says only that: "The game has ended (GAME_OVER): the only action
that can be taken now is RESET (0)."

Also seen there, not yet examined: 13 of vc33's thoughts did not load, all
"unterminated triple-quoted string". The string opens at line 4 of programs of
230–576 lines, or at the next-to-last line. The raw answers are in the run's store.
The aim fell due unheard: `predict` held 2 frames of 52, so every thought was on
the frame, the first part to fail. vc33 took 1,708 s, against 413 s in v9.

### The aim run, read from its stores (2026-09-27)

Kernel `dil-arc3-run`, code `fa83817` (before the rename and the fix for the ended
game): Qwen3.8-Flash-Next NVFP4, four games, 60 cycles, the mind's aim prior, the
onlooker in the world. Notebook 4,204 s. Outputs in
`scripts/data/kaggle/dil-run/output-aim/`. The first download was cut short when
the session ended; it was downloaded again.

| game | commands | frames held | aim held | stood still | levels | wall |
|---|---|---|---|---|---|---|
| ls20 | ACTION2 ×58 | 55/60 | inferred, `levelsDelta 1` within 10 | 0 | 0 | 348 s |
| vc33 | ACTION6 ×50, then none | 2/52 | inferred, within 10 | 9 cycles after `GAME_OVER` | 0 | 1,708 s |
| ar25 | ACTION1 ×5, then none | 2/7 | none after cycle 7 | 54 cycles | 0 | 927 s |
| sk48 | ACTION6 ×59 (the cell moved once) | 60/60 | inferred, within 5 | 0 | 0 | 89 s |

- **The aim was held and met the region.** Every game's model stated an aim,
  `inferred`, as reaching a level. In ls20 it fell due every 10 actions and the
  mind thought on `goal` at 17, 27, 37 and 57; in sk48, 8 times. **Behaviour did
  not turn**: each candidate predicted as well, was kept, and proposed the same
  action.
- **ar25 lost its aim and stood still for 54 cycles.** At cycle 7 a better
  predictor with no `GOAL` was kept, and the aim went with the program it
  replaced. 108 "no goal" thoughts followed, and none wrote a `GOAL`: each
  revised the held program, which had none, as the last message asked ("Revise
  your functions"). The note that it had no aim sat at the head of the first
  message.
- **vc33 after `GAME_OVER`**: see the entry before; fixed in `330ea56`.
- **The unterminated strings, read from the kept answers** (vc33, 13):
  - 6 answers opened a block, thought inside a docstring they never closed,
    then began a whole new block and closed it. `extract_code` took from the
    first opener to the only closer.
  - 7 wrote one block whose docstring never closed.

Fixed (Plone approved the first two):

- **The aim is the mind's.** A program that states one replaces it; one that
  states none leaves the mind the aim it held.
- **Why an answer was not taken is said to the model**, in the last message:
  why a `GOAL` was not taken (`goal_check`), or why the code did not load. The
  feedback now asks to revise "predict, propose and GOAL".
- `extract_code` reads the last block that opens and closes.
- `run_game.py`'s summary lists the program's moves apart from the answers.

259 tests.

### A review of the repository against its own documents (Plone, 2026-09-27)

Plone passed on a review. I checked each point against the repository, reproducing
where it could be run. All held, but for two counts: the reproduction gave 3
prompts, not 8; and 21 scripts import removed code, not 23 (the difference was
not traced).

- **The competition's rules reached every prompt unasked.** T3 asks the store by
  each arrival's description (`{"sense":"vision"}`, `{"object":"region-status"}`,
  `levels`, `actions`). The mind put every store return into "What you recalled
  from memory" and into `built_from`. So each prompt carried `prior:directive`
  ("You are playing a game. Your goal is to win."), the level rules, the cost,
  and the actions ("semantically mapped to up"), cut at 600 characters. This
  contradicted "the mind reads by asking" and the neutral task. **Plone chose:**
  only what answers a cue the model asked reaches its prompt. T3's recall stays,
  and is traced. Recalled items are cut at 4,000 characters now, and say so when
  cut. Reproduced after the change: no recalled section, and `built_from` holds
  only the frames, the task and the aim.
- **ACTION6 with no cell**: `propose` returning `(6,)` was a command to the mind
  and a wait to the body. The body's rule is now one function,
  `command.can_carry_out`, which the mind asks. That is the second time the rule,
  written twice, parted.
- **A program asked for was swallowed**: `take_return` dropped every `program`
  return. What the model asks for, program or its own earlier answer, it now
  reads.
- Documents brought to what holds:
  - README: the status, what it is told, the roles (now CLAUDE's four, with the
    world outside them), what the mind is, finding 7, the layout (`src/world/`).
  - Docstrings: `prior.py`, `host.py`, `run_game.py`. "character" becomes
    "agent"; it is not the protocol's word.
  - Tag H's pointer to the dead `standing_status`, now removed.
  - The affordance comment in `cycle.py`.
  - `wm` becomes `mind` in `run_game.py`.
  - `CUE_KEYS` is derived from `OPEN_TAG_KEYS`.
  - `scripts/README.md` gains `run_competition.py`, `push_dil_run.py`,
    `make_manifest.py` and the new arguments.

262 tests.

### Rethought on how it acts, the same action is not kept (Plone, same day)

In the aim run each rethought program predicted as well as the one it replaced,
and was kept, and proposed the same action. For the reasons about how the agent
acts (the onlooker, a want, an aim the region refuted), a candidate that only
predicts as well is now kept only if its `propose`, from where the game stands,
gives another action than the held program's. When it does not, the model is
told: "it proposed ACTION1 again, the action the program you hold proposes now…".
A candidate that predicts better is kept as before. Which other action is the
model's.

263 tests. Not in the notebook that runs tonight (built on `c7a2257`); it goes
into the next one.

### The first submission of dil-arc3 (2026-09-26, UTC)

Plone asked for a submission that day, with the fix for "rethinks but acts the
same" in it and no full re-run. Kaggle submits only a notebook version that has
run to the end, so two versions ran:

- **v11** (`c7a2257`, before the fix), Save & Run on four games offline, 60
  cycles each, **4 at once, through `run_competition.py`**. Server ready in
  820 s. The four games together took **388 s**: ar25 384 s, ls20 306 s, sk48
  154 s, vc33 90 s. All exited 0, none stood still, no level; 1,512 s of notebook.
  This was the first run of the parallel path on Kaggle. It was kept as the
  fallback.
- **v12** (`3b31806`, with the fix), Save & Run on ls20 alone to be quick. Server
  ready in 690 s; ls20 took 1,261 s, 53 answers kept, 5 not taken, no level;
  2,281 s of notebook. The new rule acted at once: at cycle 5 a candidate that
  proposed RESET again was not kept, and the model was told why. The commands
  went RESET ×10, ACTION1 ×2, then ACTION2.
- **Submitted: v12**, at 20:42:04 UTC, ref `56588469`, "dil-arc3 3b31806: DIL
  loop, Qwen3.8-Flash-Next NVFP4, 60 cycles a game, 4 at once". The scored
  rerun goes through the gateway branch, which no run before it could exercise.
- **Timing risk, not measured on the scored run.** ls20 alone took 1,261 s in v12
  and 306 s in v11. At 4 at once, ~110 games at v12's pace would not fit in 9 h;
  the deadline (9 h less 20 min) stops what runs and starts nothing more, so the
  notebook should end in time with fewer games played.

#### v11 and v12, game by game (read from their reports and stores, 2026-09-27)

| run | game | commands | frames held | thoughts (kept) | aim inferred | wall |
|---|---|---|---|---|---|---|
| v11 | ar25 | ACTION1 ×59 | 54/60 | 13 (8): frame 6, goal 5 | clear the grid to background, within 10 | 384 s |
| v11 | ls20 | ACTION1 ×59 | 54/60 | 15 (7): frame 6, goal 5, status 2 | move the block pattern from bottom to top, within 10 | 306 s |
| v11 | sk48 | ACTION6 ×59 | 60/60 | 16 (16): goal 8, onlooker 7 | put the keys into the doors, within 5 | 154 s |
| v11 | vc33 | **RESET ×59** | 60/60 | 13 (13): goal 11 | trigger completion via the key blocks, within 5 | 90 s |
| v12 | ls20 | RESET ×10, ACTION1 ×2, ACTION2 ×47 | 12/60 | 53 (3): frame 48, onlooker 3 | reach the exit, within 10 | 1,261 s |

- v11 is before the "act otherwise" rule, and every game is one action. Each aim
  that fell due was rethought and a program kept, and it proposed the same
  action.
- **vc33 in v11 commanded RESET 59 times.** Its `propose` returns
  `(6, x, y)` when it finds the target it looks for, and `(0, None, None)`
  otherwise. It never found it, and RESET is always carried out. A RESET
  predicts itself, so no frame failed and only the aim fell due. Under v12's rule
  those rethoughts would not keep the same RESET.
- ar25 in v11 is the first run in which the model asked its memory:
  `{"kind": "thought", "provenance": "scar"}`.
- v12's ls20 predicted poorly (12/60), so 48 of 53 thoughts were on the frame.
  The "act otherwise" rule applies only to the onlooker, want and goal. It acted
  once, at cycle 5 (RESET again, not kept). At cycle 12 an aim that fell due was
  met by a program that acted otherwise.
- **Still there in v12**: 2 answers "unterminated triple-quoted string", after
  the last-whole-block fix. They are single blocks whose docstring never closes:
  the model's own. 2 answers ran to the 12,288-token cap with no code.
- C7 passes in v12 (6 onlooker scars); it fails in every v11 game.

### Two bugs in what the mind is told, and the documents set to the submission (2026-09-27)

Plone passed on two more findings. I reproduced both before changing anything.

- **The mind read its own writes as memory.** A datum the mind writes comes back
  through the store's channel in the same form as a store answer. `_answers`
  matched it to the model's `ASK` by tags alone. Asked at cycle 0 for
  `{"kind":"thought"}` and `{"kind":"program"}`, when the store held neither, the
  next prompt showed "an answer you gave" and "a program (version 1)", and
  `written-0-0` and `written-0-1` entered `built_from`. That is against "memory
  is what the store held before the cycle that asks".
  - Fix: the mind keeps a fingerprint of each payload it writes. When that
    payload comes back, it is an echo, not an answer. A real answer to a
    question asked in cycle N holds only what the store held before N, so it
    cannot be a write of N.
  - My own test of yesterday had pinned the bug: it asked at cycle 0. It now
    asks when the program is in the store.
- **A kept program was reported as not taken.** A program kept without a
  `GOAL`, or with one refused, carried that as its note, and the next prompt
  said "Your last answer was not taken". Now the model is told what happened:
  either "not taken: why", or "the program was kept; its GOAL was not taken:
  why". `run_game.py` counts "program not taken" by `kept`, not by note.
- A candidate whose `propose` gave nothing had been told "it proposed ACTIONx
  again". It is now told "its propose gave no action from where the game stands
  now".
- CLAUDE.md now names the model the submitted notebook serves (Qwen3.8-Flash-Next
  NVFP4), and records the submission: v12, `3b31806`, ref `56588469`.
  `build_dil_run.py` defaults to `flash-next`.
- These fixes are not in the submitted v12. That notebook is as `3b31806` has it.

265 tests.

### v13 and v14: the patched notebook on four games (2026-09-27)

Code `af72f78`: own writes are echoes, truthful kept notes, and the rules before
it. Save & Run on four games offline, 60 cycles, 4 at once. Not a submission.

- **v13 failed on Kaggle's hardware**: `CUDA error: uncorrectable ECC error
  encountered` while loading weights. Everything before it was sound (419 files
  checked, runtime extracted, all shards loaded). The engine died, but cell 5
  waited its full 1,800 s before failing: it should fail on "Engine core
  initialization failed" in the log. Not yet changed.
- **v14**, the same notebook pushed again: server ready in 930 s, the four games
  in 946 s, 2,241 s of notebook. No level.

| game | commands | frames held | thoughts (kept) | not taken as "the same again" | wall |
|---|---|---|---|---|---|
| ar25 | ACTION6 ×7, ACTION1 ×52 | 54/60 | 10 (4) | 1 | 292 s |
| ls20 | ACTION1 ×12, ACTION2 ×36, ACTION1 ×11 | 37/60 | 36 (6) | 6 | 851 s |
| sk48 | ACTION6 ×12, ACTION1 ×25, ACTION6 ×9, ACTION7, ACTION6 ×12 | 48/60 | 35 (11) | 10 | 941 s |
| vc33 | ACTION6 ×50, none ×4, RESET ×5 | 38/56 | 42 (26) | 9 | 853 s |

- **Behaviour turns in every game now.** Before `3b31806` each game kept one
  action; here each changes action at least once. The rule refused 26
  candidates that proposed the same action again.
- **vc33 got out of `GAME_OVER` by itself**: 4 cycles standing, then RESET. The
  prompt no longer names the stale list of actions.
- **No write was built from the mind's own echoes**: 0 of 165 written data name
  a `written-` datum in `built_from`. ls20 and sk48 asked
  `{"kind":"thought","provenance":"running"}`, and read only what the store held
  before the question.
- Still there: 4 answers with an unterminated docstring, 2 at the token cap.
  ar25's aim said `within: 150`, longer than the run, so it never fell due: the
  declared limit on `within`.
- C7 passes on ar25, ls20 and vc33, and fails on sk48.

### The onlooker says a repetition again; propose may look ahead (Plone, same day)

Plone approved two of three directions after v14 (the third, thinking on, was not
chosen). `1710630`:

- **The onlooker says "repeating" again each `REPEAT_AT` more acts** while a run
  lasts, with `at_least` 4, 8, 12… Said once and then held, it let ar25 repeat
  ACTION1 52 times in v14 with 10 thoughts in all. Between nudges it holds what
  it said, so a run kept on purpose is not stopped at every act. The cadence is
  declared, not measured. "back-and-forth" is unchanged.
- **The model is told `propose` may call its own `predict`** to look ahead toward
  what `GOAL` says will come back, and that each run of either must end within
  `PROGRAM_SECONDS` (2). They share one namespace, so this was possible before
  and never said. Plone: a capability of the program, not a strategy for a kind
  of game.

268 tests. Offline run v15 (four games, 60 cycles, 4 at once) pushed at 05:01 UTC.

### Documents set to the runs; the server wait fails fast (Plone, same day)

Plone passed on a review; each point checked against the repository and held.

- README's status said behaviour "keeps to one action", and finding 7 that the
  rewritten program "proposes the same action". Both predate `3b31806`: v12's
  offline ls20 went RESET, ACTION1, ACTION2, and v14 changed action in every
  game. Both now say what holds, and keep apart what the submitted code did and
  what the code after it did. One figure in the review was corrected: v14's
  games took 292–941 s, not 851–941 s (ar25 took 292 s).
- CLAUDE.md timed games from v9 (201–750 s alone). It now gives v11, v12 and
  v14, and what they mean for ~110 games: about 7 h at v14's pace, about 9.6 h at
  v12's ls20 pace, so only part of the games may be played before the deadline.
- **The server wait fails fast.** In v13 the API server raised "Engine core
  initialization failed" at 00:53:32 and did not exit, so `server.poll()` stayed
  None and the cell waited its 1,800 s. The wait now reads the log each round and
  stops on that line or "EngineCore failed to start". Checked on the logs kept:
  it matches v13's and not v14's. v15, already running, has the old wait.
- Two more from Plone. The old models' server wait (`< 1200`) had no `else`:
  when time ran out it printed "server ready" and went on. It now fails, as the
  flash-next wait does; both variants build and parse. A line of CLAUDE.md that
  the onlooker edit left at 95 characters is rewrapped.

### v12 scored: 0.00 (2026-09-27)

Submission `56588469` (notebook version 12, code `3b31806`, submitted 2026-09-26
20:42:04 UTC) is COMPLETE, public score **0.00**, first seen at 05:34 UTC; it was
PENDING at 05:24. The starter kit's random agent scored 0.02 (`56462757`).

- What the scored rerun did cannot be read: Kaggle shows no log of it. How many
  of the games it reached before the deadline, and whether any stood still, is
  not known.
- 0.00 is shown to two decimals, so it does not by itself show that no level was
  completed; it shows the score is below 0.005.
- It is below the random agent's. The random agent takes up to 80 actions a game
  and resets on `GAME_OVER`; the offline runs of this code kept to one or two
  actions over long runs. Not a measurement of the scored run.
- COMPLETE shows the notebook ended and a submission was made. It does not show
  that the gateway recorded the games' actions: one scorecard driven from
  several processes through one arcade is still not verified, and a broken
  gateway path would also score 0.00. The two causes cannot be told apart from
  the score.

### A probe of the road the games go through (Plone, same day)

v12's 0.00 has two readings the score cannot tell apart: the agent played and
got nowhere, or the road its games go through lost their actions. Plone chose to
spend a submission on telling them apart.

- `scripts/random_game.py` plays the starter kit's random agent, as its
  `my_agent.py` and the harness write it: RESET when not played or over; else
  ACTION1..7 at random, not read from what the game offers, ACTION4 twice as
  likely in ls20, ACTION6 at a random cell; up to 81 actions; stop at WIN.
- `run_competition.py --player random_game.py` runs it on the same road as the
  agent: one arcade, one scorecard, each game in its own process through
  `world/remote.py`. `build_dil_run.py --probe` builds a notebook of it
  (`dil-arc3-gateway-probe`), CPU, no model.
- Already seen, before any submission: the offline scorecards record the actions
  made from the game processes. Locally, two games of the probe: 162 actions
  sent, `total_actions` 160 (RESET not counted). The kept Kaggle runs: v12's ls20
  49 (ACTION1 ×2 + ACTION2 ×47), v14 228. So the arcade-to-scorecard part of the
  road holds offline; the gateway, over HTTP in a scored rerun, is what the probe
  tests.
- Reading it: about 0.02 means the road holds and v12's 0.00 is the agent's;
  0.00 points at the road. The random agent's own 0.02 is one draw.
- Probe version 1 failed in its first cell: Kaggle unpacks `dil-arc3.tar` into
  the dataset, so the probe's search for the tar found nothing. It now finds
  `random_game.py` and copies the repository around it, as the main notebook
  does. Checked by running its cells here against the unpacked layout.
- **Submitted: probe version 2**, code `a86dbff`, at 2026-09-27 06:12:00 UTC, ref
  `56600038`. Its Save & Run played the four offline games through the road:
  81 actions each (RESET once, ACTION1..7 in between), no level, scorecard
  `total_actions` 320 (324 less the four RESETs). Not the agent: a submission
  the paper does not describe.

### v15: the repeated remark and the look-ahead line, on four games (2026-09-27)

Code `1710630`, Save & Run on four games offline, 60 cycles, 4 at once. Not a
submission. The four games took 2,204 s (v14: 946 s). No level.

| game | commands | frames held (v14) | thoughts (kept) | "the same again" refused | wall (v14) |
|---|---|---|---|---|---|
| ar25 | ACTION1 ×15, ACTION2 ×25, ACTION4 ×19 | 25/60 (54/60) | 55 (3) | 16 | 1,083 s (292 s) |
| ls20 | ACTION1 ×10, ACTION2 ×37, ACTION1 ×12 | 11/60 (37/60) | 71 (3) | 12 | 2,200 s (851 s) |
| sk48 | ACTION1 ×5, then ACTION2/ACTION1 alternating ×50 | 2/60 (48/60) | 62 (3) | 2 | 1,754 s (941 s) |
| vc33 | ACTION6 ×50, none ×5, RESET ×4 | 26/55 (38/56) | 63 (16) | 16 | 1,705 s (853 s) |

- **The look-ahead line was not taken up.** Of 251 answers, 2 have a `propose`
  that calls `predict`, and neither was kept (v14: 1 of 123). No program ran
  over its 2 s.
- **The repeated remark came, and did not turn behaviour much.** Onlooker scars:
  30, 30, 6, 40. Most rethinks it set off proposed the action already held and
  were refused (16, 12, 2, 16), so the held program went on. Runs of one action
  are still 10–50 long. sk48 moved from repeating into back-and-forth, which is
  not said again, and stayed there for 50 cycles.
- **Frames held fell in every game**, and the rethinks were mostly on the frame
  (35, 49, 58, 29) and not taken for not explaining better. Only 3 programs were
  kept in ar25, ls20 and sk48 (v14: 4, 6, 11). Not attributed: more varied
  actions meet more unfamiliar frames, and the run changed two things at once.
- **Time**: 55–71 thoughts a game against 10–42, and twice v14's wall time. At
  this pace 110 games would take about 17 h: most would go unplayed in a scored
  run.
- Still there: 8 answers with an unterminated string (ls20 2, vc33 6), 4 without
  a code block, 1 with no `predict`.

### The gateway probe scored 0.06: the road holds (2026-09-27)

Submission `56600038` (the starter kit's random agent on dil-arc3's road) is
COMPLETE with a public score of **0.06**, seen at 06:22 UTC, ten minutes after it
was submitted.

- **The road holds.** One scorecard, driven from a process per game through
  `world/remote.py`, was taken by the gateway and scored the levels the random
  agent completed. v12's 0.00 is the agent's own: it completed no level worth
  0.005, or too few games were played for it to show. Which of the two is not
  known.
- 0.06 against the starter's own 0.02 on the same rule: the difference is the
  random agent's draws (it seeds from the clock), not the road. Two draws; the
  random agent's score is somewhere around a few hundredths.
- The random agent completed no level on any of the four offline games, so
  those four cannot show whether an agent beats it.

### A mind that learns from nothing, in the one seat (Plone, 2026-09-27)

Plone: build a mind with no trained weights, whose thinking is an algorithm —
the loop, the store and the host unchanged. Two rules in CLAUDE.md were set to
his meaning first: "one mind" (which mind sits there can change); and nothing
computes curiosity, want or expectation on the mind's behalf ("cấm tính hộ,
không phải cấm code").

`src/arc3/learning_mind.py`: each transition it takes is learned and written
(`kind: transition`, built from the frame and report); an act taken again from
the same state is expected as learned, the expectation the datum's; a refuted
one is scarred and revised as no longer holding. It finds the region's clock —
rows that change whatever is done — and reads states without it (`kind: clock`).
It chooses: a path to a level gained before; an act not yet taken here, the
least known kind first (UCB1); a path to a state with one; RESET, or the state
visited least. ACTION6 clicks the things on the grid. Each choice is written
(`kind: choice`) with why and what it was built from. `run_game.py --mind
learning`; `run_competition.py --mind`; `build_dil_run.py --mind learning`
builds a CPU notebook (`dil-arc3-learning`). 275 tests.

Offline, here, on the two games the starter kit ships:

- vc33, 150 cycles: **level 1 completed** — the first level dil-arc3 has
  completed. 400 cycles: level 1, no more (609 s, two games at once).
- ls20, 150 cycles: no level; 43 states, the four acts spread; clock rows 61-62.
  400 cycles: **level 1 completed** (ACTION1 gained it); 103 states; 698 s, two
  games at once.
- Fixed on the way, each general: the clock was found late while one act
  repeated (curiosity now favours the least known kind); a looser clock rule
  took the rows a moving piece crossed (now three kinds of act and at most two
  cells a row); RESET looped when nothing was left to try (now only after
  something new was learned).
- Not yet: README; a run on Kaggle (ar25, sk48); the time 110 games would take.

### The learning mind keeps the scar rhythm alone (Plone, same day)

Measured on the two 400-cycle runs above: each cycle was slower than the last
(0.45 s at the start, 3.02 s by the end, two games at once) and each store was
2 GB, 2.1 GB of it snapshots — one at the close of every cycle, because the
learning mind writes every cycle and the declared cadence commits every cycle
that writes, each snapshot holding the whole store. Plone chose to keep dil-core's
scar rhythm alone for this mind (option 1): it adds data rather than revising
one, and every write is in `[event]` already. `Daemon(commit_on_write=False)`;
`run_game.py` turns it off for `--mind learning`; the language mind keeps both.
276 tests.

ls20, 400 cycles, alone: **level 1**, 197 s, 0.21 s a cycle at the start and
0.96 s by the end; 67 snapshots; store 406 MB (363 MB snapshots, 36 MB `[event]`,
9 MB `[data]`). The frame is scarred almost every cycle (483 frame scars in 400):
the mind does not predict the clock, and a transition it holds carries the clock
as it was. So the scar rhythm still snapshots often.

Kaggle keeps up to 20 GiB in /kaggle/working (its notebook documentation); at
~0.4 GB a game, 110 games would not fit.
- Plone approved: in a scored rerun each game's store goes to /kaggle/tmp and is
  removed once the game has played (`run_competition.py --stores DIR
  --drop-stores`); the reports stay. A scored rerun's outputs cannot be read
  back, so nothing readable is lost; a Save & Run keeps every store. Checked
  here on two games.

### The learning mind on Kaggle: four games at once, 300 cycles (2026-09-27)

Notebook `dil-arc3-learning` version 1, code `b6836a0`, Save & Run on CPU, four
games at once, 300 cycles each. Not a submission. The games took 376 s of
notebook; 670 MB of output (snapshots still whole: it ran before the tree below).

| game | level | states met | clock rows | why it chose | wall |
|---|---|---|---|---|---|
| ar25 | 0 | 92 (92 grids) | none | not yet taken 299 | 290 s |
| ls20 | 0 | 77 (292 grids) | 61, 62 | not yet taken 239, path 59 | 353 s |
| sk48 | 0 | 74 (74 grids) | none | not yet taken 300 | 358 s |
| vc33 | **1** | 33 (283 grids) | 0 | not yet taken 261, path 21 | 333 s |

- vc33 completed level 1 on Kaggle too. ls20 did not in 300 cycles (here it
  took more than 150 and at most 400).
- ar25 and sk48: every grid a new state and every choice an untried act — each
  step reached somewhere new, so nothing was ever retried.
- At this pace ~110 games at four at once take about 110 / 4 × 367 s ≈ 2.8 h.

### Snapshots as a tree of objects, as git stores a commit (Plone, same day)

Plone asked why snapshots are heavy when a git commit is light. The marker is
light (~420 bytes); the payload was one JSON of the whole state per commit
(dil-core's choice 2-(a)), rewritten whole each time: 67 snapshots, the last
10.4 MB, in one 400-cycle run. Plone directed the fix in dil-core, then the port.

- dil-core `1096476`: every object or array of at least `MIN_OBJECT_BYTES` (1024,
  declared) is stored once under `objects/` by its sha256 and referenced from
  its parent; the root under `state/` is the snapshot's address. Unchanged
  subtrees are shared; each object is checked on read (a Merkle tree); a
  whole-JSON snapshot still reads. The protocol is unchanged: §9 asks for the
  entire system in an immutable, content-addressed marker; how it is stored is
  `DECIDE@IMPL`.
- Ported: `src/dil/store/commit_store.py`, and five tests to match dil-core's.
  281 tests.

### The tree measured; ar25 and sk48 read; curiosity in two steps (Plone, same day)

**ls20, 400 cycles, alone, with the tree** (code before the curiosity change
below): level 1; 67 snapshots as before; store **116 MB** (was 406 MB):
snapshots 72 MB in 1,052 objects and 67 roots of ~4 KB (was 363 MB), `[event]`
36 MB, `[data]` 9 MB. **Slower**: 292 s (was 197 s), 0.25 s a cycle at the start
and 1.26 s by the end (was 0.21 and 0.96). Each commit still walks and hashes the
whole state to find what changed, and tries to write each object it meets.
One run each; not repeated.

**ar25 and sk48 on Kaggle** (read from their stores):

- ar25 offers ACTION1-7, sk48 ACTION1-4, 6, 7. **No click did anything**: 0 of
  202 in ar25, 0 of 197 in sk48; 206 and 202 of their 300 steps changed no cell.
  Each thing on a grid is a kind of its own (colour and size), so each new thing
  was an untried kind, and curiosity kept clicking.
- ar25 keeps a counter in column 63 (rows 0, 1, 2, … turn 11 → 5), but not on
  every step that did something, so no clock was found; no grid repeated anyway
  (92 grids, 92 states).

**Curiosity in two steps** (general, as the rule for the mind's own
computation allows): first which action, over every kind of it (UCB1 on the
action's counts); then, for ACTION6, which thing to click (UCB1 on the kinds).
Clicking that never did anything anywhere is wanted less, however many things
are left unclicked. Test added: 282 tests.

### The tree, faster (Plone, same day)

Profiled on the last snapshot of that run (10.4 MB as one JSON): a put took
3.4 s, against 0.43 s to write it whole — the code visited every cell of every
grid (4.3 million calls) and serialized every row twice. Now each node's text
is built from its children's, bottom-up, and a row of plain values is written
in one call, found by its elements' types (checked in C). Same format: on two
real snapshots the root hashes and the objects are identical to before, and
the state reads back equal. A put of the last snapshot: 1.38 s (was 3.45 s).

ls20, 400 cycles, alone, end to end: **227 s** (whole snapshots 197 s; the first
tree 292 s), store **116 MB** (whole: 406 MB), level 1. A port-side
optimization: dil-core's format and names are unchanged. 282 tests.

### The one mind, neutral; the model is its computing (Plone, same day)

Plone: a model is the part of the one mind that computes — not a second mind,
not a second brain — and the mind's code is to be neutral about its region.
Checked first: `arc3/mind.py` was not. Beside the language model's own parts, it
named the region's report fields (`stateTo`, `levelsDelta`, `depthDelta`), its
ended states, ACTION6's cell, the frame payload's keys, the host's channels, and
imported the body's rule directly.

Now:

- `src/mind/` imports nothing from `arc3`. `mind.py`: the seams, when it thinks,
  want and aim, writes by handle, questions to memory, the onlooker, commands.
  `organs.py`: what a host declares of its eye and body. `models/base.py`: what a
  model is to the mind (it writes and asks nothing itself; it says what to).
- `src/arc3/organs.py`: this host's organs, every value read from its own code.
- `prior:mind-task` carries the task's aim in a form a mind that reads no text
  can hold: `{"aim": "get through the levels", "reached_when": {"fields":
  {"levelsDelta": 1}}}`. The words of the task are unchanged.
- **Step 3, the learning model** (`mind/models/learning.py`, from
  `arc3/learning_mind.py`, removed): the same algorithm, through the model
  interface. Checked against its moves recorded before the change: ls20 400
  cycles and vc33 150 cycles — after the start-up, every move is the same (398
  and 148 compared), and both complete level 1. What differs is the start: the
  mind commands nothing while it holds no aim, and the aim now comes from the
  task prior, answered the cycle after it is asked; so the body makes the host's
  start-up RESET at cycle 0 and waits at cycle 1.

282 tests.
- **Step 4, the language model** (`mind/models/language.py`): the program, the
  prompt, scoring and its rule for what it keeps of a revision (Plone: in the
  model, for now). `arc3/mind.py` now only seats it: the one mind, this model,
  this host's organs, and the helpers its tests reach for, bound to them. The
  region's values the model uses come from the organs; the words it writes to
  its model still speak of the game (ACTION{n}, RESET (0), hex grids), kept word
  for word. Checked: all 282 tests pass with no check changed (one test patched
  a module that moved), and one scripted run through the old code and the new —
  questions to memory, the onlooker's change, a level, another act, `GAME_OVER` —
  gave the same 10 prompts and the same 31 data, byte for byte.
- The flag stays `--mind language|learning`: `--model` is already the served
  model's name.
- **Step 5, a place for an API key** (Plone: designed now, left empty, so it is
  not forgotten): `ModelEndpoint.api_key_env`, the name of the environment
  variable, read when a request is sent into its `Authorization` header only.
  A test sends real requests to a local server: the header carries the key, and
  nothing written, logged or kept holds it; a missing key is named, not shown.
  CLAUDE.md gains "Kept for after the competition". 284 tests.
- **Step 6**: CLAUDE.md and README to the new layout — where the mind, its
  models and the organs are; the body's rule declared with the organs; the
  learning model in "What the mind is".

### A Save & Run packs its stores into one file (Plone, same day)

Since snapshots became a tree, a store is thousands of small files, and Kaggle
hands a notebook's outputs back one file at a time: learning notebook version 2's
download stopped at 1,439 files and 94 MB, with only one store complete. Now,
in a Save & Run, either notebook packs every `store-*` into `stores.tar.gz` and
removes the folders; the reports stay beside it. A scored rerun has no stores to
pack. Run here through the CPU notebook's cells on two games: five outputs, the
archive 409 KB, and both stores unpacked read every snapshot back.

### Learning notebook version 3 on Kaggle: the neutral mind, packed stores (2026-09-27)

Code `b928f28`, Save & Run on CPU, four games at once, 300 cycles, as versions 1
and 2. The four games took 414 s (version 2: 413 s).

- **The download took 13 s**: eight files, the stores in one 16.8 MB archive.
  Unpacked: 56-87 MB a store; every snapshot of all four read back in full (34,
  48, 68 and 39), each object checked against its name.
- **The same play as version 2**, but for the start: each game stood still one
  cycle while the mind waited for its aim, and made one more RESET (the host's
  start-up). Levels the same (vc33 1, the others 0); states met the same or
  within two (ar25 252, was 254); the counts of each act differ by one or two.

### Learning notebook version 4: 600 cycles, to find the ceiling (Plone, same day)

Same code as version 3, 600 cycles, four games at once. The four took 1,061 s of
`run_competition`; download 18 s (52 MB archive; stores 157-293 MB unpacked).

| game | level | states met | wall | s/cycle by 100-cycle block |
|---|---|---|---|---|
| ar25 | 0 | 497 | 670 s | 0.89, 0.93, 1.05, 1.14, 1.21, 1.29 |
| ls20 | **1** | 127 | 825 s | 0.92, 1.05, 1.17, 1.57, 1.91, 1.50 |
| sk48 | 0 | 378 | 1,050 s | 1.13, 1.49, 1.48, 2.12, 2.08, 2.08 |
| vc33 | 1 | 54 | 701 s | 0.90, 0.94, 1.01, 1.19, 1.32, 1.51 |

- ls20 completed level 1 on Kaggle, which it did not in 300 cycles.
- Toward the end fewer than four games ran at once, so the last blocks are
  faster than they would be with the queue full.
- What it means for ~110 games at four at once, the deadline at 9 h less 20 min
  (~31,000 s after start-up): at these four games' mean (811 s a game) about
  22,300 s (6.2 h); were every game as slow as sk48, about 28,900 s (8.0 h). A
  game that does not fit is not started, and scores nothing.

### Reading motion — tried, worse on ls20 so far; a review's seven points (Plone, same day)

Plone asked for the learning model to compute more. The diagnosis: it keeps
what an act did in one exact state and nothing carries over, so almost every
step reaches a new state (ar25 497 states in 600 steps). A first step toward
generalising, `mind/models/motion.py`: a thing that moves is the cells that turn
up a fixed displacement away (read from one step; ls20's piece is two colours
and moves five cells); from that, what each act does to it, what it moves on,
what stops it; and a search, in imagination, for a place it has not been.

Measured here, 600 cycles:

| run | level | actions to level 1 |
|---|---|---|
| ls20, without motion | 1 | 515 |
| ls20, with motion | 0 | — |
| vc33, with motion (it only clicks) | 1 | 81 |

- A first version asked ACTION1 306 times in a row: what it would move onto was a
  colour it had once moved onto and its own colour, so nothing new counted as a
  stop, and the imagined place stayed "not reached". Now an act that moved
  nothing from a place is not imagined from there again, and the transition
  learned there outranks what is imagined (Plone's review, point 1).
- Still worse: its imagination runs out after 49 steps. Counted in both ls20
  runs: without motion it met 48 places of the piece in 12 scenes (the grid with
  the piece lifted and the clock off), 123 pairs; with motion 36 places in 4
  scenes. Touching things changes the scene, and "a place not yet reached"
  ignores it; it also stops before any colour it does not know.
- So `motion` is off by default (`run_game.py --motion` turns it on).

Plone's review, and what was done:

1. The loop above (fixed as said).
2. The onlooker had no effect on the learning model. Now an act it says is
   repeated, or gone back and forth with, is put behind every other where the
   region stands, and the thought is written.
3. Its scars are almost always the clock's (Kaggle, 300 cycles: ls20 held 4 of
   299 whole, 125 off the clock; vc33 3 and 203; "no longer holding" 0 but for
   one in ls20 at 600). Said in the docstring, in CLAUDE.md's open items, and to
   be said in the paper.
4. "Reads by asking" and "short-term perception, never the whole history" are
   the language model's; the learning model keeps what it learned, all of it in
   the store (Plone chose this). The mind's right to read the store is the same
   for both.
5. Nothing is revised in place any more: a transition that no longer holds, and
   each version of what it learned of motion, is a new datum built from the one
   before (Plone chose this), so the scar rhythm alone keeps every version.
6. README: ls20 completed level 1 on Kaggle too, at 600 cycles.
7. Where it stands after the clock grows is read from the latest grid, not from
   the edge just taken; the aim is counted each time it comes, as tries are;
   `Context.missed` is typed as the dict it is.

Also seen: with the onlooker now heard, ls20 without motion took 515 actions to
its first level here, where it had completed it within 400 cycles before. One
run each; not attributed.

289 tests.

### A review of the onlooker's road, and three of its points done (Plone, same day)

Plone passed on five points. Each was checked against the code and the stores
of `scripts/data/motion-trial/` (code `8febb84`, 600 cycles).

**1. The onlooker's objection, as the learning model hears it** — checked, not
changed; Plone put the question on how the agent hears a remark and what it
does with it, not on the onlooker.

- In a cycle the remark arrives third (`signal-N-2`, after the frame and the
  status), and the mind commands on the status: in cycle 12 of m3-ls20-motion
  `[event]` has T5's test (ACTION1) at seq 855 and the remark's scar at 869.
  The command in the cycle an objection was heard was the act objected to in
  15 of 19 thoughts (m3-ls20-motion), 16 of 40 (m3-ls20-plain), 1 of 2
  (m3-vc33-motion).
- The objection is `(state, act)`, for the state it stands in when it hears.
  It stood there again the very next cycle after 1 of 19, 6 of 40 and 1 of 2,
  but came back later: in m3-ls20-motion 1,514 choices were made at an
  objected state and 1,456 took an act objected to there, every one "toward a
  state with an act not yet taken" — the branch whose path does not ask
  `_objected`. Also: "back-and-forth" objects both acts at one of the two
  states the alternation runs through; "all known" falls back to the objected
  acts when all are objected; `_plan`'s `unlearned` does not ask `_objected`.
- The review's example, ar25's ACTION1 ×52, was v14's and the language model's
  (said once, then held; fixed by `1710630`), not the learning model's.

**2. The remark in `built_from`.** The model was shown what the onlooker said,
and nothing named it. `Context.remark_unit` is the unit the remark came in: the
language model's answer names it whenever the prompt carries the remark, the
learning model's thought names what it objected on, and each choice that quotes
the onlooker names it. On ls20, 80 cycles, learning model: every choice that
quoted the onlooker (10; with motion 22) and every thought (4; 7) names a remark
datum in `[event]`.

**3. What the learning model does not write.** CLAUDE.md said all it holds is in
the store. Not so: its counts, how often a transition was taken and ended the
region (`seen`, `ended`, which the path reads), the states it visited, whether
it learned since its last RESET, and with motion where the thing has been, what
it touched, the colours that brought the aim and where it stuck. CLAUDE.md and
the docstring now say those are derivable only by replaying the observations
through the model, in order; no replay has been run.

**4. Where it stuck is held in its scene.** `_stuck` was keyed by place alone
and never cleared, so a place stuck before a door opened, or a level before,
stayed stuck. It is now keyed by the scene — the grid with the thing lifted
off, off the clock (`motion.lift`) — and a place stuck in one scene is free in
another. Not measured on a run (motion is off by default). A scene key made
before the clock grows is not read again under it, so what stuck then is
forgotten.

Found, not changed: `_reindex` re-reads `_edges` and `_here` under a grown
clock but not `_visits`, `_objected` or `_kind_of`, which are keyed by state.
In the three runs the clock grew once, at cycle 8, before any objection.

Point 5 (README) is open with Plone.

292 tests.

### The rule for history, kept; a line added to it (Plone, same day)

Asked whether `CLAUDE.md` lacked the rule or broke it: it broke it. The rule —
history goes in LOG; README and CLAUDE say only what holds now — has been a
hard constraint since `3612987` (2026-09-24), and eight passages were added
after it: run results (`8febb84`, `331525c`, `e9b74ea`), designs replaced
(`4583fad`, `683552c`) and corrections (`c7a2257`, `8febb84` — the last written
in this project's sessions by Claude). Others from 2026-09-22 had stayed when
the history moved out, three of them wrong now: Milestone 2's "there is no
running agent", "two signals a cycle" (the onlooker is a third), and that the
mind commands "once the region has said all it says" (it commands on the
status, before the remark).

The rule had a gap: it did not say what becomes of a fact about the world that
was established by a measurement and still holds. Plone added: such a fact stays,
stated as a fact, with where it was established in LOG; a result of this agent's
runs, a design replaced or a correction never does.

Done: the passages from 2026-09-22 are under that date above; the later ones
were in LOG already. `CLAUDE.md` keeps the facts and points to LOG; the three
wrong lines say what holds, and the learning model's objection says where it is
asked and where not. README's status and "What is measured…" paragraph, and its
learning model's levels, are out: what the agent has done is in LOG.

Not done, open with Plone: README's Findings are written as history (gaps
"verified by measurement, then fixed", "lost 62 of 66", "until `3b31806`"), and
finding 7 says "No level has been completed", which the learning model's runs
contradict.
