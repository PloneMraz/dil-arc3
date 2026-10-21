# The paper — tables (draft)

Every number is read from `LOG.md` (the entry named in brackets) or from Kaggle's
list of submissions (`kaggle competitions submissions`), and is checked again
against them before it enters the Writeup or the PDF. Scores are RHAE in percent,
as Kaggle and the toolkit's scorecard give them: the leaderboard's on the hidden
games, the Save & Run's on the 25 public games (`environment_files`) at 600 cycles
a game, four at once.

## Table 1 — every submission

| Submission | Notebook, version | Code | What it is | Leaderboard | 25 public games (levels of 183, score) |
|---|---|---|---|---|---|
| `56462757` | starter kit | — | the starter's random agent | 0.02 | — |
| `56600038` | gateway probe | `a86dbff` | the random agent on dil-arc3's road | 0.06 | — |
| `56588469` | `dil-arc3-run` 12 | `3b31806` | a language model (Qwen3.8-Flash-Next) in the learning's place, 60 cycles | 0.00 | — |
| `56623380` | `dil-arc3-learning` 5 | `f76ff5f` | the learning mind, no weights | 0.05 | — |
| `56658708` | 12 | `a33d954` | grid inducer, S2b, attention; the rerun ended early, cause not known | 0.00 | — |
| `56820389` | 18 | `1bbd7e2` | attention; the clock read in rows and columns | 0.26 | 15, 0.502 |
| `56887238` | 23 | `b6a95ac` | the store as the mind's memory; experiences as its expectation | 0.25 | 13, 0.499 |
| `56934496` | 26 | `a6c4563` | suspects: where the aim may lie, tested before it has come | 0.02 | 15, 0.515 |
| `56983446` | 28 | `9e69156` | version 23 with moves, blocks and into aims once the aim has come | 0.25 | 13, 0.514 |
| `57371259` | 35 | `b4d7d5a` | collisions turn the mind; the field carries its history (B1) and the counts follow it (B2) | 0.26 | 16, 0.518 |
| `57443352` | 37 | `9fcaafc` | as 35, its stores verifying under dil-core's verifier | 0.25 | 16, 0.491 |
| `57470744` | 41 | `963b7fb` | as 37, each turned choice naming its return and its thought | pending | 15, 0.489 |

