"""Build the Kaggle dataset and notebook that run dil-arc3, with the model at the mind.

    python scripts/kaggle/build_dil_run.py [--model 35b-a3b|27b|flash-next] [--game ls20]
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
# The vLLM image built for Qwen3.8-Flash-Next (`vllm/vllm-openai:qwen38-flash-next`),
# its layers on Kaggle; vLLM stock releases up to v0.29 cannot load the model.
FLASH_RUNTIME = "keithtyser/qwen38-flash-next-vllm-nvfp4-runtime-v1"
COMPETITION = "arc-prize-2026-arc-agi-3"
# name: (Kaggle model handle, manifest from Hugging Face, served name, serving)
MODELS = {
    "27b": ("michaelpoluektov/qwen3-6-27b-fp8/transformers/default/1",
            "qwen3_6_27b_fp8.manifest.json", "qwen3.6-27b-fp8", "wheelhouse"),
    "35b-a3b": ("michaelpoluektov/qwen3-6-35b-a3b-fp8/transformers/default/1",
                "qwen3_6_35b_a3b_fp8.manifest.json", "qwen3.6-35b-a3b-fp8", "wheelhouse"),
    # RadixArk/Qwen3.8-Flash-Next-NVFP4 at 7b71922, as copied to Kaggle by keithtyser;
    # checked file by file against Hugging Face before it is served.
    "flash-next": ("keithtyser/qwen3-8-flash-next-nvfp4/PyTorch/radixark-modelopt-fp4/1",
                   "qwen3_8_flash_next_nvfp4.manifest.json", "qwen3.8-flash-next-nvfp4", "flash-next"),
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
SERVING = next(iter(find(n) for n in ("requirements.lock", "runtime-manifest.json")
                    if any(Path("/kaggle/input").rglob(n))))
ARC_WHEELS = find("arc_agi_3_wheels", kind="dir")
ENVS = ARC_WHEELS.parent / "environment_files"
for name, path in [("dil-arc3 data", DATA_DIR), ("model", MODEL_DIR), ("vLLM", SERVING),
                   ("arc wheels", ARC_WHEELS), ("environments", ENVS)]:
    print(f"{name:14}: {path}")
print("games:", sorted(p.name for p in ENVS.iterdir()))
print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout)
print(subprocess.run(["free", "-g"], capture_output=True, text=True).stdout)''',
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
WHEELS = SERVING
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
    '''# The runs. In a scored rerun (KAGGLE_IS_COMPETITION_RERUN) every game the gateway
# offers is played on one scorecard, several at once, and the gateway writes the
# submission; otherwise the chosen games are played offline from the competition's own
# files, the same way, and a placeholder submission lets the commit through.
# Each game is its own agent, with its own store; the model's server is shared.
RERUN = bool(os.environ.get("KAGGLE_IS_COMPETITION_RERUN"))
DEADLINE = T0 + 9 * 3600 - 20 * 60  # nothing starts after, and what runs stops: 20 min kept for the end
cmd = [sys.executable, "-u", str(REPO / "scripts" / "run_competition.py"),
       "--endpoint", BASE, "--model", "SERVED", "--max-tokens", str(MAX_TOKENS),
       "--cycles", str(CYCLES), "--concurrency", str(CONCURRENCY), "--deadline", str(DEADLINE), "--out", str(W)]
if RERUN:
    os.environ.setdefault("ARC_API_KEY", "test-key-123")
    os.environ.setdefault("ARC_BASE_URL", "http://gateway:8001/")
    t = time.time()
    while True:  # the gateway comes up on its own time
        try:
            urllib.request.urlopen(os.environ["ARC_BASE_URL"] + "api/games", timeout=10); break
        except Exception as exc:
            if time.time() - t > 900:
                raise RuntimeError(f"the gateway did not answer in 900s: {exc!r}")
            time.sleep(5)
    print(f"gateway ready in {time.time() - t:.0f}s", flush=True)
    cmd += ["--mode", "competition", "--base-url", os.environ["ARC_BASE_URL"]]
else:
    cmd += ["--mode", "offline", "--offline-dir", str(ENVS), "--games", ",".join(GAMES)]
done = subprocess.run(cmd, cwd=str(REPO), env=dict(os.environ))
print(f"run_competition exit {done.returncode} after {time.time() - T0:.0f}s of notebook", flush=True)
if not RERUN:
    import pandas as pd
    pd.DataFrame([["1_0", "1", True, 1]], columns=["row_id", "game_id", "end_of_game", "score"]) \
        .to_parquet(W / "submission.parquet", index=False)''',
    # ── 8 ──
    '''print("==== vLLM throughput lines (last 5)")
print("\\n".join([l for l in LOG.read_text().splitlines() if "throughput" in l][-5:]))
print(f"notebook wall time {time.time() - T0:.0f}s")
server.terminate()
server.wait(timeout=60)
shutil.rmtree(SITE, ignore_errors=True)  # the runtime is not output
shutil.rmtree(REPO, ignore_errors=True)
print("server stopped; outputs:", sorted(p.name for p in W.iterdir()))''',
]

# For Qwen3.8-Flash-Next, cells 4 and 5 are these. The runtime and the launch follow
# what a public notebook ran on this machine (Tufa Labs' Duck harness, as served by
# keithtyser); the code is this project's own.
FLASH_CELLS = {
    3: '''# vLLM from the image built for this model: each layer checked against the runtime
# manifest, extracted in order, its whiteouts applied.
import re, signal
RT_MANIFEST_SHA256 = "e9453f8d0e9c5eb2e14712e0f8563aaa96752ddc1705f245cac327537502baad"
ROOT = Path("/tmp/dil-vllm-runtime")
SITE = ROOT / "usr/local/lib/python3.12/dist-packages"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()

t = time.time()
assert sha256(SERVING / "runtime-manifest.json") == RT_MANIFEST_SHA256, "not the pinned runtime"
rt = json.loads((SERVING / "runtime-manifest.json").read_text())
shutil.rmtree(ROOT, ignore_errors=True)
ROOT.mkdir(parents=True)
for layer in sorted(rt["selected_layers"], key=lambda r: r["index"]):
    blob = SERVING / layer["file"]
    blob = blob if blob.exists() else SERVING / (layer["file"] + ".blob")
    assert blob.stat().st_size == layer["size"] and sha256(blob) == layer["sha256"], layer["file"]
    subprocess.run(["tar", "-xzf", str(blob), "-C", str(ROOT), "--no-same-owner",
                    "--exclude=*/__pycache__", "--exclude=*.pyc"], check=True)
    for marker in sorted(ROOT.rglob(".wh.*"), key=lambda p: len(p.parts), reverse=True):
        assert marker.name != ".wh..wh..opq", marker
        target = marker.with_name(marker.name[4:])
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
        marker.unlink()
print(f"runtime: {len(rt['selected_layers'])} layers checked and extracted in {time.time() - t:.0f}s")

# The checkpoint keeps its PLE n-gram embedding in FP8 under an NVFP4 config; the
# stock loader picks the FP8 loader only under an FP8 config. One gate, written
# against the stock file's hash, selects it for this checkpoint's PLE and nothing else.
PLE = SITE / "vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py"
PLE_PREFIX = "language_model.model.layers.1.ple.ple_embedding.ngram_embedding"
assert sha256(PLE) == "a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7", "not the stock file"
anchor = '    """Select global-scale FP8 only for quantized PLE checkpoint shards."""\\n'
src = PLE.read_text()
assert src.count(anchor) == 1
PLE.write_text(src.replace(anchor, anchor + (
    "    import os  # dil-arc3: this NVFP4 checkpoint\'s PLE embedding is FP8\\n"
    "    if (os.environ.get(\\"DIL_ARC3_NVFP4_PLE_FP8\\") == \\"1\\"\\n"
    "            and type(quant_config).__name__ == \\"ModelOptNvFp4Config\\"\\n"
    f"            and prefix == {PLE_PREFIX!r}):\\n"
    "        return Qwen3_8FlashNextPLEFp8EmbeddingMethod()\\n")))

def driver_dir():
    """Where the real (non-stub) libcuda.so.1 is: ldconfig's cache, then the usual places."""
    out = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True).stdout
    libs = [Path(l.split("=>", 1)[1].strip()) for l in out.splitlines() if "libcuda.so.1" in l and "=>" in l]
    dirs = [d for d in os.environ.get("LD_LIBRARY_PATH", "").split(":") if d]
    libs += [Path(d) / "libcuda.so.1" for d in [*dirs, "/usr/local/nvidia/lib64", "/usr/lib/x86_64-linux-gnu"]]
    libs = [p.resolve() for p in libs if p.is_file() and "stubs" not in str(p.resolve()).lower()]
    print("libcuda.so.1:", sorted(set(map(str, libs))))
    return max(libs, key=lambda p: p.stat().st_size).parent if libs else None

