"""Write a model manifest from what Hugging Face publishes, to check a Kaggle copy against.

    python scripts/kaggle/make_manifest.py <hf-repo> <revision> <kaggle-model-handle> <out.json>

Every file of the repository at that revision, with its size and the hash Hugging
Face publishes for it: sha256 for LFS files (the weights), the git blob sha1 for
the rest. The notebook checks the mounted copy against it, file by file, before
the model is served. A Kaggle copy made by someone else is trusted only as far as
it matches.
"""
from __future__ import annotations

import json
import sys
import urllib.request


def tree(repo: str, revision: str) -> list[dict]:
    url = f"https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true&expand=true"
    rows: list[dict] = []
    while url:
        with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 — the public Hub API
            rows.extend(json.loads(r.read()))
            link = r.headers.get("Link") or ""
        url = next((part.split(";")[0].strip()[1:-1] for part in link.split(",") if 'rel="next"' in part), "")
    return rows


def main() -> None:
    repo, revision, handle, out = sys.argv[1:5]
    files = {}
    for row in tree(repo, revision):
        if row.get("type") != "file":
            continue
        lfs = row.get("lfs")
        files[row["path"]] = ({"sha256": lfs["oid"], "size": lfs["size"]} if lfs
                              else {"git_blob_sha1": row["oid"], "size": row["size"]})
    manifest = {
        "kaggle_model": handle,
        "note": "sha256 for LFS files (the weights); git blob sha1 for the small files, as Hugging Face publishes them.",
        "source": f"https://huggingface.co/{repo}",
        "revision": revision,
        "total_bytes": sum(f["size"] for f in files.values()),
        "files": dict(sorted(files.items())),
    }
    with open(out, "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"{len(files)} files, {manifest['total_bytes']:,} bytes -> {out}")


if __name__ == "__main__":
    main()
