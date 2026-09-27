# scripts/

The measurement and run scripts behind the numbers in `README.md` and
`LOG.md`. They were written in a session scratchpad on Windows and moved here
on 2026-09-24, so that the work is kept with the code it measured.

Run them from the repository root with the starter kit's interpreter, which has
the game engine:

```sh
PY=../ARC-AGI-3-Kaggle-Starter/.venv/bin/python
$PY scripts/<script>.py [args]
```

`_paths.py` works out where the repository, its `src/` and the starter kit are,
from where it sits, so nothing depends on where the workspace is mounted.

## Data

`scripts/data/` is git-ignored output.

- `frames.pkl` — 316 real transitions (`ls20` 159, `vc33` 157), the set every
  offline measurement here was scored on. **Reproducible exactly**:
  `$PY scripts/dump_frames.py scripts/data/frames.pkl` regenerated it on
  2026-09-24 and all 316 transitions were identical to the original.
- `prior-<game>-*/` — the durable store and `[event]` log of each `run_prior.py`
  run.

## Scripts that run against the current code

Each was run on 2026-09-24 and completed.

| script | what it measures | args |
|---|---|---|
| `wm_probe.py` | can an open model write an executable world model of `ls20` (exact-grid replay, counterexample feedback that keeps the best program) | `--game ls20 --endpoint URL [--no-think] [--data transitions.json]` or `--baseline-only` |
| `compare_programs.py` | re-scores every program in probe logs and says where its wrong cells are (the bar on rows 61–62, or elsewhere) | `LOG.json ... [--show LOG.json:ROUND]` |
| `export_transitions.py` | exports the recorded transitions as plain JSON, so the probe runs without this code | `[OUT.json]` |
| `kaggle/build_probe_run.py` | builds the Kaggle dataset and notebook that run the probe on an RTX Pro 6000 with vLLM, after checking every model file against Hugging Face's published hashes (`kaggle/qwen3_6_27b_fp8.manifest.json`) | `[--model 27b\|35b-a3b] [--rounds N] [--runs-per-mode N] [--max-tokens N] [--max-model-len N]` |
| `run_game.py` | a live game with the one mind in the loop: the host carries the frame, the model writes the program as data, reads what it asks the store for, and revises on mismatch; prints what the run's own `[event]`, `[data]` and commits say | `GAME CYCLES --endpoint URL [--model NAME] [--max-tokens N] [--think] [--alone] [--offline-dir DIR] [--remote HOST:PORT] [--out DIR]` |
| `run_competition.py` | plays every game an arcade offers on one scorecard, several at once, each game in its own `run_game.py --remote` process, with a deadline — the scored rerun's road, and the offline one | `--mode competition\|offline --endpoint URL --model NAME --out DIR [--base-url URL] [--offline-dir DIR] [--games a,b] [--cycles N] [--concurrency N] [--deadline EPOCH] [--max-tokens N] [--player random_game.py] [--mind language\|learning] [--stores DIR] [--drop-stores]` |
| `random_game.py` | the starter kit's random agent, played through `run_competition.py`'s road (`world/remote.py`) in place of the agent: a probe of that road, no model, no DIL | `GAME CYCLES --remote HOST:PORT` (launched by `run_competition.py --player random_game.py`) |
| `kaggle/build_dil_run.py` | builds the Kaggle dataset (dil-arc3's source) and notebook that run `run_competition.py` on an RTX Pro 6000 with vLLM: offline from the competition's `environment_files` on Save & Run, through the gateway in a scored rerun | `[--model 35b-a3b\|27b\|flash-next] [--game ls20,vc33] [--cycles 60] [--max-tokens N] [--max-model-len N] [--concurrency N] [--probe] [--mind learning]` — `--probe` builds the gateway probe instead: the random agent on that road, CPU, no model; `--mind learning` builds `dil-arc3-learning`, the learning mind on CPU, whose scored rerun keeps each store in scratch space and drops it once the game has played. A Save & Run of either notebook packs every store into one `stores.tar.gz` (Kaggle hands outputs back one file at a time): `kaggle kernels output <kernel> -p DIR`, then `tar -xzf DIR/stores.tar.gz -C DIR` |
| `kaggle/push_dil_run.py` | uploads the built dataset, waits until Kaggle serves that version (a file made after the upload, and `--must-have`), then pushes the notebook | `-m MESSAGE [--must-have PATH] [--wait SECONDS]` |
| `kaggle/make_manifest.py` | writes a model manifest from what Hugging Face publishes (sha256 for weights, git blob sha1 for the rest), for the notebook to check a Kaggle copy against | `HF_REPO REVISION KAGGLE_HANDLE OUT.json` |
| `dump_frames.py` | records transitions from both games | `OUT.pkl` |
| `verify_gate.py` | the host's boundary gate against live frames | — |
| `probe_frame.py` | the real shape and value range of frames | — |
| `try_reprs.py` | candidate effect representations | `frames.pkl` |
| `readlog.py` | reads a downloaded Kaggle kernel log | `LOG.json [N]` — not re-run, needs a log |
| `rules_text.js` | the rendered text of a JavaScript page (Kaggle rules, leaderboard) | `node scripts/rules_text.js URL OUT` |

## Scripts written against code that has since been removed

They are kept because the numbers recorded in `LOG.md` came from them. Run
them against the commit they were written for, from a worktree:

```sh
git worktree add ../dil-arc3-at-321d9e0 321d9e0
DIL_ARC3_SRC=../dil-arc3-at-321d9e0/src $PY scripts/model_vs_persistence.py scripts/data/frames.pkl
git worktree remove ../dil-arc3-at-321d9e0
```

| commit | what it still had | scripts |
|---|---|---|
| `b7b64d3` | the counting mind (`arc3.mind` before 2026-09-24) and the computation of the grid it read (`perceive.py`, `seeing.py`, `interpret.py`) — the two-mind era | run and completed at that commit: `run_prior.py` (also `admit`), `run_things.py`, `identity.py`, `seeing_measure.py`, `track.py`, `track_mover.py` |
| `321d9e0` | `arc3.model`, `arc3.effect`, `affordance_key` — the affordance era | run and completed: `diagnose.py`, `model_vs_persistence.py`, `three_arms.py`, `verify_shipped.py`, `run_loop.py`, `debug_vc33.py` · imports verified, not re-run (live games, minutes each): `field_trace.py`, `measure_recollection.py`, `run_agent.py`, `store_demo.py`, `measure_effect.py` |
| `147aab3` | the stuff-level readers `changes_of`, `contacts`, `interactions_of`, and `Region.kind` | run and completed: `see.py`, `contacts.py`, `surround.py`, `surround2.py`, `thing_repeat.py` |

`model_vs_persistence.py` reproduces the recorded figures exactly at `321d9e0`:
`ls20` 76% → 94%, `vc33` 41% → 69%. It carried a bug of its own — its last
loop built an ACTION6 move without coordinates and raised after printing the
results — fixed on the way in.

## What was not kept

The one-shot edit scripts (`port_*.py`, `mind_directive.py`, `prior_object.py`,
`arc3_describe.py`, `readme_prior.py`) replaced exact passages of source that
have since been committed; re-running them would fail on text that is no longer
there, and their effect is in the history. Scripts that served `dil-core` or the
website stay with the Windows backup until they are moved to their own
repositories.