cuda = ROOT / "usr/local/cuda-13.0"
cache = Path("/tmp/dil-vllm-cache")
libs = [cuda / "targets/x86_64-linux/lib", cuda / "lib64", SITE / "torch/lib",
        *sorted(p for p in (SITE / "nvidia").glob("*/lib") if p.is_dir()),
        driver_dir() or Path("/usr/local/nvidia/lib64"), Path("/usr/local/nvidia/lib64"),
        Path("/usr/lib/x86_64-linux-gnu")]
ENV = {k: v for k, v in os.environ.items() if k != "PYTORCH_ALLOC_CONF"}
ENV.update({
    "PYTHONPATH": f"{SITE / 'nvidia_cutlass_dsl/dsl_packages'}:{SITE}",
    "PATH": f"{cuda / 'bin'}:{ROOT / 'usr/local/bin'}:{os.environ.get('PATH', '')}",
    "LD_LIBRARY_PATH": ":".join(str(p) for p in libs if p.is_dir()),
    "CUDA_HOME": str(cuda), "CUDACXX": str(cuda / "bin/nvcc"), "CUDA_VISIBLE_DEVICES": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID", "TORCH_CUDA_ARCH_LIST": "12.0",
    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:False",
    "VLLM_PLE_CPU_OFFLOAD": "1", "VLLM_PLE_OFFLOAD_READY_TIMEOUT": "1500",
    "VLLM_ENABLE_CUDA_COMPATIBILITY": "0", "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
    "VLLM_NO_USAGE_STATS": "1", "DO_NOT_TRACK": "1", "DIL_ARC3_NVFP4_PLE_FP8": "1",
    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4", "TMPDIR": str(cache / "tmp"),
    "HF_HOME": str(cache / "hf"), "XDG_CACHE_HOME": str(cache), "TRITON_CACHE_DIR": str(cache / "triton"),
    "TORCHINDUCTOR_CACHE_DIR": str(cache / "inductor"), "FLASHINFER_WORKSPACE_BASE": str(cache / "flashinfer"),
})
(cache / "tmp").mkdir(parents=True, exist_ok=True)
probe = subprocess.run([sys.executable, "-c",
    "import vllm, torch\\n"
    "from vllm.model_executor.layers.quantization.modelopt import ModelOptNvFp4Config as C\\n"
    "from vllm.models.qwen3_8_flash_next.nvidia.ple_layer import _get_ple_embedding_quant_method as g\\n"
    "c = C(quant_method=\'NVFP4\', is_checkpoint_nvfp4_serialized=True, exclude_modules=[\'*.ple.*\'], group_size=16)\\n"
    f"print(vllm.__version__, torch.__version__, type(g(c, {PLE_PREFIX!r})).__name__)"],
    env=ENV, capture_output=True, text=True)
