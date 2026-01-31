#!/usr/bin/env python3
"""Copier‑Task:
1. Adjusts *.copier‑answers.yml* to include a skip list with all globs
   of the disabled features.
2. Deletes any associated files/directories only if
   git confirms that none of the files are versioned (so that they may be
   created by copier before running this script1).

Call:  python3 update_feature_skips.py <project_root>
"""

import sys, subprocess, shutil, yaml, pathlib, os, time

project_root = pathlib.Path(sys.argv[1]).resolve()
feature_file  = pathlib.Path(sys.argv[2]).resolve()
answers_file  = project_root / ".copier-answers.yml"

DEL_FILE_MAX_AGE = time.time() - 150 # max age of files to be deleted

def git_tracked(path: pathlib.Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0

def dir_has_tracked(d: pathlib.Path) -> bool:
    return any(git_tracked(p) for p in d.rglob("*") if p.is_file())

def safe_delete(path: pathlib.Path):
    if not path.exists():
        return
    if path.stat().st_mtime < DEL_FILE_MAX_AGE:
        print(f"[skip] {path} is too old (and might have been created by user - instead of copier), skipping deletion")
        return
    if path.is_dir() and dir_has_tracked(path):
        print(f"[skip] {path}/ contains tracked files")
        return
    if path.is_file() and git_tracked(path):
        print(f"[skip] {path} is tracked in git")
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        print(f"[del]  {path}/")
    else:
        path.unlink()
        print(f"[del]  {path}")

# ----------------- load file contents ---------------------
with feature_file.open() as f:
    feature_globs = yaml.safe_load(f) or {}

with answers_file.open() as f:
    answers = yaml.safe_load(f) or {}

skip = set(answers.get("skip", []))

# ----------------- Check and delete ----------------
for feat, globs in feature_globs.items():
    active = answers.get(f"feature_{feat}", False)
    if active:
        continue                      # keep feature
    for pattern in globs:
        skip.add('/' + pattern)             # skip entirely in the future
        for match in project_root.glob(pattern):
            safe_delete(match)        # remove untracked

answers["skip"] = sorted(skip)
with answers_file.open("w") as f:
    yaml.safe_dump(answers, f, sort_keys=False)

print("\n[task] Updated skip list.")
