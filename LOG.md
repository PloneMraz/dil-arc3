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

### README's Findings as they were written this day, moved here on 2026-09-27

README's Findings, from `054b63b`, `147aab3` and `cf81f63` (2026-09-23), as they
stood when Plone had them rewritten to what holds now. Word for word; the
headings one level down.

Porting DIL from [dil-core](https://github.com/PloneMraz/dil-core) and running it
against a live environment turned up more about the protocol than about
ARC-AGI-3. These are the substance of the work rather than a side effect of it,
and they fall into three kinds — which is worth keeping straight.

##### Gaps between the protocol and its reference implementation

Each was verified by measurement, then fixed in `dil-core` first and ported back.
All five have the same shape: a channel present in the topology that nothing
drew on.

1. **The store was write-only.** §9 says "the self accrues from scars" and defines
   three provenance edges by which a scar returns. On a real run all three fired
   **zero** times: the loop called `data.put` once per cycle and never read
   anything back, so §10's resistance-retrieval channel was satisfied nowhere.
2. **The modulatory field was inert downward.** INV-7 has it reaching every layer
   as background — "same data plus a different field yields different meaning".
   No layer read it. Two of the eight did not even declare the parameter, and its
   only consumer was a single gain at the appraisal step.
3. **And inert upward.** "Every layer contributes to it as one competing
   parameter; contributions blend, never last-write-wins." No layer *could*
   contribute; the only caller was the driver, once per cycle, with one
   hard-coded key. With one contributor, blending is last-write.
4. **The top layer was a sink.** Nothing read T8's output: its relative values
   and its Other-to-Other interactions were produced every cycle and dropped.
   INV-1 forbids dead branches, and §6.2 says in as many words that "T8 closes
   back into the loop, not into a sink". The meaning-channel cannot carry T8's
   output back down, so it now returns through the field.
5. **Admitted, and never asked for.** Host data enters through the tagging-gate
   stamped `prior`, and §9 has it move to `running` "once it has run". Nothing
   ever asked for it, so it never ran. §6.4 already names the mechanism — "T3
   emits a *query*: it opens or calls a channel to ingest actively" — and the
   index is the open-tag layer §9 already requires to be consistent by key. T3
   now asks the store with the description of what just arrived; the answer
   comes back through T1 and runs every layer. Recalled on a cue, never poured
   in.

##### A property of the protocol's own design

6. **The experience store is a biased sample, by construction.** §9 admits only
   registered mismatches, so what it holds are the region's *surprises*. Asked to
   predict, it lost 62 of 66 contests against the model — not because it is
   wrong, but because an exception loses to a distribution. No verdict is
   involved anywhere: §9 is explicit that a scar "carries no claim of
   correctness". This is not a defect to fix; it is what an experience store of
   collisions *is*, and it means the store is right for driving change and wrong
   for answering what happens next.

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

### README's Findings rewritten to what holds (Plone, same day)

Plone: the Findings say what holds now about the protocol; the history stays in
LOG, which the paper can cite. Findings 1-6 as they were written are under
2026-09-23 above; finding 7, written in `331525c`, read:

> 7. **Behaviour turns, but reaches no level.** The mind holds an aim (`GOAL`,
>    inferred when the task names none) and meets it when it falls due; the
>    mismatch reaches the model, which rewrites its program. Until `3b31806` the
>    rewritten program proposed the same action. Since then, a rewrite made on
>    how the agent acts — the onlooker, a want, an aim — is kept only if it acts
>    otherwise, and in the offline runs since, every game changes action. No
>    level has been completed to learn from. Local to this repository, not
>    upstream's.

Each finding was checked against the code and the stores before it was
rewritten (the motion-trial stores and an 80-cycle ls20 run of the learning
model):

- 1 and 5 hold: `scar → running` 18 times in 80 cycles, 235 in 600;
  `prior → running` 6 times; T3 asked the store four times, once per
  description (`sense: vision`, and the status's three `object`s).
- **2 and 4 hold only in part.** Every layer receives the field, but its values
  are read in three places: T7's attention width (`strangeness`, `otherCount`,
  `contextNovelty`, `attentionGain`), appraisal (`appraisalGain`) and the fit
  floor (`fitFloor`). Of what is contributed, only T4's `strangeness` and T6's
  `otherCount` are read. T3's `channelActivity`, T5's `surprise`, T7's
  `silence`, T8's `interactions` and `resistanceConcentration`, and the
  driver's `resistance` are blended and carried and read by nothing. Nothing
  contributes `contextNovelty` since the counting mind went, nor `fitFloor`;
  `appraisalGain` is only the value the run starts with. T1 and T2 receive the
  field and a `contribute` and use neither. So T8 closes into the field, not
  back into behaviour. The README now says so.
- 3 holds (a convex blend per key, taking effect at N+1, T3-T8 and the driver).
- 6 holds; its figure (62 of 66) is under 2026-09-23.
- 7 was history ("until `3b31806`") and, in "No level has been completed",
  contradicted by the learning model. It is now two gaps that hold: with the
  language model, nothing in what is kept favours a program that reaches the
  aim; with the learning model, the onlooker is heard after the command and
  acted on narrowly (the review above).

### The field in dil-core, checked and rebuilt; a mind for dil-core (Plone, same day)

**dil-core had the same hole** (checked at `dbb1640`, read only): the field's
values were read at T7 (`otherCount`, `strangeness`, `contextNovelty`,
`attentionGain`), appraisal (`appraisalGain`) and the fit floor; T3, T4, T5, T6
and T8 named their field parameter `_field`, T1 and T2 did not take one; six
contributed keys were read by nothing. `a1914f3`'s CHANGELOG says T8 "closes
back… from N+1"; its test checks only that the keys land in the field. Every
scar's context anchor records the whole field (`fieldState`), so it was legible
in `[event]`, and read back by nothing.

Plone: a declared gap is honest and useless; design the field as the
specification describes it, and give dil-core a mind with a slot for a model.
Done in dil-core, in four steps, each tested and pushed:

1. **`1e0a22a` — GLOB-MOD carries three axes** — `trust`, `alertness`,
   `exploration`, the specification's own examples (DIL-en-v7 §2) — and every
   layer reads one and votes from what it alone sees (`FIELD_WIRING`). The
   facts are no longer in the field ("how to read, never what is read").
   Found on the way, both by tests: a reading law of 2v annulled operations at
   0 (no valence, no attention span, no evidence, a floor above every
   confidence), so the gain is now ½–1½; and a field reaching
   `SUFFICIENT_RECURRENCE` would fail §13.4's accumulation reading, so T5 reads
   exploration instead, and its rule gets the field. Quick-start conformance
   4/3/0 and a long run 6/1/0, as before. 389 tests.
2. **`aa98da9` — the model is the mind's, not the host's.** AGENTS.md and
   CONTEXT.md called it a host faculty; the host "carries no self and
   contributes no self" (DIL-en-v7 §2). Host, mind, and DIL between them —
   Plone's statement, CONTEXT.md §5a.
3. **`8722def` — the mind** (`src/mind`), seated at T5's rule, on the model of
   this repository's `mind.py`: expects without the answer, looks, thinks on
   what failed as often as alertness allows, asks memory, writes with
   `builtFrom`, commands as T5's test. `standingModel` is the reference law
   exactly. 397 tests.
4. **`4358977` — the model slot takes a language model**, local at an address
   or hosted with `apiKeyEnv`; the request runs in a child Node process the
   mind waits on (the loop is synchronous). The key reaches only the header.
   Not yet run against a real model; a language model's expectation is not yet
   tied to the datum it wrote. 405 tests.

Not yet ported here: the field's axes (this port still has the facts), and
dil-core's mind is its own; this repository's mind stays as it is.

### The field's axes, ported (Plone, same day)

Port of dil-core `1e0a22a`. `dil/loop/field.py` (the axes, the reading law ½–1½,
votes); every layer, appraisal and forward-building read an axis; every layer
votes; the driver adds nothing; T5 hands the field to a rule that takes it
(`field` by name, or an eighth argument — a rule written before keeps its call).
Declarations in `dil/loop/decisions.py` as dil-core's. Two things only the port
needed: rounding half up, as JavaScript's `Math.round` does (Python's `round`
rounds half to even, and `shifted_count(3, 1.5)` would be 4, not 5); and T8's
reading of the evidence as a number — it took only an `int`, so T6's weighed
evidence (1.5) would have read as 0 without a sound.