print(probe.stdout, probe.stderr[-3000:])
assert probe.stdout.split()[-1] == "Qwen3_8FlashNextPLEFp8EmbeddingMethod", "the PLE gate did not select FP8"''',
    4: '''# The model's server, in its own session. Its PID is kept, and only its group is stopped.
# The PLE embedding stays in host memory (VLLM_PLE_CPU_OFFLOAD); the rest fits the GPU.
# The weights take 81.8 GiB of it, which left 2.29 GiB of KV cache at a 0.92 share, short
# of the 2.37 GiB one 64K request needs (kernel v8). The KV cache is set outright instead,
# at the 5 GiB the public notebook served this model with on this machine.
LOG = W / "vllm-server.log"
server = subprocess.Popen(
    [sys.executable, "-m", "vllm.entrypoints.cli.main", "serve", str(MODEL_DIR),
     "--served-model-name", "SERVED", "--host", "127.0.0.1", "--port", "8000",
     "--load-format", "safetensors", "--dtype", "bfloat16", "--quantization", "modelopt_fp4",
     "--tensor-parallel-size", "1", "--distributed-executor-backend", "mp",
     "--kv-cache-memory-bytes", str(5 * 1024**3), "--max-model-len", "MAX_MODEL_LEN", "--max-num-seqs", "4",
     "--max-num-batched-tokens", "8192", "--enable-chunked-prefill", "--async-scheduling",
     "--max-cudagraph-capture-size", "32", "--no-enable-prefix-caching",
     "--reasoning-parser", "qwen3", "--chat-template", str(MODEL_DIR / "chat_template.jinja"),
     "--speculative-config", \'{"method":"mtp","num_speculative_tokens":3}\',
     "--no-enable-log-requests", "--disable-uvicorn-access-log"],
    env=ENV, stdout=open(LOG, "w"), stderr=subprocess.STDOUT, start_new_session=True)
