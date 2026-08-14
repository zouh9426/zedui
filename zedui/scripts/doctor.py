#!/usr/bin/env python3
"""doctor.py — ZedUI environment health check.

Verifies the full upstream chain zedui's workflow depends on: the five
upstream skills resolve to real installs (matched by frontmatter ``name:``,
case-insensitive, not by directory name, following symlinks), impeccable's
version and key scripts match the tested baseline, UUPM's search.py contract
holds, zedui's own scripts compile, and the project's DESIGN.md (if any) is
in sync with its tokens.css.

Skill resolution candidate order (project-level first, first hit wins):
    <project-root>/.agents/skills/   ~/.agents/skills/
    ~/.kimi-code/skills/             ~/.claude/skills/   ~/.codex/skills/

Every check prints a one-line ✓/✗/⚠ result; the summary drives the exit
code — any critical check failing exits 1. Warnings (impeccable version
drift, UUPM search.py hiccup) never fail.

Pure standard library (stdlib only). Python 3.8+.

Usage:
    doctor.py [--project-root PATH]

    --project-root   project root to health-check (default: current
                     directory). Used for the project-level skill install
                     (.agents/skills/) and for the DESIGN.md / tokens.css
                     sync check.

Exit codes:
    0  all critical checks passed
    1  at least one critical check failed
"""

import argparse
import os
import py_compile
import re
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import uupm_to_design as utd  # noqa: E402  (bridge script in the same scripts/)

TESTED_IMPECCABLE_VERSION = "4.0.4"

# (expected relative path, basename to search for when the path moved)
IMPECCABLE_SCRIPTS = (
    ("scripts/context.mjs", "context.mjs"),
    ("scripts/detector/detect-antipatterns.mjs", "detect-antipatterns.mjs"),
)

ZEDUI_SCRIPTS = ("uupm_to_design.py", "token_lint.py")

SKILL_NAMES = ("ui-ux-pro-max", "design-taste-frontend", "interface-design",
               "impeccable", "zedui")

GENERATED_MARKER_RE = re.compile(r"<!-- zedui:generated:([a-z-]+):(start|end) -->")


# --------------------------------------------------------------------------
# skill resolution
# --------------------------------------------------------------------------

def candidate_dirs(project_root):
    """Skill install candidates, project-level first (see SKILL.md)."""
    home = os.path.expanduser("~")
    return [
        os.path.join(project_root, ".agents", "skills"),
        os.path.join(home, ".agents", "skills"),
        os.path.join(home, ".kimi-code", "skills"),
        os.path.join(home, ".claude", "skills"),
        os.path.join(home, ".codex", "skills"),
    ]


def _read_frontmatter_field(path, field):
    """Read a scalar field from a SKILL.md YAML frontmatter block.

    Matches by field name (case-sensitive key, quoted or bare scalar) and
    ignores everything past the closing ``---``.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = []
            for i, line in enumerate(fh):
                if i > 200:
                    break
                lines.append(line.rstrip("\r\n"))
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    prefix = field + ":"
    for line in lines[1:]:
        s = line.strip()
        if s == "---":
            break
        if s.startswith(prefix):
            val = s[len(prefix):].strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            return val
    return None


def _inode(path):
    try:
        st = os.stat(path, follow_symlinks=True)
        return (st.st_dev, st.st_ino)
    except OSError:
        return None


def _walk_skill_mds(root):
    """Yield SKILL.md paths under root; follows symlinks (skills are often
    installed as symlinks), guards against symlink cycles."""
    visited = set()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        key = _inode(dirpath)
        if key is not None:
            if key in visited:
                dirnames[:] = []
                continue
            visited.add(key)
        if "SKILL.md" in filenames:
            yield os.path.join(dirpath, "SKILL.md")


def resolve_skill(skill, dirs):
    """Return [(candidate_index, candidate_dir, skill_md_path), ...] for a
    skill name matched against frontmatter ``name:`` (case-insensitive)."""
    hits = []
    for idx, cand in enumerate(dirs):
        if not os.path.isdir(cand):
            continue
        for smd in _walk_skill_mds(cand):
            name = _read_frontmatter_field(smd, "name")
            if name is not None and name.strip().lower() == skill.lower():
                hits.append((idx, cand, smd))
    return hits


def _find_basename(root, basename):
    """Search root (following symlinks) for a file with the given basename."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        if basename in filenames:
            return os.path.join(dirpath, basename)
    return None