- 316 tests (24 new, `tests/test_field.py`, ported from dil-core's); one test
  set to T3's new snapshot (`asked` with the cycle each cue was last asked).
- ls20, 80 cycles, learning model, against the same command before the port:
  the same scars by source (onlooker 20, frame 88, region 12), 2 of 79 frames
  held, the same conformance, no level. The field moved — alertness near
  0.15, exploration near 0.13, trust near 0.75 by cycle 10, read from the
  scars' `fieldState` — and changed nothing this run could show: the learning
  model decides what is done, and what the field reaches here (T7's span, how
  many situations are built, the fit floor) changed no scar.
- `scripts/field_trace.py` is pinned to `321d9e0` and left as it is.
- README Findings 2–4 say what holds now; a ninth gap: this repository's mind
  does not take the field.

## 2026-09-28

### The onlooker's word strikes the mind (Plone, 2026-09-27/28)

Plone: the design read like a turn-based game — the remark travelling a long
way and landing a turn late. A word from outside, once the senses have it,
strikes the mind directly; the mind takes it in, thinks, and chooses to act
otherwise then, not by waiting for the word before it acts. And it arrives as a
mismatch, a ResistEvent, not plain data. A word said again and again must raise
the mind's attention, not fall silent. Settled with Plone: H5 (i), a known way
to the aim takes no objection; H7 (ii), an objection is lifted when the onlooker
says something else. Done:

- **The mind commands again before the body moves.** The body carries out the
  last test of the cycle; the remark comes after the status the mind first
  commanded on, and when it collides and the mind thinks, the mind commands
  again (`mind.on_remark`).
- **An answer is an expectation.** Having answered a remark, the mind expects
  the onlooker to stop (`Organs.quiet`), and that expectation is its answer's
  data (`Thinking.answer`; the learning model's objection thoughts, the language
  model's program kept on the remark). Said again, or held while the agent keeps
  doing it, the expectation fails: a ResistEvent, the scar on the remark and on
  the answers. The learning model keeps every answer to a word while it stands,
  so from the second collision on the first answer, whose id is known by then,
  is scarred; the first comes back before its id does, and is not attributed.
- **Attention.** The field reaches the mind (`mind_rule(..., field=)`); it thinks
  on failed expectations as often a cycle as alertness allows
  (`MIND_THOUGHTS_PER_CYCLE`), and the learning model reaches an objection said
  again over the run the onlooker points at, as far as alertness says.
- **The onlooker says a back-and-forth again** each `ALTERNATION` more steps,
  with `at_least`; held, it had let m3-ls20-motion alternate for hundreds of
  cycles on 13 remarks.
- **The learning model**: an objection puts an act behind every other at every
  point of choice (H1: a way whose first act is objected to only when there is
  no other, and it says so; H3: every known act objected to → RESET; H4: the
  imagined path's unlearned acts too); a back-and-forth is objected to at the
  states it ran through (H2); told it stands still with nothing to do, it resets
  (H6); objections are held by what the onlooker said, lifted when it says
  otherwise, keyed by the grid as it came and read under the clock (H7). Toward
  the aim it takes none (H5).

Measured, ls20, 600 cycles, against the m3 stores of 2026-09-27
(`scripts/onlooker_answers.py`; one run each, not attributed):

| | m3-plain | now | m3-motion | now |
|---|---|---|---|---|
| A: body's move in an objection's cycle was the act objected to | 16/40 | 0/32 | 15/19 | 0/57 |
| B: choices at an objected state that took the objected act | 34/85 | 0/6 | 232/264 | 0/0 |
| cycles the mind commanded twice | 0 | 52 | 0 | 57 |
| onlooker collisions | 164 | 99 | 78 | 168 |
| answers scarred | — | 2/52 | — | 0/57 |
| level 1 | 515 actions | 377 actions | no | no |

B is counted once per choice; the 1,456 of 1,514 said on 2026-09-27 counted a
choice once per objection covering it. With motion, the back-and-forth is gone
and the run reaches where the imagination runs out ("nothing it can do here",
26 times): standing still, told so, RESET, the same 20 cycles again — the
motion limit already logged, now reached instead of the loop. Stores in
`scripts/data/onlooker-strike/` (git-ignored). 327 tests.

### Motion removed (Plone, same day)

Every ls20 run with motion, 600 cycles, ended at level 0 (motion-ls20,
m3-ls20-motion, onlooker-strike/motion); every one without it passed level 1
(515 and 377 actions here, and the 600-cycle Kaggle run). vc33 passed with it,
but motion read only acts without a place and vc33 has only ACTION6, so it never
ran there. Why it did not help, as measured: its imagination took the scene as
fixed while touching things changes it (36 places in 4 scenes against 48 in 12
without it); it stopped before any colour it did not know; it put aside the
acts whose motion it could foresee, the very branch that got the run without it
through; and where the imagination ran out it had no way on — a back-and-forth
before the onlooker struck, a loop of standing still and RESET after.

Plone chose to remove it rather than keep an unused branch the paper would have
to explain. `mind/models/motion.py`, the learning model's motion state, rule,
expectation, planning and `_stuck`, `run_game.py --motion`, and five tests are
gone; git keeps them (last at `f111572`). A learning model with motion off
behaved exactly as this one, so no run changes. ls20, 60 cycles, runs as
before. 322 tests.

### Learning notebook version 5: 600 cycles, four games at once (2026-09-28)

`dil-arc3-learning` version 5, code `f76ff5f` (the field's axes, the onlooker's
word striking the mind, no motion), Save & Run on CPU, ar25, ls20, sk48 and vc33
at once, 600 cycles each, as version 4 (`b928f28`). Not a submission. 1,115 s of
`run_competition`; download 18 s (52 MB archive). All four exited 0.

| game | level | actions to level 1 (v4) | states met (v4) | wall (v4) | s/cycle by 100-cycle block |
|---|---|---|---|---|---|
| ar25 | 0 | — | 497 (497) | 690 s (670) | 0.91, 0.99, 1.01, 1.27, 1.21, 1.30 |
| ls20 | **1** | 377 (330) | 145 (127) | 859 s (825) | 0.95, 1.13, 1.27, 1.66, 2.04, 1.44 |
| sk48 | 0 | — | 366 (378) | 1,106 s (1,050) | 1.18, 1.53, 1.64, 2.26, 2.17, 2.21 |
| vc33 | **1** | 83 (81) | 54 (54) | 731 s (701) | 0.94, 1.02, 1.05, 1.25, 1.43, 1.52 |

- **The same levels as version 4, at a slightly higher cost**: ls20 377 actions
  to level 1 where version 4, whose learning model the onlooker did not reach,
  took 330; vc33 83 against 81. Between them, the code that first heard the
  onlooker took 515 on ls20 (m3-ls20-plain, here). One run each; not attributed.
- **ls20 on Kaggle is the local run of 2026-09-28 exactly** — 145 states, 542
  grids, the same scars by source (onlooker 102, frame 750, region 117): the
  learning mind is deterministic across machines.
- **The onlooker** (`scripts/onlooker_answers.py`): the body never carried out an
  act objected to in the cycle the objection came (ls20 0/32, sk48 0/5, vc33
  0/2), nor chose one at a state an objection held for (0/6, 0/3, 0/2); the mind
  commanded twice in 52, 11 and 2 cycles; answers scarred 2/52, 5/11, 0/2. ar25
  drew one remark in 600 cycles — every step reached a new state, so nothing
  was ever repeated for the onlooker to see.
- The script first compared act ids only, and counted vc33's click at (4, 0),
  commanded in place of the objected (61, 33), as the objected act; it now
  compares the act whole.
- For ~110 games four at once, at these four games' mean (847 s) about
  23,300 s (6.5 h) of the 9 h less 20 min.

### Submitted: learning notebook version 5 (Plone, same day)

At Plone's request, `dil-arc3-learning` version 5 (code `f76ff5f`) was submitted
to ARC-AGI-3 at 2026-09-28 00:12:57 UTC, ref `56623380`: the learning mind, 600
cycles a game, four at once, CPU, the deadline 9 h less 20 min from the
notebook's start, each store dropped once its game has played. Its Save & Run
is the entry above. Pending when written; no dataset version is pushed while
its rerun may still read `dil-arc3-src`.

### A mind with no aim at its first step never started without the onlooker (same day)

Found while running ls20 `--alone` to weigh the onlooker's cost: 600 cycles, one
state met, no choice made. At cycle 1 the learning mind holds no aim yet — the
task comes back from memory a moment later — so it commands nothing and the
body stands. What it reads then arrives, and nothing asked it to command: in a
cycle the body stood still in, only the onlooker's word arrives, and with no
onlooker nothing does. Every run with the onlooker stood one cycle at the start
for this reason ("the body stood still: 1 cycles"), and the remark "standing
still" set it going. Now, when what it reads comes back and it holds an aim
while the body waits, the mind commands (`Mind.take_return`); the runs stand
still for no cycle. ls20 with the onlooker plays exactly as before (377 actions
to level 1). A test holds it. 323 tests.

### What the onlooker cost, and a repetition going somewhere kept on (Plone, same day)

Version 5 took 377 actions to ls20's level 1 where version 4, whose learning
model the onlooker did not reach, took 330. Plone: the design follows the
specification; find the cause and what can be improved.

- **The cost is the onlooker's, all of it.** The learning mind is deterministic
  (ls20 on Kaggle and here agree to the grid), so the current code was run on
  ls20 with and without the onlooker: 330 actions to level 1 alone — version
  4's exactly — and 377 heard. (The run alone first stood for 600 cycles: the
  bug above.)
- **Where.** Versions 4 and 5 made the same 179 moves; they part at cycle 180,
  on "repeating ACTION3", where version 4 walked on along a path it knew and
  version 5 turned. Of version 5's 52 cycles commanded twice, the act changed in
  16 — every one on "repeating" over a run whose every step had reached a state
  not stood in before: a repetition going somewhere, which the onlooker, knowing
  no game, remarks on too. In no cycle did the objection change an act while the
  agent circled; there the first command had already left the act objected to.
- **What changed.** Told once that it repeats an act whose every step reached a
  new state, the mind weighs the word against that evidence and keeps on,
  writing why (`kept_on`) and expecting to hear it again if it is wrong; told
  again, `REPEAT_AT` acts later, it objects. A back-and-forth is objected to at
  once: it returns by definition.

| ls20 / vc33, 600 cycles | actions to level 1, ls20 | vc33 |
|---|---|---|
| without the onlooker | 330 | — |
| heard, as version 5 | 377 | 83 |
| heard, a repetition going somewhere kept on | **330** | **81** |

In the kept-on ls20 run the mind kept on 15 times and objected 28 times; the
body carried out no objected act in an objection's cycle (0 of 10), nor chose
one where an objection held (0 of 8); it commanded twice in 57 cycles. vc33
kept on twice and objected to nothing. One run each. Stores in
`scripts/data/onlooker-cost/` (git-ignored). 326 tests.

### A review of the documents and the mind's seams (Plone, same day)

Five points, each checked against the code:

1. "The submitted run" named no submission once there were two of the agent:
   CLAUDE.md and README now name `56588469` for the language model and
   `56623380` for the learning model.
2. Short-term perception was cut at `BASELINE_WINDOW` (16) while T5's window,
   since the field, is 16 shifted by exploration (8 to 24 — about 22 at the
   exploration of 0.13 measured on ls20). The mind now reads its perception as
   T5 does its window, from the same field (it keeps 32).
3. README's ninth gap said the language model does not read the field; the
   field's alertness sets how often the mind thinks for either model. Only the
   language model's prompt does not show it; said so.
4. A cycle the mind commands twice in left two `choice` data and no mark of
   which the body carried out. The mind now tells its model it is commanding
   again (`on="command again"`), and the learning model's second choice says
   which it replaces (`supersedes`); CLAUDE.md says how to read it back — a
   cycle's T5 tests in `[event]`, the last carried out.
5. The fix of the no-aim start commanded on any recall of a prior while the
   last command was none — a language model asking for its task mid-run could
   have spent up to two model calls on "no command". It now acts only on a
   prior's first arrival.

Three tests, each failing on the code before (`git stash` segfaulted on this
checkout; the check was made by restoring the committed files by hand). 329
tests.

### Learning moved from the model to the mind: S1 (Plone, same day)

Plone: learning is developing experience into what serves the agent, not storing
it; and it belongs to the mind, since a model for another task should not have to
define learning again. His approved design moves the loop to the mind and leaves
the model only the computing, as an **inducer**:
- **S1**: the loop moves to the mind, with the exact inducer, and gives the same
  results;
- **S2**: curiosity and look-ahead move to the mind;
- **S2b**: curiosity rates a kind of act by how often it reaches a new state,
  not how often it changes the state;
- **S3**: a grid inducer that generalises;
- **S4 and S5** wait on S3's results.

Plone also settled:
- it is done in dil-arc3 first;
- the fit rule: a hypothesis is held while right more often than wrong, and of
  those that apply, the one right most often is used;
- "learning model" is renamed; what was the learning model is now the exact
  inducer.

**What is where now.**
- `src/mind/learning.py` holds the loop and names no task. It keeps:
  - experiences;
  - hypotheses, written as `kind: hypothesis` (it was `transition`);
  - the expectation, held by the hypothesis it came from;
  - the counts for and against each hypothesis, with a new datum when whether it
    holds changes;
  - curiosity, paths, and the onlooker's word.
- `src/mind/models/exact.py` holds the inducer:
  - perception: a state's identity, its situation, the clock, the things;
  - the acts a state affords;
  - `induce`, `predict`, `describe`.
- `src/mind/models/learning.py` is gone.
- `run_game.py --mind learning` seats `Learning(ExactInducer(...))`.

**The refactor changes nothing.** The old rule dropped a transition at its first
failure. With that rule in place of the fit rule, the new code and the code
before it (`4e56bc0`) were each run on ls20 and vc33 for 600 cycles. Their
reports agree line for line, apart from the run's own key, time and path:
- every cycle's choice;
- the moves;
- the scars by source and datum kind;
- 38,265 and 37,505 `[event]` records.

The first level came at the same cycle, after 330 actions on ls20 (cycle 333)
and 81 on vc33 (cycle 84), counting non-RESET moves in `[event]` before the
first status with `levelsDelta > 0`.

**The fit rule, then.** It differs from the old rule only for a hypothesis that
was borne out before it failed.

| 600 cycles | actions to level 1 | hypotheses marked no longer held | states met | onlooker collisions |
|---|---|---|---|---|
| ls20, old rule | 330 | 2 | 130 | 103 |
| ls20, fit rule | 330 | 0 | 134 | 112 |
| vc33, old rule | 81 | 0 | 54 | — |
| vc33, fit rule | 81 | 0 | 54 | — |

- vc33 is the same in every cycle: no hypothesis there ever failed.
- ls20 is the same up to cycle 421. At cycle 422 the old rule dropped the
  hypothesis from `6beb37e9…` by ACTION1, first written at cycle 345. The fit
  rule kept it, because it had been borne out before, and the two runs part
  there, after level 1.
- Neither run reaches level 2.
- The body carried out no objected act in the cycle of the objection: 0 of 10 on
  the old rule, 0 of 14 on the fit rule.

One run each.

**What S1 does not yet do.**
- The exact inducer suggests one hypothesis per situation and act. So "the one
  right most often" has nothing to choose between until an inducer suggests
  several (S3).
- A failure that does not change whether a hypothesis holds is not written as a
  datum. It shows only as the scar on the hypothesis that held the expectation.
- The counts are held, not written, as before.

The code is under the next commit. Stores are in `scripts/data/s1-baseline/`,
`s1-check/` and `s1-fit/` (git-ignored). There are 330 tests; the new one keeps a
hypothesis right twice and wrong once.

### S2: the mind looks ahead by what its hypotheses predict (same day)

The mind now reaches its hypotheses by the scope the inducer declares for each:
for the exact inducer, the situation it was met in and its act. It expects from
the held hypothesis that applies and was right most often. It weighs every
hypothesis that applied to a step.

It looks ahead by what its held hypotheses predict, not by the experiences it
kept:
- through the situations it has stood in;
- for an inducer whose hypotheses apply beyond where they were met, up to
  `MAX_IMAGINED_STEPS` (3, declared) past them, where a situation it has not
  stood in counts as something left to try.

An act its hypotheses say leads to a situation it has stood in no longer counts
as untried. With the exact inducer, whose hypotheses apply only where they were
met, none of this can differ.

**Measured.** ls20 and vc33, 600 cycles. Each report agrees line for line with
S1's, apart from the run's key, time and path. Wall time was 499 and 336 s,
against 468 and 324 s, but the two runs did not share the machine equally, so
the times do not compare.

The check on ar25 and sk48 is reported with S2b. Both games can now run on this
machine: their files are the competition's public `environment_files`,
downloaded to `Downloads/` and git-ignored here. The S1 runs of both, 600
cycles, reached no level, with 498 and 379 states met.

### S2b: curiosity for somewhere new, not for a change (Plone, same day)

Curiosity now counts, for each kind of act and each act, how often it reached a
situation not met before, instead of how often it changed the state. The odds
are still Laplace's, raised by UCB1, and the choice datum says `odds_of_new`. An
act that only takes the mind back where it stood changes the state every time
and reaches nowhere new. On sk48, ACTION7 (undo) did that: in S1's 600-cycle run
it was taken 133 times, and 105 of those led back to a situation already met.

**S2 on ar25 and sk48, first.** With the exact inducer, the two reports agree
with S1's line for line, as ls20 and vc33 did.

**Measured.** All four games, 600 cycles each, the exact inducer, one run each.
Actions to level 1 count the non-RESET moves in `[event]` before the first
`levelsDelta > 0`.

| | S1: level (actions to level 1) | S2b | steps reaching somewhere new | ACTION7 steps back to a situation met |
|---|---|---|---|---|
| ls20 | 1 (330) | **0** | 133 → 124 | — |
| vc33 | 1 (81) | 1 (**72**) | 53 → 53 | — |
| ar25 | 0 | **1 (578)** | 497 → 535 | 20 → 7 |
| sk48 | 0 | 0 | 378 → 452 | **105 → 12** |

- **sk48's undo loop is gone.** ACTION7 was taken 16 times instead of 133.
- **ar25 passed a level for the first time, at cycle 586.**
- **ls20 lost the level S1 reached.** It met 125 situations against 134, and
  took ACTION1 165 times against 219. This was not traced further: one run, and
  the order of exploring changed from the first choices on.
- Levels over the four games stay at 2, now vc33 and ar25.
- Wall times (614, 464, 481, 949 s) ran six games at once, so they do not
  compare with S1's.

Stores are in `scripts/data/s2/` and `s2b/` (git-ignored). 331 tests.

### S3: the grid inducer, whose hypotheses reach past where they were met (same day)

**What was built.**
- `src/mind/models/grid.py` sees what the exact inducer sees. Beside the exact
  hypothesis, it suggests one that reaches further:
  - "this act changes nothing": for an act that takes a place, on that colour;
  - "this act rewrites, in each part of the grid it changes, the cells L into
    R".

  Each part of a rewrite is found on its own:
  - at the place the act is put, when that lies in or next to the part;
  - else at the one place its box lies;
  - or, where the box lies at several, by the ring of cells around it, the
    grid's edge among them.

  An act that takes a place must be put on the colour it was put on then.

- The mind now asks its inducer for hypotheses on two occasions: a new situation
  and act, and a step that no held hypothesis foresaw. It holds once what the
  inducer keys alike.
- The mind counts `unseen`: steps from a situation and act never met, how many
  it expected, and how many of those were right.
- `--inducer exact|grid` goes through `run_game.py`, `run_competition.py` and
  the Kaggle builder. The default stays `exact`.
- `scripts/replay_inducer.py` replays a run's steps through the mind's learning
  with each inducer. The acts are the run's, so only the expectations differ.

**Replayed on S1's steps**, of the steps from a situation and act never met
(exact: 0 by construction):

| | never met | grid expected | right |
|---|---|---|---|
| ls20 | 426 | 281 | 259 (92%) |
| vc33 | 529 | 396 | 345 (87%) |
| ar25 | 596 | 531 | 490 (92%) |
| sk48 | 596 | 459 | 333 (73%) |

**How it got there.**
- The first rewrite placed its parts at fixed distances from each other. It was
  right on 60 of 193 such steps in ar25 and 176 of 271 in sk48.
- Each counter is a part of the state, not a clock:
  - ar25 keeps one in column 63. It ticks on ACTION1-5 and never on ACTION6 or
    7, so it counts moves, and the row-only clock rule cannot find it.
  - sk48 keeps one in row 53, which ticks on some moves.
- Every wrong prediction was off by those one or two cells, so each part is now
  found on its own.
- The first replay of vc33 had never found the clock. The replay did not name
  the kinds of act as `propose` does, so every click was one kind. Fixed in the
  script.
- vc33 took 333 s to replay. Three changes brought it to 46 s, with the same
  answers:
  - the parts at the place are looked at first;
  - the colour under the place must match;
  - each box is checked rarest colour first, and where each part lies is
    remembered per situation.

**Live, 600 cycles, one run each.** Levels, with actions to level 1 in brackets.

| | ls20 | vc33 | ar25 | sk48 | levels |
|---|---|---|---|---|---|
| exact (as S2b) | 0 | 1 (72) | 1 (578) | 0 | 2 |
| grid, foreseen acts out of reach | **1 (128)** | 0 — stuck, 4 situations | 0 | 0 | 1 |
| grid, foreseen acts last at here | 0 | 1 (71) | 0 | 0 | 1 |
| grid, foreseen acts last (as now) | 0 | **2** (71; level 2 at cycle 306) | 0 | 0 | 2 |

- **The first live round excluded foreseen acts, as S2 wrote.** An untried act
  whose hypothesis said it leads where the mind has stood was taken out of
  reach.
  - On vc33 that stranded it: "a click on this colour changes nothing" was
    right more often than wrong. No click on that colour was tried again, so the
    hypothesis could never be refuted by one. The mind took the known act toward
    the least visited situation 581 times.
  - On sk48 the moves were foreseen to lead back, and undo, foreseen by nothing,
    was taken 259 times.
  - So a foreseen act is now tried last, never out of reach. This replaces
    S2's line.
- **The second round put foreseen acts last only at the situation it stands in.**
  On ls20 it then walked to far situations to try acts it could foresee. So the
  order is now:
  1. what it cannot foresee, here;
  2. the way to such an act, or to a situation not stood in;
  3. what it can foresee, here;
  4. the way to that, elsewhere;
  5. RESET.
- **What reached a level changed with each round.**
  - ls20 was reached once, in 128 actions (S1: 330).
  - vc33 reached level 2 for the first time, in the last round.
  - ar25, reached with the exact inducer, was never reached with the grid one.

  Over four games, one run each, no inducer and no order is shown better at
  levels.
- **The generalisation is not in doubt.** In the last round the grid inducer
  expected, and was right on, these steps from a situation and act never met:

  | | right | expected | never met |
  |---|---|---|---|
  | ls20 | 109 | 123 | 219 |
  | vc33 | 229 | 283 | 510 |
  | ar25 | 495 | 530 | 595 |
  | sk48 | 175 | 301 | 598 |

  The exact inducer expected none of them.
- **Exact, on the S3 code** (asked on surprise, foreseen acts last), was the S2b
  run in every cycle on all four games: it foresees nothing it has not met.
- **Cost.** Eight runs shared the machine. Grid took 1131, 1088, 761 and 1400 s;
  exact took 884, 707, 739 and 1190 s: 3% to 54% more. On Kaggle, 110 games at
  600 cycles were estimated at about 6.5 h with exact against a 9 h limit. The
  grid inducer would need fewer cycles or more games at once.

Stores are in `scripts/data/s3-exact/`, `s3-grid/`, `s3-grid2/`, `s3-exact3/`
and `s3-grid3/` (git-ignored). The games ran offline from `environment_files`.
339 tests.

### Two points the S1–S3 entries left out, and one not yet checked (Plone, same day)

**Where the runs got their games.**
- The S1 runs of ls20 and vc33 (`s1-baseline`, `s1-check`, `s1-fit`) were made
  without `--offline-dir`. The toolkit took an anonymous API key and fetched the
  list of environments from the API. It still loaded each game's code from the
  local `environment_files` (ls20 `9607627b`, vc33 `5430563c`).
- Every run from S2 on, and S1's ar25 and sk48, ran offline from those same
  files.
- S2's check agreed with S1's runs line for line across the two modes. On these
  games, the two modes play the same game.

**The replay before the mind held each hypothesis once.**
- Before the mind asked on surprise and held each hypothesis once, the grid
  inducer replayed on S1's steps (the kinds of act already named):
  - ls20: expected 312 of 426 steps from a situation and act never met, right on
    285;
  - vc33: expected 408 of 529, right on 335.
- After that change, and before each part was found on its own:
  - ls20: expected 282, right on 257;
  - vc33: expected 402, right on 335.

  So it expected fewer steps, and was right about as often. Why it expected
  fewer was not traced.
- The figures in the S3 entry are those after the parts were found on its own.

**Not yet checked: more games to measure on.**
- Run without `--offline-dir`, the toolkit logs "Successfully fetched 25
  environment(s) from API".
- Unchecked:
  - whether each of those 25 can be downloaded and played here, as ls20 and
    vc33 are;
  - which games they are.
- If they can, the inducers could be measured on 25 games, not 4. To be updated
  here once checked.

### How the language model came to sit level with the mind's learning (Plone, same day)

Asked whether the inducer belongs to the model alone, a check of the code found
that the mind's seat for a model holds its learning, not its inducer:
`Mind(Learning(ExactInducer(...)))` (`scripts/run_game.py`), and
`Mind(LanguageModel(...))` in the same seat. So the language model and the
learning are alternatives, and seating the language model leaves the mind no
learning of its own. What it keeps of a revision is the model's rule
(`language.py`), so learning is defined twice — once in the mind, once in the
model — which is what S1 was to prevent ("a model for another task should not
have to define learning again"). S1 prevents it between inducers only.

Plone: the model is the replaceable computing; the mind's learning must not
depend on it. Read back through this log, the misreading built up in four
steps, each correction carried out by moving code between files while the
wiring `Mind(<what is replaceable>)` stayed:

1. **2026-09-24: the mind was the model.** "One mind, and it is the model";
   Direction C: "The model sits at the **mind**: it is the thinking … adjusting
   is what thinking does with that." Adjusting after a mismatch — learning —
   was the model's from the start.
2. **2026-09-27: the mind learning from nothing was built as another mind.**
   "One mind" was read as "(which mind sits there can change)", and
   `arc3/learning_mind.py` took the seat instead of the language model's
   (`--mind learning`). The seat was a mind's, and learning a trait of one kind
   of mind.
3. **Same day: "the model is the mind's computing" was read as "the mind is its
   seams".** `mind.py` kept when to think, write, ask and command; everything
   that computes went to a model, the learning algorithm whole ("the same
   algorithm, through the model interface"), and the language model's rule for
   what it keeps "in the model, for now".
4. **2026-09-28, S1: the file moved, the wiring did not.** `learning.py` moved
   from `models/` to `src/mind/` and "learning model" became "exact inducer",
   but `Learning(ExactInducer(...))` still sits in the model's seat. The entry
   does not name the language model, and its list of what S1 does not yet do
   leaves it out; "for now" was not taken up again. S1's check — reports equal
   line for line — can find a change in behaviour, not a thing in the wrong
   seat, since putting it in the right seat changes no behaviour.

Plone put most of it down to how his ideas were first phrased, the code then
corrected step by step. And he corrected one reading made in this check:
"Chỉ cần model tư duy theo đúng chỉ thị thì curiosity, expectation và want sẽ là
hệ quả" (2026-09-25) means these come about in the mind, not in the language
model alone: replace the model and they must still be there. So the language
model is work left unfinished inside the model, set aside for now, not a
settled branch; its rules are not a second mind's, they are not yet revised,
and only the learning mind's are in force.

Documents set to that, no code changed:

- CLAUDE.md: "One mind" says the model changes, never the mind or its learning;
  curiosity, want and expectation are the mind's whatever its model; the rules
  in force speak of hypotheses, not the program (the invariants, what is
  expected, what is scarred, tag H); the language model's rules move, word for
  word, into "The language model — unfinished, not yet revised", which says why
  they are not in force; the open items gain the seat, and `COMMIT_CADENCE`
  says it is the language model's.
- README: the status, the roles, "What the mind is", the layout (the grid
  inducer, missing from it) and how to run the learning mind.

### The mind holds its learning; its model's seat takes the inducer (Plone, same day)

Step 1 of what the entry above found, approved by Plone with option (b): the
language model's seat and the tests through it are kept and not run.

- `Mind(inducer, organs, priors)` (`src/mind/mind.py`) makes its own `Learning`
  and holds it (`mind.learning`); nothing seated can replace it. The seat's
  interface is declared, `Inducer` (`src/mind/models/base.py`: the fourteen
  parts the learning asks of an inducer, which it had taken as `Any`), and what
  the seams ask of the learning is `Learner` (it was `Model`). The learning's
  logic is unchanged.
- The language model is not an inducer, so it is not seated: `create_mind`
  (`src/arc3/mind.py`) raises `NotImplementedError` before its body, which is
  kept as it was; `--mind language` stops before a run starts in `run_game.py`,
  `run_competition.py` and `build_dil_run.py`, whose default is now the mind
  with its learning.
- Tests: the 35 that went through the language model's seat were marked
  skipped, not removed — 30 in `test_arc3_mind.py`, 3 in
  `test_arc3_directive.py`, 1 in `test_api_key.py`, and
  `test_the_host_hears_the_onlooker_and_keeps_cycling_while_the_body_stands_still`.
  That last one checks the host and the onlooker, and no other test does: a
  cycle the body stood still in carries only what is heard, the region is not
  counted absent then, the waits cost no action and count against the budget,
  and each nudge collides. The body's acts in it are scripted; the language
  model only filled T5, and was never asked. Plone approved porting it: it now
  seats the mind with the exact inducer, every assertion as it was. Its
  onlooker scars fall at cycles 2, 3 and 4 on the remarks (`signal-2-0`,
  `signal-3-0`, `signal-4-0`), at 2 on the remark before (the standing
  expectation's datum) and at 4 on the mind's answer (`written-2-0`), which
  the language model, not asked, never gave. Two tests added: the mind holds
  its learning and the seat takes the inducer; the language model's seat
  raises. 307 pass, 34 skipped.

**Measured: nothing changes.** ar25, ls20, sk48 and vc33, 600 cycles, each
inducer, offline from `environment_files`, eight at once as S3 ran, against the
S3 runs `s3-exact3` and `s3-grid3`. All eight reports agree line for line (635
lines each) apart from the scorecard, two timestamps, the store's path and the
wall time: every choice, the scars by source and datum kind, the `[event]`
records (38,670 exact ls20 to 42,763 grid sk48) and the levels — exact vc33 1
and ar25 1; grid vc33 2.

Wall time was 25–55% longer in every run (exact ls20 1,227 s against 884 s;
grid sk48 1,704 s against 1,400 s). The change adds no work to a cycle — the
seams call `self.learning` where they called `self.model` — and this machine
also ran the tests during the runs; not traced. Stores are in
`scripts/data/step1-exact/` and `step1-grid/` (git-ignored).

### Step 2a: a language model the mind learns with; 2b, its mechanism on a probe's program (Plone, same day)

Step 2 of the entry before last: the language model as an inducer. Plone's
choices: the model thinks and computes, and does not decide — it chooses no act,
holds no aim, does not judge its own program (Q1); all that reads the grid is
the model's, not code beside it (option (a)). Asked when to call it (Q2) and what
to show it (Q3), he let the proposals stand. Whether FIT_LAW's "the one right
most often" is a count or a rate (Q4) is left as it is, a count, and open.

- **The learning tells the inducer more, and keeps what it says.** `induce`
  takes `foreseen` — whether a hypothesis held foresaw the step — and
  `evidence`, the mind's short-term perception as (step, report) pairs, this
  step last; the mind passes its perception to the learning with each step
  (`observe(..., seen=)`). An inducer's `said()` is written whole, each a datum
  built from the step it was asked on. The exact and grid inducers take both and
  ignore them, and say nothing.
- **`src/mind/models/language_inducer.py`** (`--inducer language`, at
  `--endpoint`). Asked only on a step not foreseen, shown the perception, the
  step, and the program it wrote last, the model writes one program:
  `predict(grid, action, x, y)`, and if it can `where(grid)` (the grid as it
  bears on where the region stands, cells that change whatever is done set to
  -1) and `targets(grid)` (the cells worth putting an act that takes a cell on).
  The program is a hypothesis applying everywhere (`general`), its code in the
  datum. Its reading of the grid is the latest program's that defines `where`
  or `targets`, and a change of it is a datum (`kind: perception`) on which the
  learning reads every situation again. Before any, a situation is the grid as
  it came and no cell is a target. Code keeps only records beside it: a state's
  hash, the exact hypothesis. A program is a hypothesis only if it gives, from
  the step it was asked on, where the region came to — what an experience
  suggests must bear it out; otherwise the answer says why. Declared: it
  predicts no report of the region, and asks memory nothing.
- Tests, with a scripted model on the learning mind's 3x3 game (7): asked once,
  every later step foreseen by its program; shown the perception; a program
  that does not bear out its step is no hypothesis, and asked again; its `where`
  reads the clock cell out, and the change is a datum; its `targets` are where
  ACTION6 may go; a model that does not answer leaves the exact records and the
  commands. One expectation of the first test was wrong and corrected: the mind's
  whole-grid `holds` stays 0 where the program does not predict the clock; the
  learning's off-the-clock count is 1. 314 pass, 34 skipped.
- Smoke, ls20, 5 cycles, the endpoint closed: 4 answers kept, each "the model
  did not answer"; 4 exact hypotheses; the mind commanded every cycle.

**Exact and grid unchanged.** The eight S3 runs again (600 cycles, offline):
every report agrees line for line with `s3-exact3` and `s3-grid3`, but for
key, time and path. Wall time was shorter than S3's this time (exact ls20 731 s
against 884 s; grid sk48 1,255 s against 1,400 s), so step 1's longer times
were the machine's.

**2b — the mechanism, on a program written outside the loop.** With no served
model here, `replay_inducer.py --inducer language --program` has a scripted
model answer every question with the 95% ls20 program of 2026-09-24
(`output-run2/probe_nothink_1.json`, under an adapter for its two-argument
`predict`) — a fixture for the mechanism, not evidence about a model. S1's ls20
steps (`s1-fit`, 600), with the learning choosing at each step and timed:

| | expected (right) | never met: expected (right) | hypotheses (held) | choosing |
|---|---|---|---|---|
| exact | 174 (172) | 426: 0 (0) | 428 (427) | 1 s |
| grid | 455 (426) | 426: 281 (259) | 614 (592) | 9 s |
| language (fixture) | 566 (288) | 550: 516 (271) | 551 (550) | 2 s |

- **The program was held while right more often than wrong, and dropped when it
  no longer was**: 278 for, 320 against. Before level 2 (cycle < 333) it gave
  where the region came to on 278 of 329 steps (misses: 42 elsewhere, 9 in the
  bar on rows 61-62); from level 2 on, on none of 264 — 254 of them in the bar
  alone. It was written for level 1, and the fixture cannot write another.
- **The model was asked 279 times in 600 steps**: on every step no held
  hypothesis foresaw. At 3.9-76.3 s an answer (the one mind's first run on
  Kaggle, Qwen3.6-35B-A3B, 2026-09-24), that is 18 minutes to 6 hours a game,
  before a real model's answers change how often it is asked. That is what 2c has to measure.
- **Looking ahead with a program is cheap here**: 2 s of choosing in 600 steps.
- 550 steps met no situation met before, against 426: the program has no
  `where`, so the bar makes every grid a situation of its own.
- Q4 is not tested here: one program only.

Stores and reports in `scripts/data/step2a-exact/`, `step2a-grid/`, `step2b/`
(git-ignored).

### No language model for ARC-AGI-3 for now; the code and the documents made to agree (Plone, same day)

Plone stopped step 2 before the Kaggle run (2c): ARC-AGI-3 is not played with a
language model for now. The language inducer stays as it is — built, tested,
never run against a served model — and the work goes back to the mind with its
other inducers. What was asked was only that the code agree with itself and
with its documents. No logic changed: every edit is a docstring, a message, a
help text or a test's expectation of a message.

- What still said the language model was "unfinished" and "not yet revised" —
  `src/arc3/mind.py` (its docstring and `UNSEATED`, the skip reason of the 34
  tests), `src/mind/models/base.py`, `src/arc3/__init__.py`, `src/mind/mind.py`,
  `run_game.py`, `run_competition.py`, `build_dil_run.py`, three test comments,
  `scripts/README.md` — now says what holds: its earlier form, which submission
  `56588469` ran, sat in the learning's place and is kept, not run; its revision
  is the language inducer. The test of the kept seat expects that message.
- `mind.py`: the seams for a want and for an aim with a time served only that
  earlier form; no model seated now states either, so they are unused.
- CLAUDE.md: the language inducer is not used for ARC-AGI-3 for now; "the
  language model, once revised" is gone from what a model can be; the notebook
  section says which lines are the GPU notebook's (one model server, the wait
  for it) and why a game plays in a process of its own.
- README: finding 7 is the earlier form's, and says how every inducer is kept
  now; finding 9 says neither form of the language model is shown the field;
  the language inducer is not used for ARC-AGI-3 for now.
- `learning.py` names the three inducers.

314 pass, 34 skipped.

### S5 held to its criterion; FIT_LAW by rate (Plone, same day)

Plone set out what S4 and S5 were in the design approved for S1:

- **S4 — a hypothesis about the aim, carried to the next level.** Reaching the
  aim is an experience too; the mind draws from it what brings the aim, and uses
  it at the next level — in the same loop, not a mechanism of its own. Passes
  if ls20 and vc33 get through level 2.
- **S5 — the language model through the inducer interface.** The hypothesis is
  a `predict` program, `induce` has the model write one, and the rule "kept if it
  explains better" moves from `language.py` to the mind, as the general fit law.
  Passes if the prompts that ran are kept word for word; if one must change,
  Plone is told first.

**S5 was not held to its criterion, and this repository's own rule was broken.**
The language inducer of step 2a was built with a prompt of its own, in code:
only `render_evidence`'s lines were the earlier form's. Plone was not told
first. And words written into code are the side door Plone closed on
2026-09-25 ("Bản chất prompt cũng có khác gì datum có tag 'prior' đâu"): in no
store, in no `built_from`. Plone asked for it to be fixed:

- The inducer's words are `prior:mind-task`'s, under three new keys — `induce`,
  `induce_feedback`, `unforeseen` (`src/arc3/task.py`). `TASK` and `FEEDBACK`
  are unchanged byte for byte. What changed from them is said beside them: "two
  Python functions" becomes "Python functions"; the `propose` block becomes the
  `where` and `targets` blocks; the paragraph on `propose` looking ahead toward
  the GOAL becomes one sentence on the time each run has; the ASK sentence is
  gone; in the feedback, "predict, propose and GOAL" becomes "predict, where and
  targets"; `unforeseen` ("No program you wrote foresaw the last step.") is new.
  A test holds the two texts to that.
- The inducer is shown them as the earlier form was: one message with the task,
  the evidence and why it is asked; then, when it wrote a program before, that
  program as its own turn and the feedback, scored on the grid alone
  (`misses_text`, moved out of `LanguageModel` unchanged, so the earlier form's
  words are the same). It gets the words from the learning, which hands on
  each prior the mind recalls (`Inducer.receive_prior`), and is asked nothing
  before they come. Each answer is built from the step and `prior:mind-task`.
- Smoke, ls20, 5 cycles, endpoint closed: 3 answers, not 4 (the first step came
  before the prior); `written-2-0` is built from `signal-2-0` and
  `prior:mind-task`.

**Q4: FIT_LAW by rate** (Plone). Of the hypotheses that apply and are held, the
one right at the highest rate, (right + 1) / (tried + 2), is expected from; at
an equal rate, the one right more often, then the first met. By a count, a
hypothesis held longer outranked a truer one met later. It changes which
hypothesis is expected from wherever two apply — for the grid inducer the exact
and the general ones, for the exact inducer two exact ones at one situation and
act — so runs can change. **Not yet measured**: Plone asked for the work on S4
to be reported before the next measurement.

319 pass, 34 skipped.

### Learning notebook version 5 scored: 0.05 (2026-09-28)

Submission `56623380` (`dil-arc3-learning` version 5, code `f76ff5f`, submitted
00:12:57 UTC) is COMPLETE, public score **0.05**. It was first seen at 09:15 UTC
and was PENDING ten minutes before.

- It is above v12's 0.00 (`56588469`, the language model).
- It does not show the learning mind beats the random agent: the random agent
  scored 0.02 (`56462757`) and 0.06 (`56600038`), with no seed fixed.
- Kaggle shows no log of the scored rerun. Which games it completed levels in,
  and how many games it reached before the deadline, is not known.
- The rerun is over, so a new `dil-arc3-src` dataset version may be pushed.
- The code scored is `f76ff5f`. It is not the code of S1–S3 (`283fdf6` on),
  which has not been submitted.

### Four laws of curiosity, to be measured against each other (Plone, same day)

Why ls20 lost the level S1 reached, read from the S2 and S2b runs of ls20
(`scripts/data/s2/`, `s2b/`): the two agree to cycle 10 and part at cycle 11,
and the only change between them is what curiosity counts. S2 counted a change;
S2b counts somewhere new. The inducer was the same exact one.

| act | S2: changed / tried | S2b: somewhere new / tried |
|---|---|---|
| ACTION1 | 183 / 219 (84%) | 31 / 164 (19%) |
| ACTION4 | 105 / 132 (80%) | 49 / 163 (30%) |
| ACTION3 | 97 / 125 (78%) | 15 / 134 (11%) |
| ACTION2 | 90 / 117 (77%) | 33 / 133 (25%) |

In a maze a change is mostly "not blocked": nearly even across acts, ACTION1
slightly ahead, and ACTION1 — the act that gained the level — taken 219 times.
Somewhere new is rare and uneven, and depends on where the walk has been: S2b
wanted ACTION4 and ACTION2, and ACTION1 less. ls20 ends a life about every 133
actions (resets at cycles 132, 265-267, 398-400...), so the exit must be reached
deep within one: S2 got there in its third life (cycle 333), S2b spread out
(125 situations against 134) and did not. vc33's level 2 is the grid inducer's
(exact reaches level 1 only). One run each; one map.

Plone asked why neither "somewhere new, and a change" nor "a change, and a new
one": taken as both conditions, each is somewhere new (reaching somewhere new is
a change). But a step ends one of three ways — blocked, back where it stood,
somewhere new — and S2 counts the last two alike, S2b the first two. Settled
with Plone: the laws are named and kept side by side, and the one that does
best across the games chosen after.

- **S2** `changed`, **S2b** `new` (the default), **S2c** `new-then-changed`
  (somewhere new; between kinds as likely to, a change), **S2d**
  `new-plus-changed` (the two odds added) — `learning.CURIOSITY`,
  `--curiosity` in `run_game.py`, `run_competition.py` and `build_dil_run.py`.
  The learning counts changes beside what it counted; the choice datum gives
  `odds_of_change` where a law counts one.
- The grid inducer with S2's law had never been run: it is one of the cells of
  the measurement.
- Tests: each law wants what it counts (a kind that mostly goes back against one
  mostly blocked); the default gives the numbers S2b gave. A 20-cycle ls20 run of
  each, grid inducer, ran through. 321 pass, 34 skipped.

To be measured on the 25 games in the competition's `environment_files` — all
of them are there (listed with `kaggle competitions files`: ar25, bp35, cd82,
cn04, dc22, ft09, g50t, ka59, lf52, lp85, ls20, m0r0, r11l, re86, s5i5, sb26,
sc25, sk48, sp80, su15, tn36, tr87, tu93, vc33, wa30) — on Kaggle, once
submission `56623380` is done (it was PENDING at the time of writing): every law
on the same code, Q4 in it, S2b run again.

### S4: a hypothesis about the aim, carried to the next level — built, not yet measured (Plone, same day)

Plone chose (B): what brings the aim is read from what the grid showed before
the step that reached it, where the act worked. Reported before measuring, as
asked.

**Why (B), from the stores.** The step that reaches the aim changes the grid
nearly whole — a level over: vc33 2,768 and 2,872 of 4,096 cells, ls20 1,479,
ar25 715 (`s3-grid3`, `s3-exact3`, `s1-fit`). The grid inducer suggests nothing
general from a change that large (`BIG_CHANGE`, 1,024), and its general
hypotheses carried no report, so nothing about the aim reached past where it
was met: the mind went toward the aim only at situations it had reached it from.
What did carry to a new level was curiosity's count of how often a kind of act
brought the aim — a count held, not a hypothesis.

**What was built.**
- The learning (every inducer): a prediction may have no state and say only
  what the region will report — a hypothesis about the aim. When the report
  says the aim came, the inducer is asked again with that report and with what
  the mind expected of the step (`induce(..., report=, expected=)`); what it
  suggests is held and written as any hypothesis, built from the frame and the
  report. Each hypothesis about the aim that applied to a step is weighed by
  that step's report. It is kept out of the step's expectation (so not scarred:
  the status's scar would fall on the state's hypothesis too), declared.
- Choosing: an act that reached the aim here; else an act a held hypothesis
  says brings the aim here; else the way to where the aim was reached; else the
  way to where a held hypothesis says an act brings it; then what it has not
  tried, as before.
- The grid inducer's `aim` form: this act, where these cells lie, brings the
  aim. For an act with no place, the cells are those the mind expected it to
  change (the prediction of the hypothesis it held for the step); for an act
  that takes a place, the thing it was put on; with the ring around each, as
  it was. It applies where every part lies, box and ring both — around it is
  part of what brought the aim. With nothing expected to change and no place,
  nothing is suggested. The exact and language inducers suggest none.
- Tests (4): the form from the expected change, applying where the cells and
  the exit beside them lie and not where the exit is elsewhere; the form from a
  click, the thing's colour; in the loop, at a layout never stood in, the mind
  takes the act its hypothesis says brings the aim; a hypothesis that applied
  and did not bring it is counted against, and no longer held. Each fails with
  its part of S4 taken out. 325 pass, 34 skipped.
- Smoke, vc33, grid, 100 cycles: ran through; one `aim` hypothesis written
  (a click on colour 9, one part). Not a measurement.

The criterion — ls20 and vc33 through level 2 — is to be measured with the
rest on the 25 games. ls20 does not reach level 1 on this code now (since
S2b), so ls20 can show nothing for S4 until it does.

### Learning notebook version 5 scored: 0.05, recorded again (same day)

The same result as the entry of this name above, recorded a second time on the
same day; kept as written (noted 2026-09-29).

Submission `56623380` (`dil-arc3-learning` version 5, code `f76ff5f`: the
learning model, before the learning moved to the mind; 600 cycles a game, four
at once, CPU) is COMPLETE with a public score of **0.05**, read with `kaggle
competitions submissions` after Plone said it had finished.

- Beside the others on the same scale: the language model's `56588469` 0.00;
  the starter kit's random agent 0.02 (`56462757`) and, on this repository's
  road, 0.06 (`56600038`).
- It does not show the agent beats the random one: two draws of the random
  agent gave 0.02 and 0.06, and 0.05 lies between them.
- What the rerun did cannot be read: Kaggle shows no log of it. How many of the
  games it played before the deadline (the offline estimate was 6.5 h of the
  9 h less 20 min) and how many levels it completed are not known.
- Offline, this code completed level 1 of ls20 in 377 actions and of vc33 in
  83, and no level of ar25 or sk48. The score squares the ratio of a human's
  actions to the agent's, so a level got through in many more actions than a
  human takes counts for little.

The code now differs from `f76ff5f` (the mind holds its learning, the grid
inducer, Q4, S4 and the laws of curiosity): a later submission is another
submission, and the paper names the one it describes.

### How the score is computed, and the human baselines (same day)

Plone asked what the human baseline is in each game.

- **The formula, read in the toolkit** (`arc_agi/scorecard.py`): a completed
  level scores `(baseline_actions / actions_taken)² × 100`, capped at 115; a
  level not completed scores 0 and still counts in the game's weights; a game's
  score is its levels' scores weighted by level number; the scorecard's score
  is the games' mean. Checked on version 5's offline scorecard: vc33's level 1,
  a baseline of 7 against 85 actions, scores 0.678 (0.6782 in the card), and
  the game 0.678 / 28 = 0.0242 (seven levels, weights 1 to 7). So the scale is
  0-100: version 5's four offline games came to 0.00906, version 4's to
  0.01027 (`scripts/read_scorecard.py`, added). Whether Kaggle's public 0.05 is
  on the same scale was not checked.
- **The baselines** are in each game's `metadata.json`, `baseline_actions`, one
  per level. The 25 games' files were downloaded from the competition
  (`kaggle competitions download -f environment_files/<game>/<version>/metadata.json`)
  to `Downloads/arc-metadata/`: 6 to 10 levels a game, 171 (cd82) to 1,843
  (wa30) actions a game; 6 to 578 a level, median 60; level 1, 7 to 78, median
  30. ls20: 22, 123, 73, 84, 96, 192, 186. vc33: 7, 18, 44, 61, 131, 34, 152.
- So version 5's level 1 took about 17 times ls20's baseline (379 against 22)
  and 12 times vc33's (85 against 7): 0.34 and 0.68 points of 100.

### Goal and aim, settled; the language model's earlier form to go (Plone, same day)

Plone: every living thing has an aim without being told one. An instruction
given from outside is a **goal**; the **aim** is the creature's own — it takes
the goal's value when there is one, and when there is none, the creature still
has an aim to act by. Settled, with one precision put to him and taken: the aim
a mind holds without a goal is not an arbitrary one but one of its make-up, and
it must be one what comes back could show (the regress rule of 2026-09-25) —
proposed and agreed: **the region reports something it has not reported
before**, of the same kind as the task's goal (`levelsDelta: 1` is a field of
the report).

Found on the way: the aim is not in the mind's code but in `prior:mind-task`'s
data (`TASK_AIM`), recalled by the mind and held twice — as the seams' `_goal`
and the learning's `_aim`. The learning mind has no aim of its own: with no task
aim it commands nothing. `prior:mind-aim`'s words, which say to work one out,
reach only the language model's earlier form.

Plone also: the language model has no aim — it is a model; the aim is the
mind's, and the mind tells the model what to compute. Its `GOAL` goes. Put to
him and agreed in substance: the whole earlier form goes with it (its seat,
`LanguageModel`, the 34 skipped tests, `prior:mind-aim`, the seams only it used
— want, `within`), since stripping its `GOAL` alone would leave neither the
submitted code nor the new one; `3b31806` keeps that code for the paper.

To do after the 25-game measurement, so that its runs share one dataset:
- the task's aim becomes the goal (data, a prior); the mind holds one aim, in
  its code, taking the goal's value, or else its own: the region reports
  something new;
- the earlier form removed, and with it the second copy of the aim.

Open with Plone: whether the language inducer's words keep "The aim is to find
how to get through its levels." (S5 kept it word for word; it tells the model
what the region is for, not an aim to pursue) or drop it.

