"""Build the Kaggle dataset and notebook that run the world-model probe on a GPU.

    python scripts/kaggle/build_probe_run.py [--model 27b|35b-a3b] [--rounds 3]
        [--runs-per-mode 2] [--max-tokens 16384] [--max-model-len N]

Writes two folders under scripts/data/kaggle/ (git-ignored), ready for the CLI:

    dataset/   wm_probe.py, transitions.json, the model manifest, dataset-metadata.json
               -> kaggle datasets create -p scripts/data/kaggle/dataset      (first time)
               -> kaggle datasets version -p scripts/data/kaggle/dataset -m "..."
    kernel/    probe.ipynb, kernel-metadata.json
               -> kaggle kernels push -p scripts/data/kaggle/kernel

The notebook follows the one way of serving an open model offline on this
competition's hardware that a public notebook has shown to work (Tufa Labs'
Milestone-1 notebook): vLLM installed from a public offline wheelhouse, on an RTX
Pro 6000, internet off. It serves an official Qwen FP8 quantisation mirrored on
Kaggle Models — Qwen3.6-27B-FP8 or Qwen3.6-35B-A3B-FP8 — and before using it
checks every file against the sizes and hashes Hugging Face publishes (the
matching *.manifest.json beside this script).
It then runs several probes at once against the server, with and without
thinking, and writes each run's log to /kaggle/working.

Nothing here submits to the competition.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
OUT = SCRIPTS / "data" / "kaggle"

OWNER = "plonemraz"
DATASET_SLUG = "dil-arc3-probe"
KERNEL_SLUG = "dil-arc3-world-model-probe"
PROMPT_ALLOWANCE = 24576
WHEELHOUSE = "driessmit1/arc3-vllm-h100-wheelhouse-v3"
# Official Qwen FP8 releases, mirrored on Kaggle Models by a third party; each is
# checked file by file against Hugging Face before it is used.
MODELS = {
    "27b": ("michaelpoluektov/qwen3-6-27b-fp8/transformers/default/1",
            "qwen3_6_27b_fp8.manifest.json", "qwen3.6-27b-fp8"),
    "35b-a3b": ("michaelpoluektov/qwen3-6-35b-a3b-fp8/transformers/default/1",
                "qwen3_6_35b_a3b_fp8.manifest.json", "qwen3.6-35b-a3b-fp8"),
}

CELLS = [
    # ── 1 ──
    '''# dil-arc3 world-model probe
#
# Can an open model, served offline, write an executable world model of an ARC-AGI-3 game?
# Measurement only: nothing here submits to the competition.
import hashlib, json, os, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W = Path("/kaggle/working")
T0 = time.time()

def find(marker):
    for p in Path("/kaggle/input").rglob(marker):
        return p.parent
    raise FileNotFoundError(marker)

DATA_DIR = find("wm_probe.py")
MODEL_DIR = find("model.safetensors.index.json")
WHEELS = find("requirements.lock")
print("probe data :", DATA_DIR)
print("model      :", MODEL_DIR)
print("wheelhouse :", WHEELS)
print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout)''',
    # ── 2 ──
    '''# Every model file against the size and hash Hugging Face publishes for the official release.
# A third party's mirror is used only if it is byte-for-byte the official release.
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
    '''# vLLM from the public offline wheelhouse, installed into /kaggle/working as Tufa Labs do.
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
    # ── 4 ──
    '''# The server. Its PID is kept, and only that PID is stopped at the end.
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
    # ── 5 ──
    '''# The probes, several at once: vLLM batches concurrent requests.
RUNS = []
for mode in ("nothink", "think"):
    for i in range(RUNS_PER_MODE):
        tag = f"{mode}_{i}"
        cmd = [sys.executable, str(DATA_DIR / "wm_probe.py"), "--game", "ls20",
               "--data", str(DATA_DIR / "transitions.json"), "--endpoint", BASE,
               "--model", "SERVED", "--rounds", str(ROUNDS), "--max-tokens", str(MAX_TOKENS),
               "--out", str(W / f"probe_{tag}.json")] + (["--no-think"] if mode == "nothink" else [])
        RUNS.append((tag, subprocess.Popen(cmd, stdout=open(W / f"probe_{tag}.txt", "w"),
                                           stderr=subprocess.STDOUT)))
t = time.time()
for tag, p in RUNS:
    p.wait()
    print(f"{tag}: exit {p.returncode} after {time.time() - t:.0f}s", flush=True)''',
    # ── 6 ──
    '''# What each run found, and what it cost.
for tag, _ in RUNS:
    print(f"==== {tag}")
    print((W / f"probe_{tag}.txt").read_text()[-1500:])
print("==== vLLM throughput lines (last 5)")
print("\\n".join([l for l in LOG.read_text().splitlines() if "throughput" in l][-5:]))
print(f"notebook wall time {time.time() - T0:.0f}s")''',
    # ── 7 ──
    '''server.terminate()
server.wait(timeout=60)
print("server stopped")''',
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=sorted(MODELS), default="27b")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--runs-per-mode", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=16384)
    # A request is refused unless prompt + max_tokens fits the context. The probe's
    # prompts have reached 20,537 tokens; run 2 lost a run by one token at 65,536.
    ap.add_argument("--max-model-len", type=int, default=None,
                    help=f"default: max(65536, max tokens + {PROMPT_ALLOWANCE})")
    a = ap.parse_args()
    max_model_len = a.max_model_len or max(65536, a.max_tokens + PROMPT_ALLOWANCE)

    dataset, kernel = OUT / "dataset", OUT / "kernel"
    for d in (dataset, kernel):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)

    shutil.copy(SCRIPTS / "wm_probe.py", dataset)
    shutil.copy(SCRIPTS / "data" / "transitions.json", dataset)
    for _handle, manifest, _served in MODELS.values():
        shutil.copy(HERE / manifest, dataset)
    handle, manifest, served = MODELS[a.model]
    (dataset / "dataset-metadata.json").write_text(json.dumps({
        "title": "dil-arc3 probe",
        "id": f"{OWNER}/{DATASET_SLUG}",
        "licenses": [{"name": "CC0-1.0"}],
    }, indent=1))

    params = (f"ROUNDS = {a.rounds}\nRUNS_PER_MODE = {a.runs_per_mode}\n"
              f"MAX_TOKENS = {a.max_tokens}\n")
    cells = [c.replace('"MANIFEST"', f'"{manifest}"').replace('"SERVED"', f'"{served}"')
             .replace('"MAX_MODEL_LEN"', f'"{max_model_len}"') for c in CELLS]
    cells[4] = params + cells[4]
    nb = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                     "language_info": {"name": "python"}},
        "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                   "source": src} for src in cells],
    }
    (kernel / "probe.ipynb").write_text(json.dumps(nb, indent=1))
    (kernel / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{OWNER}/{KERNEL_SLUG}",
        "title": "dil-arc3 world-model probe",
        "code_file": "probe.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": False,
        "machine_shape": "NvidiaRtxPro6000",
        "keywords": [],
        "dataset_sources": [WHEELHOUSE, f"{OWNER}/{DATASET_SLUG}"],
        "competition_sources": ["arc-prize-2026-arc-agi-3"],
        "kernel_sources": [],
        "model_sources": [handle],
    }, indent=1))
    print(f"dataset -> {dataset}\nkernel  -> {kernel}\n"
          f"model {a.model} ({handle}), rounds {a.rounds}, runs per mode {a.runs_per_mode}, "
          f"max tokens {a.max_tokens}, context {max_model_len}")


if __name__ == "__main__":
    main()