BASE = "http://127.0.0.1:8000/v1"
t = time.time()
while time.time() - t < 1800:
    if server.poll() is not None:
        print(LOG.read_text()[-6000:]); raise RuntimeError("vLLM exited")
    try:
        urllib.request.urlopen(BASE + "/models", timeout=5); break
    except Exception:
        time.sleep(10)
else:
    print(LOG.read_text()[-6000:]); raise RuntimeError("vLLM not ready in 1800s")
print(f"server ready in {time.time() - t:.0f}s")
print(subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout)
print(subprocess.run(["free", "-g"], capture_output=True, text=True).stdout)''',
}
FLASH_STOP = '''print("==== vLLM throughput lines (last 5)")
print("\\n".join([l for l in LOG.read_text().splitlines() if "throughput" in l][-5:]))
print(f"notebook wall time {time.time() - T0:.0f}s")
os.killpg(server.pid, signal.SIGTERM)  # the group this notebook started, and nothing else
server.wait(timeout=120)
shutil.rmtree(ROOT, ignore_errors=True)  # the runtime is not output
shutil.rmtree(REPO, ignore_errors=True)
print("server stopped; outputs:", sorted(p.name for p in W.iterdir()))'''


def _pack(dest: Path) -> None:
    """src/ and the two scripts the run needs, as the repository lays them out."""
    def keep(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        return None if "__pycache__" in info.name or info.name.endswith(".pyc") else info

    with tarfile.open(dest, "w") as tf:
        tf.add(REPO / "src", arcname="dil-arc3/src", filter=keep)
        for name in ("_paths.py", "run_game.py", "run_competition.py"):
            tf.add(SCRIPTS / name, arcname=f"dil-arc3/scripts/{name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=sorted(MODELS), default="35b-a3b")
    ap.add_argument("--game", default="ls20", help="one game, or several separated by commas, played in turn")
    ap.add_argument("--cycles", type=int, default=60)
    ap.add_argument("--max-tokens", type=int, default=12288)
    ap.add_argument("--max-model-len", type=int, default=65536)
    ap.add_argument("--concurrency", type=int, default=4, help="games played at once, on one model server")
    a = ap.parse_args()

    dataset, kernel = OUT / "dataset", OUT / "kernel"
    for d in (dataset, kernel):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)

    _pack(dataset / "dil-arc3.tar")
    for _handle, manifest, _served, _serving in MODELS.values():
        shutil.copy(HERE / manifest, dataset)
    handle, manifest, served, serving = MODELS[a.model]
    (dataset / "dataset-metadata.json").write_text(json.dumps({
        "title": "dil-arc3 source", "id": f"{OWNER}/{DATASET_SLUG}",
        "licenses": [{"name": "CC0-1.0"}],
    }, indent=1))

    games = [g.strip() for g in a.game.split(",") if g.strip()]
    params = (f"GAMES = {games!r}\nCYCLES = {a.cycles}\nMAX_TOKENS = {a.max_tokens}\n"
              f"CONCURRENCY = {a.concurrency}\n")
    chosen = list(CELLS)
    if serving == "flash-next":
        for i, cell in FLASH_CELLS.items():
            chosen[i] = cell
        chosen[7] = FLASH_STOP
    cells = [c.replace('"MANIFEST"', f'"{manifest}"').replace('"SERVED"', f'"{served}"')
             .replace('"MAX_MODEL_LEN"', f'"{a.max_model_len}"') for c in chosen]
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
        "dataset_sources": [FLASH_RUNTIME if serving == "flash-next" else WHEELHOUSE,
                            f"{OWNER}/{DATASET_SLUG}"],
        "competition_sources": [COMPETITION], "kernel_sources": [], "model_sources": [handle],
    }, indent=1))
    print(f"dataset -> {dataset}\nkernel  -> {kernel}\n"
          f"model {a.model}, game {a.game}, cycles {a.cycles}, max tokens {a.max_tokens}, "
          f"context {a.max_model_len}")


if __name__ == "__main__":
    main()