### The constrained setting as a test of the design — a note for the paper (Plone, same day)

Plone: the competition's setting — little knowledge, a budget of actions, no
network — is why a specialised model had to be written; with a large language
model behind an API key the work would be far simpler, and errors of code or
design far harder to find; once the design is mended and runs smoothly, the
agent with an API key in an open region is far stronger. Agreed, with what the
record adds and two precisions, for the paper's limits and future work:

- **A weak, transparent model shows the design's faults; a strong one covers
  them.** Today's alone: the learning seated in the model's place (hidden for
  days by the language model, which wrote, kept and proposed on its own), the
  prompt a side door, the aim held twice, ls20's level lost to a law of
  curiosity. And the learning mind is deterministic — ls20 on Kaggle and here
  agree grid for grid — so every difference traces to one change; two language
  runs on the same prompt did not agree (2026-09-25).
- **Simpler in result, not in audit.** `[event]` records what a model was shown
  and what it answered; why it wrote what it wrote no one can check. By design
  the model is replaceable computing, judged by the region; the paper says the
  loop reads back whole, and the inside of a model as far as that model allows.
- **Stronger is likely and not measured.** Thinking is free under RHAE and the
  place for a key is built (`ModelEndpoint.api_key_env`), but the mind's
  learning still chooses the act: strength depends on the model's prediction and
  on the mind's exploring alike.