[LOG: "v12 scored: 0.00", "The gateway probe scored 0.06", "Learning notebook version 5
scored: 0.05", "Submission `56658708` scored 0.00", "Version 18 …", "Submission `56820389`
scored 0.26", "Version 23 …", "Submission `56887238` scored 0.25", "Version 26 …",
"`56934496` … scored 0.02", "Version 28 …", "`56983446` … scored 0.25", "Version 35 …",
"Version 35 scored 0.26", "Version 36 (Save & Run) …" (Kaggle's version 37), "Submission
`57443352` scored: 0.25", "Version 40 …", "Version 41 …"]

## Table 2 — one change at a time, on the 25 public games

Each Save & Run against the one before it; what changed, and what it did.

| Version | What changed | Levels | Score | Kept |
|---|---|---|---|---|
| 16 | the clock in columns | 12 | 0.477 | — |
| 18 | attention; the clock rules of today; faster code | 15 | 0.502 | yes |
| 19 | (A) and (B): the store as the mind's memory; synced once a cycle | 15 | 0.502 | yes (no level changed) |
| 20 | `made` curiosity (B1), C1, FORESEEN_LAW | 15 | 0.488 | no |
| 21 | S2b, C1, FORESEEN_LAW | 13 | 0.364 | no (FORESEEN_LAW harms) |
| 22 | `made`, C1, no FORESEEN_LAW | 13 | 0.430 | no |
| 23 | S2b, C1; experiences as the mind's expectation | 13 | 0.499 | yes |
| 24 | P1 (a blocked hypothesis for an act that takes no place) | 12 | 0.499 | no |
| 25 | the objects inducer (first form) | 12 | 0.457 | no |
| 26 | suspects | 15 | 0.515 | no (hidden 0.02) |
| 28 | moves and into aims once the aim has come | 13 | 0.514 | yes |
| 30 | silence collides; a collision turns the mind; the field reaches it | 14 | 0.513 | yes |
| 32 | T1: each command tests what memory is least sure of | 13 | 0.379 | no |
| 33 | T1c | 12 | 0.255 | no |
| 34 | the report's collisions thought on; what an act did where it stood alike, expected again; the mind's vote on trust | 16 | 0.519 | yes |
| 35 | the field's carry (B1, 0.95) and the counts following it (B2) | 16 | 0.518 | yes |
| 37 | acts opaque to the mind; an act never taken never foreseen; the log's hash as dil-core's | 16 | 0.491 | yes |
| 38 | objects inducer, a move said only once seen three times | 15 | 0.500 | no |
| 39 | objects inducer, a thing known by its colours | 14 | 0.486 | no |
| 40, 41 | turned choices relinked to their thoughts; the world's prior recalled | 15 | 0.489 | yes |

[LOG: the version headings "Version 16 …" to "Version 41 …", and "The objects inducer
(step 3) on the 25 games" and "(step 4)". Versions 29 and 31 repeat 28 and 30.]

What it shows (Theory): before the first success a change reshuffles where the
mind explores, and the public games did not foretell the hidden ones — suspects
reached the most levels here (15, 0.515) and scored 0.02 hidden, against 0.25 for the
version it changed.

## Table 3 — ideas that failed

| Idea | Measured on | Result | Against |
|---|---|---|---|
| FORESEEN_LAW: of acts all foreseen, the one foreseen least surely first | 25 games | 13 levels, 0.364 (with C1) | 15, 0.502 (version 19); the law alone run on tn36 and sp80 |
| C2b: a ladder of looser aim hypotheses | 6 games | no level more; vc33's borne out once, refuted 195 times | — |
| P1: a blocked hypothesis for an act that takes no place | 25 games | 12 levels, 0.499 | 13, 0.499 |
| WAY_LAW: try an act here by the chance a way ends otherwise | ls20, tu93 | ls20's level in 564 actions; tu93 0.283 | version 23: 342 actions; P1 alone: tu93 0.571 |
| The objects inducer, first form | 25 games | 12 levels, 0.457 | 13, 0.499 |
| Suspects: where the aim may lie, tested before it comes | hidden games | 0.02 | 0.25 |
| Near at a step's scale (for suspects) | 6 games | 0.502 | 0.578 |
| An end as an experience | 6 games | 0.571 | 0.569 (no level more) |
| A repeated remark objected to everywhere | 10 games | every level the same; ar25 251 → 253 actions | — |
| Foreseen acts by doubt | 10 games | tn36's level lost | 33 actions |
| After the aim, toward what is like where it came from | 10 games | every level and action the same | — |
| Moves mirrored to the other three ways | 10 games | every level and action the same | — |
| Moves per thing | 10 games | every level and action the same | — |
| T1, five versions | 25 games | 13 levels, 0.379 (T1); 12, 0.255 (T1c) | 14, 0.513 |
| The language inducer (a served model writing `predict`) | 1–3 games | its programs right about one step in eleven; no level | — |
| The objects inducer, steps 3–4 | 25 games | 15, 0.500; 14, 0.486 | 16, 0.491 |
| … with states stood in before foreseen ones | 11 games | 1.098, m0r0's level lost | 1.103 |
| … with `made` curiosity | 11 games | 0.941, 11 levels | 1.103, 12 |
| … with a counter read away from the edge | 11 games + sk48 | sk48's situations 508 → 274, no level; 0.987 | 1.103 |

[LOG: "Version 21 …", "C2b tried and removed", "Version 24 …", "WAY_LAW tried and
removed", "Version 25 …", "`56934496` … scored 0.02", "Near at a step's scale", "An end
as an experience", "A repetition said again …", "Foreseen acts by doubt", "After the aim,
toward what is like …", "Moves mirrored …", "Step 3 of A, three ways", "Version 32 …",
"Version 33 …", the language-inducer versions 4–12, "The objects inducer (step 3) on the
25 games", "(step 4)", "A state it has stood in first", "Why the 25 games' situations
grow …".]

## The evidence (section 3)

From version 41's 25 stores [LOG: "The evidence on version 41's 25 stores"; "Point 4
again, on version 41's code"]:

- every store verifies under dil-core's verifier; dil-core's checker: §13.1, §13.3,
  §13.5, §13.6 pass in all 25, §13.4 partial in all (continuity is a third party's to
  say), §13.7 fails in six (cd82, dc22, g50t, ls20, m0r0, sc25: one source of resistance
  where the onlooker had no reason to object);
- 2,757 frame scars; 1,130 chains of a scar, the thought it set off and the choice it
  turned; 717 met the next return as expected; 60 met the act again where it collided,
  32 of them as expected every time;
- 1,742 turned choices, every one built from the return that collided, 1,740 naming the
  thought (the other two, each game's last choice, awaiting);
- Figure 2: lp85, `signal-9-0` → `written-9-0` → `written-9-3` → `written-9-2`, met
  again at cycle 22 as expected;
- individuals: I0 1.106, I1 1.016, I2 1.150, A1 (no Other) 1.040 on eleven games; the
  field's chain (tu93, I1 and I2 part at step 72 by the turn's hold); the Other's chain
  (m0r0, I0 and A1 part at step 71, through the field the onlooker had moved).
