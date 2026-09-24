"""Build the Kaggle dataset and notebook that run dil-arc3, with the model at the mind.

    python scripts/kaggle/build_dil_run.py [--model 35b-a3b|27b] [--game ls20]
        [--cycles 60] [--max-tokens 12288] [--max-model-len 65536]

Not the probe: the probe ran a model on its own. This runs the agent — DIL's
loop over a live ARC-AGI-3 game, the host carrying the frame, the one mind —
the model and the program it writes — asking the store, writing its program as
data, revising it on mismatch —
with the model served by vLLM on the competition's RTX Pro 6000, internet off.
The game is played offline from the competition's own `environment_files`,
the runtime installed from its own wheelhouse (as Tufa Labs' public notebook
does). The run's store — `[event]` log, `[data]`, commits — is left in
/kaggle/working to be read back.

Writes, under scripts/data/kaggle/dil-run/ (git-ignored):

    dataset/   dil-arc3.tar (src/, scripts/_paths.py, scripts/run_game.py),
               the model manifests, dataset-metadata.json
               -> kaggle datasets create -p .../dataset      (first time)
               -> kaggle datasets version -p .../dataset -m "..."
    kernel/    run.ipynb, kernel-metadata.json
               -> kaggle kernels push -p .../kernel

Nothing here submits to the competition.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
REPO = SCRIPTS.parent
OUT = SCRIPTS / "data" / "kaggle" / "dil-run"

OWNER = "plonemraz"
DATASET_SLUG = "dil-arc3-src"
KERNEL_SLUG = "dil-arc3-run"
WHEELHOUSE = "driessmit1/arc3-vllm-h100-wheelhouse-v3"
COMPETITION = "arc-prize-2026-arc-agi-3"
MODELS = {
    "27b": ("michaelpoluektov/qwen3-6-27b-fp8/transformers/default/1",
            "qwen3_6_27b_fp8.manifest.json", "qwen3.6-27b-fp8"),
    "35b-a3b": ("michaelpoluektov/qwen3-6-35b-a3b-fp8/transformers/default/1",
                "qwen3_6_35b_a3b_fp8.manifest.json", "qwen3.6-35b-a3b-fp8"),
}

CELLS = [
    # ── 1 ──
    '''# dil-arc3 — the agent, with the model at the mind
#
# DIL's loop over a live ARC-AGI-3 game; the model thinks, the loop tests what it writes.
# Measurement only: nothing here submits to the competition.
import hashlib, json, os, shutil, subprocess, sys, tarfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W = Path("/kaggle/working")
T0 = time.time()

def find(marker, kind="file"):
    for p in Path("/kaggle/input").rglob(marker):
        return p.parent if kind == "file" else p
    raise FileNotFoundError(marker)

DATA_DIR = find("MANIFEST")
MODEL_DIR = find("model.safetensors.index.json")
WHEELS = find("requirements.lock")
ARC_WHEELS = find("arc_agi_3_wheels", kind="dir")
ENVS = ARC_WHEELS.parent / "environment_files"
for name, path in [("dil-arc3 data", DATA_DIR), ("model", MODEL_DIR), ("vLLM wheels", WHEELS),
                   ("arc wheels", ARC_WHEELS), ("environments", ENVS)]:
    print(f"{name:14}: {path}")
print("games:", sorted(p.name for p in ENVS.iterdir()))
print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout)''',
    # ── 2 ──
    '''# Every model file against the size and hash Hugging Face publishes for the official release.
man = json.loads((DATA_DIR / "MANIFEST").read_text())
print("model manifest:", man["source"])

def check(item):
    rel, e = item
    p = MODEL_DIR / rel
    if not p.exists():
        return rel, "missing"
    if p.stat().st_size != e["size"]:
        return rel, f"size {p.stat().st_size} != {e['size']}"
    if "sha256" in e:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 24), b""):
                h.update(chunk)
        return rel, None if h.hexdigest() == e["sha256"] else "sha256 mismatch"
    body = p.read_bytes()
    blob = hashlib.sha1(b"blob %d\\0" % len(body) + body).hexdigest()
    return rel, None if blob == e["git_blob_sha1"] else "git blob mismatch"

t = time.time()
with ThreadPoolExecutor(8) as pool:
    results = list(pool.map(check, sorted(man["files"].items())))
bad = [(r, why) for r, why in results if why]
print(f"checked {len(results)} files ({man['total_bytes']:,} bytes) in {time.time() - t:.0f}s; problems: {bad}")
assert not bad, bad''',
    # ── 3 ──
    '''# The ARC runtime from the competition's own wheelhouse, into this Python.
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-index", "--no-warn-conflicts",
                "--disable-pip-version-check", "--find-links", str(ARC_WHEELS), "arc-agi"], check=True)
print(subprocess.run([sys.executable, "-c", "import arc_agi, arcengine; print(arc_agi.__file__)"],
                     capture_output=True, text=True).stdout)''',
    # ── 4 ──
    '''# vLLM from the public offline wheelhouse, into its own directory, as Tufa Labs do.
SITE = W / "vllm-site-packages"
SITE.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", str(WHEELS),
                "--requirement", str(WHEELS / "requirements.lock"), "--target", str(SITE),
                "--upgrade", "--ignore-installed", "--only-binary", ":all:", "--no-compile",
                "--disable-pip-version-check", "--no-warn-conflicts", "--quiet"], check=True)
ENV = dict(os.environ, PYTHONPATH=str(SITE), VLLM_NO_USAGE_STATS="1", USE_TF="0",
           TRANSFORMERS_NO_TF="1", TRANSFORMERS_NO_TORCHVISION="1",
           LIBRARY_PATH="/usr/local/nvidia/lib64:" + os.environ.get("LIBRARY_PATH", ""))
print(subprocess.run([sys.executable, "-c", "import vllm, torch; print(vllm.__version__, torch.__version__)"],
                     env=ENV, capture_output=True, text=True).stdout)''',
    # ── 5 ──
    '''# The model's server. Its PID is kept, and only that PID is stopped at the end.
LOG = W / "vllm-server.log"
server = subprocess.Popen(
    [sys.executable, "-m", "vllm.entrypoints.openai.api_server", "--model", str(MODEL_DIR),
     "--served-model-name", "SERVED", "--host", "127.0.0.1", "--port", "8000",
     "--enable-prefix-caching", "--reasoning-parser", "qwen3", "--generation-config", "vllm",
     "--max-model-len", "MAX_MODEL_LEN"],
    env=ENV, stdout=open(LOG, "w"), stderr=subprocess.STDOUT)
BASE = "http://127.0.0.1:8000/v1"
t = time.time()
while time.time() - t < 1200:
    if server.poll() is not None:
        print(LOG.read_text()[-4000:]); raise RuntimeError("vLLM exited")
    try:
        urllib.request.urlopen(BASE + "/models", timeout=5); break
    except Exception:
        time.sleep(5)
print(f"server ready in {time.time() - t:.0f}s")''',
    # ── 6 ──
    '''# dil-arc3 itself, copied where it can write (its scripts keep their data beside them).
REPO = W / "dil-arc3"
shutil.rmtree(REPO, ignore_errors=True)
tar = DATA_DIR / "dil-arc3.tar"
if tar.exists():
    with tarfile.open(tar) as tf:
        tf.extractall(W)
else:  # Kaggle unpacked the archive into the dataset: find() gives scripts/, its parent is the repo
    shutil.copytree(find("run_game.py").parent, REPO)
print(sorted(p.name for p in (REPO / "src").iterdir()))''',
    # ── 7 ──
    '''# The run: the agent plays, the model thinks when the expectation fails.
# Every line goes to run.txt and, as it comes, to this log, so a run in progress
# shows its cycles instead of hours of silence.
RUN = W / "run.txt"
t = time.time()
with open(RUN, "w") as out:
    proc = subprocess.Popen(
        [sys.executable, "-u", str(REPO / "scripts" / "run_game.py"), GAME, str(CYCLES),
         "--endpoint", BASE, "--model", "SERVED", "--max-tokens", str(MAX_TOKENS),
         "--offline-dir", str(ENVS), "--out", str(W / "store")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(REPO))
    for line in proc.stdout:
        out.write(line)
        out.flush()
        if " INFO " not in line:
            print(f"[{time.time() - t:6.0f}s] {line}", end="", flush=True)
    proc.wait()
print(f"run exit {proc.returncode} after {time.time() - t:.0f}s")''',
    # ── 8 ──
    '''print("==== vLLM throughput lines (last 5)")
print("\\n".join([l for l in LOG.read_text().splitlines() if "throughput" in l][-5:]))
print(f"notebook wall time {time.time() - T0:.0f}s")
server.terminate()
server.wait(timeout=60)
shutil.rmtree(SITE, ignore_errors=True)  # the wheels are not output
shutil.rmtree(REPO, ignore_errors=True)
print("server stopped; outputs:", sorted(p.name for p in W.iterdir()))''',
]


def _pack(dest: Path) -> None:
    """src/ and the two scripts the run needs, as the repository lays them out."""
    def keep(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        return None if "__pycache__" in info.name or info.name.endswith(".pyc") else info

    with tarfile.open(dest, "w") as tf:
        tf.add(REPO / "src", arcname="dil-arc3/src", filter=keep)
        for name in ("_paths.py", "run_game.py"):
            tf.add(SCRIPTS / name, arcname=f"dil-arc3/scripts/{name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=sorted(MODELS), default="35b-a3b")
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--cycles", type=int, default=60)
    ap.add_argument("--max-tokens", type=int, default=12288)
    ap.add_argument("--max-model-len", type=int, default=65536)
    a = ap.parse_args()

    dataset, kernel = OUT / "dataset", OUT / "kernel"
    for d in (dataset, kernel):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)

    _pack(dataset / "dil-arc3.tar")
    for _handle, manifest, _served in MODELS.values():
        shutil.copy(HERE / manifest, dataset)
    handle, manifest, served = MODELS[a.model]
    (dataset / "dataset-metadata.json").write_text(json.dumps({
        "title": "dil-arc3 source", "id": f"{OWNER}/{DATASET_SLUG}",
        "licenses": [{"name": "CC0-1.0"}],
    }, indent=1))

    params = (f"GAME = {a.game!r}\nCYCLES = {a.cycles}\nMAX_TOKENS = {a.max_tokens}\n")
    cells = [c.replace('"MANIFEST"', f'"{manifest}"').replace('"SERVED"', f'"{served}"')
             .replace('"MAX_MODEL_LEN"', f'"{a.max_model_len}"') for c in CELLS]
    cells[6] = params + cells[6]
    nb = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                     "language_info": {"name": "python"}},
        # nbformat 4.5 requires an id on every cell; without one Kaggle warns that
        # it will become a hard error.
        "cells": [{"id": f"cell-{i}", "cell_type": "code", "metadata": {}, "execution_count": None,
                   "outputs": [], "source": src} for i, src in enumerate(cells)],
    }
    (kernel / "run.ipynb").write_text(json.dumps(nb, indent=1))
    (kernel / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{OWNER}/{KERNEL_SLUG}", "title": "dil-arc3 run",
        "code_file": "run.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": True, "enable_gpu": True, "enable_tpu": False, "enable_internet": False,
        "machine_shape": "NvidiaRtxPro6000", "keywords": [],
        "dataset_sources": [WHEELHOUSE, f"{OWNER}/{DATASET_SLUG}"],
        "competition_sources": [COMPETITION], "kernel_sources": [], "model_sources": [handle],
    }, indent=1))
    print(f"dataset -> {dataset}\nkernel  -> {kernel}\n"
          f"model {a.model}, game {a.game}, cycles {a.cycles}, max tokens {a.max_tokens}, "
          f"context {a.max_model_len}")


if __name__ == "__main__":
    main()