- **So, when a large model is fitted,** the exact and grid inducers stay as the
  reference every change to the mind runs on first (as S1 took the exact one to
  be), so that a strong model cannot hide a new fault.

### The measurement narrowed, and how a change is measured (Plone, same day)

Plone: 25 games are many and slow if most of them score nothing in every
configuration. Settled: runs 1 and 2 (exact and grid with S2b) play the 25 —
which games score at all, the reference, and each game's time on Kaggle's
machine; runs 3 to 5 (grid with S2, S2c, S2d) play 6: ls20, vc33 and ar25 —
levels reached before, where the laws of curiosity made the difference — and
three more from what runs 1 and 2 show, or else by kind of control
(`metadata.json`'s tags), sk48 first. Put to Plone and taken: selecting on runs
1 and 2 alone would drop ls20, the very game the S2 run is asked about.

Then how a change is measured, now in CLAUDE.md: six games are the development
set; what counts is not a level more but playing clearly well — the six
completed, each in few actions against its baseline (Plone: that cannot be got
by a trick fitted to six, and shows the mind and model reasoning better);
every change is a general law; when the six are met, the 25 are run once to
confirm. Put to Plone first and not taken: a held-out check on the other 19
before every change — it would stop the quick loop; the one run at the end
stays.

`run_series.py` gains `--start`, `--stop` and `--games`. The driver running the
five was stopped (it was waiting on run 1, which runs on as it was) and is
started again for runs 1 and 2.

### The port made faster: what a run spends its time on (Plone, same day)

Run 1 of the measurement took 3 h 40 min on Kaggle (1,801 s a game against the
847 s of the four games measured before; sb26 6,351 s, 10.6 s a cycle). At that
pace 110 games at four at once would take about 13.8 h. Plone asked whether the
computing could be made faster, and approved a port-side optimization, tested
here.

**Where the time goes, profiled** (sb26, 60 cycles, the exact inducer; the
profiler inflates many small calls): 504 s in the daemon's steps, of which 409 s
writing the commits — 346 s the snapshot encoder, which asked each cell of every
grid whether it was a dataclass (168 million calls), and 54 s the commit store
writing its tree — and 90 s the whole loop, mind and learning with it, 63 s of
that the `[event]` log's `copy.deepcopy` of each record. The mind and its model
are not what makes a run slow; writing down the state is. And every commit
reads the whole `[data]` store back from SQLite (13,796 decodes in 60 cycles)
and encodes it again, so a commit costs more as the store grows: why each cycle
of a run has been slower than the last.

**What was changed** — in `src/dil/`, the port; dil-core's formats and names
unchanged, as for the tree of 2026-09-27:
- `encode_snapshot_value`: plain values and rows of them recognised first, by
  type (a row checked in C); dataclasses last.
- `deep_freeze`: the plain data a record carries (values, lists, tuples, dicts,
  dataclasses of them) copied directly; anything else still `copy.deepcopy`.
- the commit store's canonical text: one `json.JSONEncoder`, not one per call
  (2.8 million in 60 cycles).

**Checked.** `scripts/check_fast_paths.py` plays a game with each fast path
wrapped, compared at every call with the code it replaced (the old encoder,
`copy.deepcopy`, `json.dumps`): vc33 120 cycles (grid) and sb26 40 — 87
encodes, 11,152 freezes, 3.3 million canonical texts, no difference. Reports
line for line the same as the same runs on the code before, but for key, time
and path. 325 pass, 34 skipped.

| run, this machine | before | after |
|---|---|---|
| sb26, 40 cycles | 96 s | 56 s |
| vc33, 120 cycles, grid | 54 s | 43 s |
| sb26, 200 cycles, side by side | 725 s | 375 s (1.93×) |

The longer the run, the more it gains. Not yet measured on Kaggle, and not in
the dataset runs 1 and 2 play. Left as it is, and the largest part remaining:
every commit still reads the whole store back and encodes it again.

### The port made faster again: nothing unchanged is read or encoded twice; a commit every 12 scars (Plone, same day)

Plone approved the deeper change left open in the entry before, and asked for
the scar count that fires a commit to go from 9 to 12.

**What was changed** — port-side, dil-core's formats and names unchanged:
- The SQLite `[data]` store holds what its table holds, decoded, in the table's
  order: read from the table once, kept as each write goes to the table
  (decoded from the text written). Every commit had read the whole table back.
- The daemon keeps each datum's snapshot encoding from one commit to the next
  while the datum is the same object (a stored `TaggedDatum` is immutable).
- The commit store keeps the text of each container it made at the last commit,
  held so its id is not reused: a container shared with the last snapshot is
  not made into text again; its objects are on disk already.
- A commit every **12** scars: declared by the run (`run_game.py`,
  `Daemon(commit_every=12)`); the port keeps dil-core's 9 in
  `store/decisions.py`, with the run's value noted beside it.

**Checked** (`check_fast_paths.py`, every call wrapped): vc33 120 cycles (grid)
and sb26 40 — 4.3 million canonical texts; 2,930 store reads, each the same as
the table decoded afresh; 23 data encodings kept across commits, each the same
as the data encoded anew; 23 snapshot addresses, each the same as a commit store
keeping no text gives. 325 pass, 34 skipped.

| sb26, 200 cycles, this machine | wall | commits |
|---|---|---|
| before any of this | 725 s | 34 |
| the first fast paths | 375 s | 34 |
| these, and a commit every 12 scars | **142 s (5.1×)** | 27 |

The report the same line for line as before any of it, but for key, time, path
and the number of commits. How much of the last step is the cadence and how
much the rest was not measured apart. Not yet measured on Kaggle; not in the
dataset runs 1 and 2 play.

## 2026-09-29

### The measurement on Kaggle: exact against grid on 25 games, four laws of curiosity on six (Plone, 2026-09-28)

Save & Run versions of `dil-arc3-learning` (not submissions), 600 cycles a game,
four at once, CPU; `scripts/kaggle/run_series.py`, outputs in
`scripts/data/kaggle/dil-run/m25-*/` (git-ignored); scores read from each run's
offline scorecard (`read_scorecard.py`, the toolkit's scoring, 0-100).

| run | code | games | score | levels | notebook |
|---|---|---|---|---|---|
| 1 exact, S2b | `4bbd221` | 25 | 0.00426 | 6 / 183 | 12,695 s |
| 2 grid, S2b | `4bbd221` | 25 | **0.14051** | 9 / 183 | 10,978 s |
| 3 grid, S2 | `97e79fd` | 6 | 0.57678 | 7 / 49 | 1,209 s |
| 4 grid, S2c | `97e79fd` | 6 | 0.57583 | 7 / 49 | 1,503 s |
| 5 grid, S2d | `97e79fd` | 6 | 0.56794 | 6 / 49 | 1,002 s |

Run 2 on the six games of runs 3-5 (ls20, vc33, ar25, lp85, tu93, lf52): 0.57583,
7 levels. Actions to each level completed (human baseline in brackets):

| game | S2b | S2 | S2c | S2d | exact S2b |
|---|---|---|---|---|---|
| ls20 (22) | 347 | 580 | 347 | — | — |
| vc33 (7, 18) | 74, 282 | 69, 282 | 74, 282 | 74, 282 | 73 |
| ar25 (32) | — | — | — | — | 585 |
| lp85 (17) | **17** | 17 | 17 | 17 | — |
| tu93 (19, 16) | 453, 108 | 445, 112 | 453, 108 | 286, 217 | 397 |
| lf52 (32) | 61 | 60 | 61 | 59 | 443 |

- **Grid against exact: 33 times the score on the same code and games.**
  lp85's level 1 in 17 actions, the human's own (100 points for it); lf52's
  in 61 against 443; tu93 and vc33 through level 2; ls20 through level 1. Exact
  held one level where grid held none: ar25 (585 actions), and m0r0.
- **The laws of curiosity make no difference that holds across the six.** S2c
  chose as S2b did choice for choice in four games, and scored the same in all
  six (its tie-break is rarely reached). S2 gained a little in lf52 and vc33 and
  lost in ls20 (580 actions against 347) and tu93; S2d lost ls20's level. S2b
  stays the default.
- **S4 was used once**: one choice "an act its hypotheses say brings the aim
  here", in lf52, in every run. The levels 2 of tu93 and vc33 did not come of it.
  Its criterion (ls20 and vc33 through level 2): vc33 yes, not through S4; ls20
  no.
- **Q4 against the S3 runs** (the same games, before the rate): the exact runs
  chose as S3's did, choice for choice, in ar25, ls20, sk48 and vc33 — the rate
  changed nothing for them. The grid runs parted from S3's before any aim was
  reached (ls20 at its 210th choice, vc33 at its 42nd), so by the rate — S4 and
  the laws of curiosity reach nothing before that — and ls20, with no level in
  S3's grid run, completed level 1.
- **Time on Kaggle, the faster port** (runs 3-5 on `97e79fd`): with the same
  choices as run 2 (S2c, four games), ls20 1,063 → 574 s and tu93 2,832 →
  935 s; ar25 567 → 777 s and lp85 294 → 460 s — slower, on the same choices, in
  a notebook playing six games against 25: not traced, taken as the machine's.
  The six under S2c averaged 771 s against run 2's 1,439 s. At that ratio,
  run 2's 25-game mean (1,411 s) would be about 755 s, and 110 games four at once
  about 5.8 h — an estimate from six games, not measured on 110.

### Goal and aim; the language model's earlier form gone; its successor's words name no game (Plone, 2026-09-28)

Point 10 of the measurement's report, part 1, as settled with Plone on
2026-09-28 (the entry "Goal and aim, settled").

- **The mind holds one aim** (`src/mind/mind.py`). The task prior's `aim`
  becomes its `goal` (`TASK_GOAL`): an instruction from outside. The mind's aim
  takes the goal's value; when no goal comes back with what it asked its memory
  for — it waits `GOAL_WAIT = 1` cycle past the one it asked in — it holds its
  own, `OWN_AIM`: the region reports something other than what it has been
  reporting most, in a state it has not ended in (Plone's precision: an aim of
  its make-up, grounded in what comes back; seeking an end excluded, since the
  host declares its ended states). The learning holds the same aim, handed by
  the mind (`hold_aim`), and no longer reads one from the prior: the second copy
  is gone. Why the wait: the answer to the mind's first question comes back in
  the next cycle, after the region's report (the commands of every run begin
  `(2, None), (2, act)`), so a mind that took its own aim at once would act on it
  where a goal was on its way.
- **The earlier form removed**: `LanguageModel` and all of `language.py` that
  only it used (`propose`, `GOAL`, want, `ASK`), its seat `src/arc3/mind.py`,
  `prior:mind-aim` (`src/arc3/aim.py`), the mind's seams only it used (want, an
  aim's `within`, the goal come sooner), `Proposal.want`, `Thinking.aim`,
  `Context.missed`, `--mind` in `run_game.py`, `run_competition.py` and the
  builder, and its tests: 30 of `test_arc3_mind.py`, `test_arc3_directive.py`.
  Kept, moved: the body's test (`tests/test_command.py`), two of `extract_code`
  (to the language inducer's), and the API key's test, rewritten for the
  language inducer. `3b31806` keeps the earlier form, as submission `56588469`
  ran it. The builder's GPU notebook now runs the language inducer (`--served`).
- **The language inducer's words name no game** (Plone: the model only computes;
  an aim is the mind's to tell it). `prior:mind-task`'s `induce`,
  `induce_feedback`, `unforeseen` and `aimed` are rewritten: "a region", the
  acts by the host's names, what came back as the report's fields that are news
  (through the organs), and "The program is for a mind working toward this:
  ..." filled with the aim the mind holds. `TASK` and `FEEDBACK` removed. This
  replaces S5's "word for word", which Plone set aside for it on 2026-09-28.
- Tests: the aim takes the goal's value and is one; with no goal, the mind waits
  a cycle, then holds its own aim and acts; its own aim is a report other than
  the usual, never an end; the model is told what the program is for; its words
  name no game. 323 pass, none skipped.

**Checked: nothing changes where a goal is given.** ls20, vc33, ar25 and lp85,
600 cycles, grid, here, against Kaggle's run 2 (`4bbd221`, the same games on
Kaggle's machine; the mind is deterministic across machines): every choice line
the same — 2,400 of 2,400 — and the levels the same. Here the four took 263,
359, 334 and 108 s.

### Attention, idea (a), as an option (Plone, 2026-09-29: point 10, part 2)

Plone kept the idea of borrowing self-attention's way of working, with no
training: the mind weighs its experiences by how alike their situation is to
the one it stands in. The design is mine, put to him for review.

- **What it changes**: only how much an act is wanted (curiosity, and the odds of
  the aim the curiosity is ranked by first). Without it, the counts are over all
  the act did, everywhere. With `--attention`, over the `ATTENTION_K = 16`
  experiences of that act (or of that kind of it) whose situations are most like
  where the mind stands, each weighed by how alike raised to
  `ATTENTION_SHARPNESS = 4`, each counted as often as it was met; when they weigh
  less than `ATTENTION_MIN_WEIGHT = 1.0`, the counts over all, as without it.
  The three values are declared, not measured. Paths, the aim's ways, objections
  and expectation do not change.
- **How alike is the inducer's** (`Inducer.similarity`): the exact inducer's, and
  so grid's, is the share of cells equal between the two states, off the rows it
  takes for the clock; 0 for states of other shapes. The language inducer
  inherits the exact one's.
- **An experience keeps what attention reads**: how often it reached a situation
  not met before (`Edge.new`) and how often the aim came of it
  (`Edge.reached`), counted as the global counts are, at each step.
- **The trace**: a choice made by attention names the experiences it went by
  (`attended`: where, which act, the weight) and is built from their hypotheses
  (those written).
- Checked, off: ls20, 300 cycles, grid, here, against the code before it
  (`a2e307f`): the same 300 commands and the same 21,776 `[event]` records. On:
  the first choice that differs is the 73rd; 300 cycles took the same time.
- Also: `run_series.py` still passed `--mind learning`, which the builder no
  longer takes since part 1; removed. Series `a6` added (the six games, grid
  with and without attention). README's list of the mind's files still named
  `src/arc3/aim.py` and `mind.py`; corrected.
- Tests: how alike two states are; with attention an act is wanted by what it
  did where the mind stood alike, and without it by all; too little alike, as
  without it; the choice names the experiences and is built from their
  hypotheses. 327 pass.

### ar25 and lp85 slower on Kaggle with the faster port: traced here (Plone asked, 2026-09-29)

The measurement's entry above took ar25 (567 → 777 s) and lp85 (294 → 460 s)
as the machine's, untraced. Traced on one machine: ar25 and lp85, 600 cycles,
grid, S2c, at `4bbd221` (run 2's code) and at `e348d9e`, the four at once on
this machine's 24 cores. The same commands in each pair, the same levels (ar25
none, lp85 one).

| | `4bbd221` | `e348d9e` | memory (max RSS) |
|---|---|---|---|
| ar25 | 378 s | 329 s | 877 → 1,036 MB |
| lp85 | 118 s | 114 s | 195 → 228 MB |

So the code is not slower for either; the slowdown on Kaggle is not in it. What
it is there stays untraced: one run each, on a machine not seen, in a notebook
playing six games against 25, alongside other games. The port's gain is small
for these two (13 % and 3 %) against ls20 and tu93, where commits cost most;
the memory it holds — the store decoded, the texts of the last commit — is
18 % more.

### The repository checked for agreement: code with itself, texts with each other, texts with code (Plone, 2026-09-29)

Plone brought a list of sixteen points, from a check against an earlier state
of the repository (its line numbers were those before `a2e307f`). Each was
checked against `0bda6d8`; two had been fixed by `a2e307f` (the API key's test
no longer skipped; the README's recall of the task alone), one half (the
language model's earlier form is gone, but `base.py` still described it).
The rest held, and are fixed here.

- **T5 compared a frame's whole stack; the mind expects its last grid.** The
  expectation carries one grid (`organs._expected_payload`), so any stack
  deeper than one never fitted. Seen in a run: ls20, 300 cycles, grid — the mind
  foresaw the last grid of a six-grid stack at cycle 34, and T5 recorded a
  mismatch and scarred the frame (the mind counted 6 hits, T5 5). Fixed by a
  fifth declared deviation: T5 takes a host-declared `fit` (`FitRule`,
  defaulting to dil-core's whole-content equality), and the host declares Tag H
  as it stood in the text: the last grid of the stack, the rest of the frame as
  it came (`arc3.decisions.situation_fit`, passed by `run_game.py`). The same
  run again: T5 fits at the mind's six cycles (0, 1, 7, 34, 137, 271), one frame
  scar fewer, the same 300 commands. The observation keeps its whole stack.
- **The mind's thinking, as the texts told it, did nothing here.** The learning
  thinks only on the onlooker's word; on a failed expectation it has learned
  from the return already, and a body waiting gets no second proposal. The
  bounds (`MIND_THOUGHTS_PER_CYCLE`, `MAX_WAIT_THOUGHTS`) are seams no learning
  here uses. The texts now say so (CLAUDE, README, `mind.py`); no behaviour was
  added, which would be a design choice.
- **T3 asks the store again** when the field leans to explore
  (`T3_REASK_AFTER`, dil-core `1e0a22a`); CLAUDE and README said once, and
  `t3.py`'s own docstrings disagreed. Corrected.
- **The protocol version**: `DIL_PROTOCOL_VERSION` said 0.3.2 and was read by
  nothing, 47 headers said "against v0.3.3", the store's claim said 0.3.5. It is
  now 0.3.5, and the claim reads it; each header says the file was first ported
  against v0.3.3 and that the package implements the pinned version.
- **Docstrings of designs gone**: `grid.py` (the rule by count), `decisions.py`
  (`mind.transition_of`, "program"), `observe.py` (the program, two channels —
  there are three), `action.py` (no answer yet on what forms a move), `frame.py`
  (the stack's reading "not settled"), `host.py` (an `action:0` entity — it is a
  context), `mind.py` (it waits for its priors — it needs none), `dil/__init__.py`
  ("only the first ring"), `base.py` (the language model's earlier form kept).
- **Texts**: the protocol's size, 60 and 55 KB, is 63 KB (62,972 bytes);
  `scripts/README.md` said every current script was run on 2026-09-24, and did
  not list `level_steps.py` or `check_fast_paths.py`; the second entry
  "Learning notebook version 5 scored: 0.05" is marked as the same result
  recorded again; `organs.py` names where its 159 and 157 come from
  (`scripts/data/frames.pkl`, counted again: 157 single grids, two stacks of six).
- **377 and 379, 83 and 85** (version 5's level 1 in ls20 and vc33): the first
  are `level_steps.py`'s, which counts RESET apart; the second the scorecard's,
  which counts a RESET as an action (`Card.inc_reset_count`) except one that
  begins a play — two of the four RESETs before each level began one (the card's
  first two plays hold no action).
- Checked and sound: every module under `src/` imports, every `__all__` names
  what exists, `mind` imports nothing of `arc3`, `dil` nothing of `arc3`, `mind`
  or `world`; the 22 scripts that no longer import are those
  `scripts/README.md` declares; `run_agent.py:91` is dead code behind
  `if False`, in one of them.
- Tests: a frame fits by the last grid of its stack; what the mind expected
  rightly of a deep stack is not recorded a mismatch (it fails without the
  fit). 329 pass.

### Attention measured on the six games (point 10, part 2)

Kaggle, notebook `dil-arc3-learning` version 11, code `e348d9e` (before T5's
fit), grid, S2b, `--attention`, 600 cycles, the six games four at once
(`run_series.py a6 --start 1`). Against grid S2b without it: the m25 series'
run (`4bbd221`, the same mind; the code since chooses alike, checked on ls20).

| game | without: levels, (actions, baseline) | with attention |
|---|---|---|
| ar25 | 0 | 1: (472, 32) |
| lf52 | 1: (61, 32) | 1: (61, 32) |
| lp85 | 1: (17, 17) | 1: (17, 17) |
| ls20 | 1: (347, 22) | 1: (342, 22) |
| tu93 | 2: (453, 19), (108, 16) | 2: (446, 19), (119, 16) |
| vc33 | 2: (74, 7), (282, 18) | 2: (74, 7), (384, 18) |

- Levels 7 → 8 (ar25's first, at 15 times its baseline); the six's mean score
  0.576 → 0.573 (the toolkit's scale, 0-100). vc33's second level took 102
  actions more, tu93's second 11 more; ls20's first 5 fewer, tu93's first 7.
  One run each: no difference here is shown to be more than chance.
- **Attention was used, and could not tell situations apart.** Most choices by
  curiosity went by it (ar25 609 of 627, ls20 437 of 445, tu93 325 of 333; lp85
  59 of 83). But the experiences it attended to were nearly all alike to where
  the mind stood: in ls20 their similarity ran 0.985-0.988 (10th to 90th
  percentile), in ar25 0.87-0.97, in tu93 0.82-0.995. The share of equal cells
  off the clock is carried by what never changes — most of a 64×64 grid — so
  every state is like every other, and the 16 "most alike" are close to any 16.
  Raised to the 4th power, 0.988 is still 0.95.
- Time: ar25 took 1,214 s against the fast port's 777 s under S2c (runs 3-5; not
  the same law, so not a clean comparison); the other five 381-955 s. The
  sorting over every experience at each choice is the likely cost; not traced.
- So, as it stands, attention changes little because its measure of alike does
  not discriminate, not because weighing by situation was tried and failed.

### Submitted: `56658708`, notebook `dil-arc3-learning` version 12 (Plone, 2026-09-29)

Plone: the latest code, with T5's fix and with attention. Code `a33d954` (the
dataset's served `decisions.py`, `t5.py`, `learning.py` and `run_game.py`
compared with the repository's before the notebook ran: the same); arguments
`--inducer grid --curiosity new --attention`, 600 cycles a game, four at once,
CPU. Submitted 01:33:30 UTC, PENDING; the day's one submission.

The Save & Run played the six games offline: no error, each exited 0, and the
same levels and actions as version 11 (`e348d9e`, before T5's fit) — 8 levels
of 49, 3,594 actions, 0.57295 on the toolkit's scale. T5's fit changed no
choice, as on ls20 here. Outputs in `scripts/data/kaggle/dil-run/output-submit-v12/`.

### Every thing offered; a click's kind read by its colour first (Plone, 2026-09-29)

lp85's second level, traced in version 12's store: 581 clicks on 65 cells, not
one changed a cell, one state all level. Checked with the inducer's own
`things()`: level 1 had 40 regions, all offered, its two arrows (colour 8 and e,
40 cells each) 35th and 36th — found at the 9th action; level 2 had 74, and 64
were offered, all of 1, 2 or 4 cells; its six arrows (10 cells each) were 67th
to 72nd, cut. And a click's kind was (colour, size): the arrows of level 1,
(8, 40), taught nothing of level 2's, (8, 10).

Plone chose (a′) and (b) together:
- **(a′)** `things()` returns every region, the ground left out
  (`MAX_CLICK_TARGETS` removed); which to try is the mind's curiosity.
- **(b)** `Inducer.coarse`: the exact inducer (and so grid) puts a click's kind
  (colour, size) within (colour). The learning keeps the same counts for the
  coarser kinds and wants a kind by its coarser one first, then itself.
- Tests: every thing is offered beyond 64; a click is of its colour first; what
  a colour did carries to a thing of that colour at another size. 332 pass.
- Here, lp85, 600 cycles, grid, attention: level 1 at 17 actions as before; in
  level 2 the arrows of colour 8 were clicked 572 times, 561 reaching a state
  not met; the level's moves ran out 12 times, and no second level. 559 s.

### The learning made neutral in its code and words (Plone, 2026-09-29)

Plone: `learning.py` is the mind's, and must be absolutely neutral — for every
environment and situation; a model may be changed for a particular problem, the
learning may not. Checked against that, and changed with the same behaviour:

- It copied a state as rows (`[row[:] for row in ...]`): now `Inducer.copy`.
- It wrote the region's report into a hypothesis's form (`hasattr(form,
  "status")`): now `Inducer.reported`.
- A hypothesis's tag `object: "frame"` was this host's word: now the host's
  declaration, `Organs.state_object` (arc3: `"frame"`, as before).
- Words and names of one region: "colour" and "size" in the curiosity's
  docstring, "the clock's doing (a budget of acts)" in a comment; `level` (the
  odds of the aim) → `aim`, `_grid_of` → `_raw_of`, `holds_off_clock` →
  `holds_by_situation`, `frame_calls` → `steps`, `Choice.frame_call` → `step`.
- Checked: ls20, 300 cycles, grid, attention, at `e7eb812` and after: the same
  300 commands, the same 21,680 `[event]` records. 332 tests pass.
- Noted, not done: `Act` is (id, x, y) in the mind's organs (CLAUDE.md, open).

### Every thing offered and coarse kinds, measured on the six (version 13, `e7eb812`)

Kaggle, `dil-arc3-learning` version 13, grid, S2b, attention, 600 cycles, four
at once. Against version 12 (`a33d954`): the same 8 levels; 0.573 → 0.677 on the
six. lf52's first level 61 → 41 actions (baseline 32); vc33's 74 → 71 and 288 vs
384 for its second (baselines 7, 18); the other four as before. lp85's second
level still not reached, as here (the counter row taken for where it stands:
LOG above). Time: lp85 987 s (324), vc33 1,000 s (776), ar25 995 s (1,178), the
rest 490-842 s.

### Submission `56658708` scored 0.00 (same day)

COMPLETE with 0.00 by 02:36 UTC, submitted 01:33: under 63 minutes, where some
110 games take 5-6 hours by the offline pace and `56623380` took about nine. So
the scored rerun ended early. Its Save & Run (the same version, arguments and
code) played six games without error; the rerun's own path (the gateway, the
scratch stores) is unchanged since `56623380`'s 0.05. Kaggle shows no log of
the rerun, and the cause is not known. Suspects: a hidden game that breaks the
code changed since `f76ff5f` in every game early; resources; and a new dataset
and notebook version (13) pushed to the same notebook at about 02:07 UTC while
the rerun ran. The six games offline and here (with sb26 and sk48) do not break
it.

### The 25 games at 60 cycles: tn36 filled memory; the submitted code did not break (same day)

Two Save & Runs of the competition's 25 games, 60 cycles, grid, attention:
- **`3fa6836`** (version 14): 24 exited 0; tn36 was killed (-9) at its 37th
  cycle. Here, with tn36's environment files downloaded from the competition
  (`environment_files/`, ignored): `MemoryError` at 4.9 GB, in the search for a
  way to where a held hypothesis says an act brings the aim — every imagined
  situation asked of every act that can be put on a thing, each prediction a
  grid, all kept in `_applies`, never dropped. With 64 things at most, the m25
  series' tn36 played 600 cycles (922 s): the cause is (a′).
- **`a33d954`** (version 15, the code submitted as `56658708`): all 25 exited
  0, no traceback. The submission's 0.00 is still unexplained.

Fixed: what the learning predicts for a situation it has not stood in is kept
for that choice only (`_imagined` cleared at each choice; `_applies` holds only
situations stood in), and a choice makes at most `MAX_IMAGINED_PREDICTIONS =
20,000` predictions there (declared, a bound on work), past which it looks no
further past where it has stood. Here: tn36 60 cycles at 287 MB, exit 0 (and its
first level); ls20 300 and lp85 600 cycles the same commands as before (lp85
1.4 GB at most, ls20 0.7 GB). 332 tests pass.

### The 25 games at 600 cycles on the latest code (notebook `dil-arc3-mind`, `f27606c`)

A notebook of its own (`--notebook dil-arc3-mind`, version 1), grid, S2b,
attention, every thing offered, coarse kinds, imagined predictions bounded; 600
cycles, four at once. All 25 exited 0, no traceback.

- **13 levels of 183, 0.320** on the toolkit's scale, against the m25 series'
  grid S2b (`4bbd221`): 9 levels, 0.141. New first levels: tn36 (35 actions,
  baseline 32 — 2.99 for the game), r11l (53 / 22), bp35 (273 / 21), ar25
  (472 / 32). Faster: lf52 (41 / 32), sp80 (243 / 39). Slower: su15 (481 / 22).
  Still none in 14 games.
- Time: 531 s (ft09) to 1,831 s (sp80), a mean of 1,036 s a game. At that pace
  110 games four at once take about 7.9 hours, against the notebook's 8 h 40 min
  deadline: a thin margin, from 25 games, not 110.

### The clock read in columns too, and by how a counter counts (Plone, 2026-09-29)

**Correction.** The entries above say lp85's second level was stuck on "the
counter row". It was a column: at each click one cell of column 0 (the left
edge, colour e) turned 5, top to bottom — row 0 at cycle 19, row 63 at 78 — and
at the end of the column the level ended (GAME_OVER every 61 cycles). Row 1
hardly changed. The rows' rule could never take it for the clock: each step
changed a different row.

- **The rule** (`exact.py`; grid inherits): besides the rows' rule as it was, a
  row or a column that, in each of the last CLOCK_WINDOW steps and whatever the
  act, changed by 1 to CLOCK_CELLS cells, always one colour into one other, next
  to the cells it changed the step before, is the clock — a bar counting a cell
  at a time. A thing moving along a line changes it two ways and is not taken.
  The clock's columns are left out wherever its rows are: a situation's
  identity, similarity, the things, grid's hypotheses. A clock datum names its
  `columns` when it has some.
- Tests: a column counting a cell at a time is the clock under one act, and two
  grids that differ only there are one situation; a cell moving down a column
  is not. 334 pass.
- Here: ls20 300 cycles, the clock rows 61-62 and the same commands as before;
  vc33 300, row 0; lp85 600, column 0 — and still no second level: off column
  0, its first 60 clicks gave 60 grids, none again. The arrow drives a belt of
  tiles longer than the level's budget of moves, so no state comes back within
  one try; curiosity for somewhere new has nothing to tire of there.

### The clock in columns, measured on the six (notebook `dil-arc3-mind` version 3, `560f667`)

Against version 13 (`e7eb812`): 8 → 7 levels, 0.677 → 0.675. The five others
played as before, level for level and action for action; lp85's second level
still not reached (its column 0 now the clock). **ar25 lost its first level**
(472 actions before): its column 63 is a counter too — one cell b → 5 at each
act but 6 and 7, top to bottom — taken for the clock at cycle 105. Off it, ar25
met 260 situations, not 568: before, the counter had made nearly every step
somewhere new, and the first level came of that. Now the mind revisits, its
choices differ (act 5 tried 17 times, not 125; 92 choices toward a state with an
act not yet taken, not 2), and no level came in 600 cycles. Its expectations
held 110 times, not 414: the clock is not predicted (open), and a hypothesis
met again now expects the counter as it was. Time 747-1,148 s a game.

## 2026-10-04

### Nothing pushed to Kaggle while a submission is scored (Plone)

Proposed after `56658708`: a notebook of its own for submissions, another for
measurements. Plone: not needed — while a submission is being scored, push
nothing to Kaggle and measure here; that leaves nothing to conflict, the shared
dataset included, which separate notebooks would not have covered. Written in
CLAUDE.md, the submission pipeline. `dil-arc3-mind` stays for measurements that
need Kaggle's own times. Also noted: on 2026-09-29 Gem wrote that Plone had
approved the separate notebook; he had approved only the 25-game check (a).

### A RESET at a level's start lost every level gained; now the runners keep RESET to the level

From a public notebook (scottlegrand, `taaf-flashnext-sheetu12b-0922`, a fork of
Tufa Labs' Duck), which sets `ONLY_RESET_LEVELS=true`. Read in the engine
(`arcengine/base_game.py`, `handle_reset`): without it, a RESET is a full reset —
back to the first level — when the level's action count is 0, and the count is
zeroed at every `set_level`: on entering a level and after a level's restart.
Checked here on lp85 with the 17 clicks this agent's run took to level 1: then a
RESET at once — without the variable, levels 0; with it, levels 1.

- In the stored runs (81 games: the 25 at 600 cycles on `f27606c`, the two
  25-game checks, the six on `560f667`) no RESET came at a count of 0: 231
  followed the region's end, 11 came mid-level after another act. No level was
  ever lost; the risk was there all the same (the mind resets when every act
  known is objected to, or nothing is left to try).
- `run_competition.py` and `run_game.py` set `ONLY_RESET_LEVELS=true` (unless
  set otherwise) before the toolkit loads. It reaches the games their process
  holds — the offline runs and Save & Run. A scored rerun's games are the
  gateway's; whether it reads the variable is not known. 334 tests pass.

### The clock: an edge bar counted by its changes, not by every step

The same public notebook's survey says every public game draws a bar counting
actions at the edge, some moving 3 cells at a time (sp80). Replayed through the
perception of `2ce3b1b`, the 25 games' stored steps (the 600-cycle run on
`f27606c`) gave a clock in 14. In the other 11 the bar moves on some acts only
(cd82, cn04, dc22, g50t, ka59, tr87, wa30: a cell at a time, the same colour
change, each next to the last; m0r0 two bars; sc25 two columns), and the rule
asked for a change at every one of 6 steps. sp80's own (row 0) was already found.

- Added (`exact.py`; grid inherits): a row or column within COUNTER_EDGE = 2
  lines of the edge whose last COUNTER_TICKS = 4 changes were each 1 to
  COUNTER_CELLS = 3 cells, all one colour change, each next to the one before,
  is the clock — however many steps between. The rows' rule and the per-step
  counter rule stay. Declared, not measured.
- Replayed: a clock in 24 of 25, most by the 5th to 12th step; sk48's bar (row
  53, moving on some acts) still not found. Without the edge condition, 25 — and
  a growing thing taken for the clock inside s5i5 (rows 9, 11) and vc33
  (columns 6, 7): the condition kept.
- Tests: an edge bar that counts every other step is the clock; an inner line
  growing every other step is not. 336 pass.
- Here, 600 cycles, the seven games on this machine, actions per level counted
  without RESET: vc33 70 → 68 for its first level (283 its second, as before),
  tn36 35 → 33, lp85 17, ls20 340, as before; ar25, sb26, sk48 none, as before.

### Version 16 of `dil-arc3-learning` (`5511bfb`): the candidate's Save & Run, 25 games at 600 cycles

Built for a submission Plone is to review; code `5511bfb` (the clock in columns,
before the RESET and edge-bar changes of later the same day). All 25 exited 0, no
traceback, the scorecard closed. **12 levels, 0.477** (the 25 at 600 cycles on
`f27606c`: 13, 0.320). r11l's first level in 20 actions, under its baseline of
22 (53 before): 4.76 for the game. ar25's first level lost, as on the six (its
counter now the clock). The other ten levels as before, action for action.

Time: 519 s to 2,043 s a game (sp80; bp35 1,777 s), a mean of 1,054 s; the run
took 7,154 s for 25 games four at once, 286 s a game. At that pace 110 games take
about 31,500 s, against the deadline's 31,200 (9 h less 20 min) and before the
notebook's own start-up: some games would not be played.

### Version 17 (`04d610a`, no attention): an empty scorecard, the faster run, and three levels slower

Notebook `dil-arc3-learning` version 17, grid, S2b, no attention, 600 cycles,
the 25 games. All exited 0, no traceback; 3,691 s in all (version 16: 7,154 s),
560 s a game on average, 932 s at most (bp35): 110 games four at once about 4.5
hours.

- **The scorecard came back empty** (no environment, no action) — caused by
  `ONLY_RESET_LEVELS`, set this morning. The toolkit opens a play on its
  scorecard only on a RESET that is a full reset (`Scorecard.update_scorecard` →
  `new_play`); with the variable every RESET is a level reset, the first one
  too, so no play is ever opened and every action is dropped. The games were
  played all the same (the runs' own reports and stores). In a scored rerun the
  games and the scorecard are the gateway's, so the variable set here likely
  neither helps nor harms there; offline it breaks the scorecard. To be undone.
- From the stores (actions per level without RESET, the same reading for both;
  scores estimated with the baselines, as the toolkit computes them): the same
  12 levels, about 0.27 against version 16's 0.51. Slower: r11l 20 → 115 actions
  (its baseline 22), lf52 41 → 139 (32), sp80 236 → 564 (39). Faster: bp35 266 →
  164, tu93 438 → 288 and 116 → 104, tn36 35 → 33, vc33 70 → 64 and 283 → 277.
  Two changes stand between the versions — attention off, and the edge bar
  counted by its changes — and which slowed which game is not known.

`ONLY_RESET_LEVELS` taken out of both runners again (Plone approved): it emptied
the offline scorecard. The engine's reset as it is stands; a RESET at a level's
count of 0 still goes back to the first level — not met in 81 stored runs.

### What slowed r11l, lf52 and sp80: attention, and the edge-bar rule (four combinations, here)

The three games' environment files downloaded (`environment_files/`, ignored);
600 cycles each, here; the old clock from a worktree at `560f667`, the new at
`10ad969`. Actions to the first level, RESET not counted:

| | old clock + attention | old clock | new clock + attention | new clock |
|---|---|---|---|---|
| r11l (baseline 22) | 20 | 174 | 19 | 115 |
| lf52 (32) | 41 | 41 | 138 | 139 |
| sp80 (39) | 236 | 368 | 263 | 564 |

- The first column is version 16 to the action, the last version 17 (without
  `ONLY_RESET_LEVELS`, which so changed nothing it did): the mind chooses alike
  here and on Kaggle, and the variable did not touch play.
- **Attention** carried r11l (174 → 20, 115 → 19) and sp80 (368 → 236, 564 →
  263); lf52 alike either way. Turning it off is what lost r11l's level under
  its baseline.
- **The edge-bar rule** cost lf52 (41 → 138 with attention or without), though
  both rules took the same row 0 for its clock — the new one by the 5th step,
  the old by the 7th — so its run went another way from there; with attention,
  r11l was the same and sp80 27 actions slower.
- Seen on the way: in r11l the rows' rule takes rows in the middle of the board
  for the clock — 6 to 23 and more with the old rules, 8 rows with the new — so
  the mind reads past part of what it plays on. Not traced yet.
- Attention doubles a run's time (version 16: 7,154 s for the 25; version 17:
  3,691 s): with it, 110 games overrun the deadline as it is.

### A cell blinking as the acts alternate was taken for the clock (r11l); now a clock row counts each cell once

Traced on r11l's stores: clicking one thing and another in turn, the mark of
what is chosen turned 0 → 3 and back at every step (rows 13-14, columns 56-57;
row 38, column 49), under three kinds of click; the rows' rule (a row changed at
every one of 6 steps, by 1 or 2 cells, under 3 kinds) took those rows for the
clock — up to 28 rows of the board with the old rules, 4 to 8 with the new — and
the mind read past them. Asking that each way of change come under two kinds of
act did not hold: a third thing clicked turned the mark both ways too.

- The rule now asks that no cell of the row change twice within the window: a
  bar counts a cell and moves on; a blinking cell is not a clock. The counter
  rules already ask one colour change, each next to the last.
- Replayed: r11l's three stored runs keep only column 0; the 25 games a clock in
  24 as before; re86 keeps row 63 and loses rows 53-55, which the rows' rule had
  added at its 91st step; sb26 keeps row 53 only. The clock test rewritten as a
  counting bar (it used a blinking cell); a blinking cell under three kinds is
  no clock. 337 pass.
- Here, 600 cycles: ls20 with attention the same commands as before; r11l's
  first level in 19 actions with attention, 115 without, as before — the rows
  were taken after it; situations met 299 and 202 (before the fix 291 and 209).

### Attention made faster, and where the time of a run goes

- **Attention**: within a choice the experiences are ranked once by how alike
  and what each act, kind or coarser kind weighed is kept (the sort is stable,
  so ranking all and keeping those a kind holds is what sorting those alone
  gave); before, every candidate thing re-sorted every experience twice.
  r11l, ls20 and lf52 at 600 cycles with attention: the same commands as before.
  The time hardly moved (r11l 1,058 → 1,068 s, ls20 992 → 992 s): the sort was
  not where the time went.
- **Profiled** (r11l, 200 cycles, attention, 236 s): `grid_key` 68 s (29%), most
  of attention's 44 s inside it (`_mask` keys each state by it); a commit's
  snapshot 42 s (18%). Since the clock's columns, `grid_key` built its bytes cell
  by cell through a generator.
- **`grid_key` row by row**: each row's bytes made at C speed (`bytearray(row)`,
  the clock's columns zeroed in it; a value outside 0-255 masked as before). The
  same key as the old one on 8,000 random grids (sizes 1-64, clock rows and
  columns, columns past the edge, negative and large values). The same commands
  on r11l, ls20, lf52 and ar25 at 600 cycles; r11l 1,068 → 794 s, ls20 992 →
  866 s, lf52 1,011 → 1,019 s, ar25 845 s (two runs at once here). 337 pass.
- Also seen: here attention adds about 12% to a run (r11l 940 s without, 1,058 s
  with, before these changes), not the doubling between versions 16 and 17 on
  Kaggle — those differ in the clock rule too, and the old one left the clock
  unfound in 11 games, every step a new situation.

### Version 18 (`1bbd7e2`, attention, the clock rules of today, faster code): 15 levels, 0.502

Notebook `dil-arc3-learning` version 18, grid, S2b, attention, 600 cycles, the 25
games. All exited 0, no traceback, the scorecard full again.

- **15 levels of 183, 0.502** (version 16: 12, 0.477). New first levels: m0r0
  (74 actions, baseline 30: 0.78 for the game), cd82 (513 / 55), sc25 (557 / 36).
  tu93's second level in 50 actions, not 119 (0.46 for the game); bp35 144, not
  273; tn36 33, not 35; vc33's first 69, not 71. Slower: lf52 138, not 41 (as on
  the four combinations), sp80 271, not 243. r11l 19 (its baseline 22), lp85 17,
  ls20 342 as before.
- Time: 5,171 s for the 25 four at once (version 16: 7,154 s), a mean of 767 s a
  game, 1,222 s at most (sp80; bp35 1,155 s): 207 s a game in all, so 110 games
  about 6.3 hours against the deadline's 8 h 40 min — from 25 games, not 110.

### Submitted: `56820389`, notebook `dil-arc3-learning` version 18 (Plone, same day)

Code `1bbd7e2`, `--inducer grid --curiosity new --attention`, 600 cycles a game,
four at once, CPU; submitted 09:43:54 UTC, PENDING; the day's one submission.
Its Save & Run: the entry above. Nothing is pushed to Kaggle until it is scored.

### The whole store is the agent's memory: protocol v0.3.6 and specification v8 (Plone)

Plone: "Toàn bộ store/ của dil là trí nhớ của agent. Trong đó, [event] không thể
bị sửa hay ghi đè mà chỉ được ghi mới và được đọc, còn [data] thì có thể." — to be
written into the specification and the protocol, not CLAUDE.md alone, and the
readings that mislead on it corrected. Before, Gem had cited a rule "memory is the
store" that is written nowhere: the phrase appears once, in quotes, in this log
(2026-09-24); what is written is CLAUDE.md's "Memory is what the store held
before the cycle that asks" (when a query is answered) and "it may read anything
in the store".

- In dil-core, where the documents live (Plone chose it): protocol v0.3.6 and
  specification v8 (`6f96857`, changelog `c45cff4`; not pushed yet). The rule in
  the protocol's terminology (§3) and as a §9 item, and in the specification.
  Corrected: the activity record "kept out of the agent's memory" → kept out of
  experience, part of the memory that is only appended to (§9); "[data] is
  mutable, overwritten each cycle" → its content may be rewritten and its
  position moves (§9, the specification, dil-core's AGENTS.md); "an [event] item
  carries no knowledge at all" → no working knowledge, still memory. No
  requirement on an implementation changes: the code of either repository is
  untouched and the store's claim stays 0.3.5.
- Here: both copied byte for byte (SHA-256 checked against dil-core), the old
  copies moved by `git mv`; `spec/README.md`'s table, CLAUDE.md (the rule, the
  protocol's file name), README.md's citation, and the note on
  `DIL_PROTOCOL_VERSION`. Code comments citing the specification's sections are
  left as dil-core leaves its own.
- Decided with Plone for what follows: (A) every change in what the mind learns
  goes into `[data]`, as revisions, with the snapshot's size measured first; (B)
  what any inducer computes from, the mind reads back from the store — for every
  inducer, not the language one alone. Design to come.

The claim that no layer learns from an activity record withdrawn (Plone: the
mind can read what the store holds and hand it to its learning, a way of
learning). In dil-core `0b9c766` (changelog `74c85b1`, not pushed): out of the
protocol's §6.4 and §9, the specification and AGENTS.md; the record stays trace,
not experience, never a scar; the changes line counts two corrected readings,
not three. Copied here again, byte for byte. Not yet changed, for Plone: the
code comments that repeat the claim (dil-core's `recollection.ts`, `cycle.ts`,
`resist-event.ts`, and this port's), and `recollection`'s reasoning that "the log
is an Other and not a memory" (§7: an agent treating the log as its own past
would claim continuity), which stands against the new rule.