def _find_tokens_css(project_root):
    """All tokens.css under the project root (skipping .git/node_modules)."""
    found = []
    visited = set()
    for dirpath, dirnames, filenames in os.walk(project_root, followlinks=False):
        key = _inode(dirpath)
        if key is not None:
            if key in visited:
                dirnames[:] = []
                continue
            visited.add(key)
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for f in filenames:
            if f == "tokens.css":
                found.append(os.path.join(dirpath, f))
    return found


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="doctor.py",
        description="ZedUI environment health check (upstream skills + "
                    "project DESIGN.md sync). Stdlib only.",
    )
    parser.add_argument("--project-root", default=None, metavar="PATH",
                        help="project root to check (default: current directory)")
    args = parser.parse_args(argv)
    project_root = os.path.abspath(args.project_root or os.getcwd())

    critical_fail = False
    results = []  # (section, status) with status in ok/fail/warn/skip

    def emit(section, status, msg):
        mark = {"ok": "\u2713", "fail": "\u2717",
                "warn": "\u26a0", "skip": "-"}[status]
        print("  %s %s" % (mark, msg))
        results.append((section, status))

    print("zedui doctor - environment health check")
    print("project root: %s" % project_root)

    # ---- [1/6] skill HOME resolution -------------------------------------
    print("")
    print("[1/6] Skill HOME resolution")
    dirs = candidate_dirs(project_root)
    homes = {}
    for skill in SKILL_NAMES:
        hits = resolve_skill(skill, dirs)
        if not hits:
            emit(1, "fail",
                 "%s not found in any candidate skill directory "
                 "(install per zedui README/SETUP)" % skill)
            critical_fail = True
            continue
        idx, cand, smd = hits[0]
        homes[skill] = os.path.dirname(smd)
        emit(1, "ok", "%s -> %s" % (skill, homes[skill]))
        for _, dup_cand, dup_smd in hits[1:]:
            emit(1, "warn", "%s also installed at: %s" % (skill, dup_smd))

    # ---- [2/6] impeccable version -----------------------------------------
    print("")
    print("[2/6] impeccable version")
    imp = homes.get("impeccable")
    if imp is None:
        emit(2, "warn", "impeccable not resolved - version check skipped")
    else:
        version = _read_frontmatter_field(os.path.join(imp, "SKILL.md"), "version")
        if version is None:
            emit(2, "warn", "impeccable SKILL.md has no version field")
        elif version.strip() == TESTED_IMPECCABLE_VERSION:
            emit(2, "ok", "impeccable version %s matches the tested baseline"
                 % version.strip())
        else:
            emit(2, "warn",
                 "impeccable version %s differs from the tested %s - "
                 "verify upstream drift" % (version.strip(), TESTED_IMPECCABLE_VERSION))

    # ---- [3/6] impeccable scripts ------------------------------------------
    print("")
    print("[3/6] impeccable scripts")
    if imp is None:
        emit(3, "warn", "impeccable not resolved - script check skipped")
    else:
        for rel, base in IMPECCABLE_SCRIPTS:
            p = os.path.join(imp, rel)
            if os.path.isfile(p):
                emit(3, "ok", rel)
                continue
            alt = _find_basename(imp, base)
            if alt:
                emit(3, "ok", "%s not at the expected path; found at %s" % (rel, alt))
            else:
                emit(3, "fail",
                     "%s missing and not found anywhere under %s" % (rel, imp))
                critical_fail = True

    # ---- [4/6] UUPM search.py contract --------------------------------------
    print("")
    print("[4/6] UUPM search.py contract")
    uupm = homes.get("ui-ux-pro-max")
    if uupm is None:
        emit(4, "warn", "ui-ux-pro-max not resolved - search.py check skipped")
    else:
        search_py = os.path.join(uupm, "scripts", "search.py")
        if not os.path.isfile(search_py):
            emit(4, "warn", "%s missing (optional check)" % search_py)
        else:
            try:
                proc = subprocess.run([sys.executable, search_py, "--help"],
                                      capture_output=True, timeout=30)
            except (OSError, subprocess.TimeoutExpired) as e:
                emit(4, "warn",
                     "%s exists but `--help` could not run: %s (optional check)"
                     % (search_py, e))
            else:
                if proc.returncode == 0:
                    emit(4, "ok", "%s exists and `--help` runs" % search_py)
                else:
                    emit(4, "warn",
                         "%s exists but `--help` failed (exit %d) - optional check"
                         % (search_py, proc.returncode))

    # ---- [5/6] zedui scripts -------------------------------------------------
    print("")
    print("[5/6] zedui scripts")
    zedui = homes.get("zedui")
    if zedui is None:
        scripts_dir = _HERE
        emit(5, "warn",
             "zedui not resolved in skill dirs; checking %s (doctor.py's own "
             "location)" % _HERE)
    else:
        scripts_dir = os.path.join(zedui, "scripts")
    for script in ZEDUI_SCRIPTS:
        p = os.path.join(scripts_dir, script)
        if not os.path.isfile(p):
            emit(5, "fail", "%s missing" % p)
            critical_fail = True
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="zedui-doctor-") as td:
                cfile = os.path.join(td, os.path.basename(p) + "c")
                py_compile.compile(p, cfile=cfile, doraise=True)
            emit(5, "ok", "%s compiles" % p)
        except (py_compile.PyCompileError, OSError) as e:
            emit(5, "fail", "%s does not compile: %s" % (p, e))
            critical_fail = True

    # ---- [6/6] project DESIGN.md sync -----------------------------------------
    print("")
    print("[6/6] Project DESIGN.md")
    design_path = os.path.join(project_root, "DESIGN.md")
    if not os.path.isfile(design_path):
        emit(6, "skip", "no DESIGN.md in project root - project check skipped")
    else:
        try:
            with open(design_path, "r", encoding="utf-8") as fh:
                design_text = fh.read()
        except OSError as e:
            emit(6, "fail", "cannot read %s: %s" % (design_path, e))
            critical_fail = True
        else:
            try:
                fm = utd.parse_design_frontmatter(design_text)
                emit(6, "ok", "frontmatter parses as zedui-design-schema-v1")
            except ValueError as e:
                fm = None
                emit(6, "fail", "frontmatter does not parse: %s" % e)
                critical_fail = True

            markers = GENERATED_MARKER_RE.findall(design_text)
            starts = sorted(name for name, kind in markers if kind == "start")
            ends = [name for name, kind in markers if kind == "end"]
            if len(starts) == 4 and len(ends) == 4:
                emit(6, "ok", "body has 4 pairs of zedui:generated markers (%s)"
                     % ", ".join(starts))
            else:
                emit(6, "fail", "expected 4 pairs of zedui:generated markers, "
                     "found %d start / %d end" % (len(starts), len(ends)))
                critical_fail = True

            tokens_list = _find_tokens_css(project_root)
            if not tokens_list:
                emit(6, "warn", "no tokens.css found under the project root - "
                     "token layer not generated (run uupm_to_design.py --tokens-css)")
            else:
                for tf in tokens_list:
                    if fm is None:
                        emit(6, "fail", "%s: cannot regenerate without a "
                             "parseable frontmatter" % tf)
                        critical_fail = True
                        continue
                    try:
                        typo = fm["typography"]
                        css = utd.build_tokens_css(
                            fm["colors"],
                            (typo.get("heading") or {}).get("fontFamily"),
                            (typo.get("body") or {}).get("fontFamily"),
                            typo["scale"],
                            fm["rounded"],
                            fm["spacing"],
                            design_path,
                        )
                    except (KeyError, ValueError, TypeError) as e:
                        emit(6, "fail", "%s: cannot regenerate tokens from "
                             "DESIGN.md: %s" % (tf, e))
                        critical_fail = True
                        continue
                    try:
                        with open(tf, "r", encoding="utf-8") as fh:
                            existing = fh.read()
                    except OSError as e:
                        emit(6, "fail", "%s: cannot read existing tokens.css: %s"
                             % (tf, e))
                        critical_fail = True
                        continue
                    if existing == css:
                        emit(6, "ok", "%s in sync with DESIGN.md" % tf)
                    else:
                        emit(6, "fail", "%s is out of sync with DESIGN.md - "
                             "re-run uupm_to_design.py --from-design DESIGN.md "
                             "--tokens-css %s" % (tf, tf))
                        critical_fail = True

    # ---- summary ---------------------------------------------------------------
    print("")
    ok_n = sum(1 for _, s in results if s == "ok")
    fail_n = sum(1 for _, s in results if s == "fail")
    warn_n = sum(1 for _, s in results if s == "warn")
    skip_n = sum(1 for _, s in results if s == "skip")
    print("Summary: %d ok, %d failed, %d warnings, %d skipped"
          % (ok_n, fail_n, warn_n, skip_n))
    if critical_fail:
        print("One or more critical checks failed.")
        return 1
    print("All critical checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
