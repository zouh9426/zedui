#!/usr/bin/env python3
"""doctor.py — ZedUI environment health check.

Verifies the full upstream chain zedui's workflow depends on: the five
upstream skills resolve to real installs (matched by frontmatter ``name:``,
case-insensitive, not by directory name, following symlinks), impeccable's
version and detection scripts hold against the tested baseline, UUPM's
search.py --design-system --json output is probed for real against the SAME
contract the bridge enforces, zedui's own scripts compile, and the project's
DESIGN.md (if any) is in sync with its tokens.css AND its body generated
blocks (derived views of the frontmatter).

This is a full-chain *installation* health check: it is deliberately stricter
than the runtime's lazy dependency resolution (SKILL.md lets a session
continue when a skill the current task never routes to is missing). doctor
reports the whole chain so gaps surface before they matter. All checks run
against the LOCALLY INSTALLED copies — an offline probe cannot know whether
public upstream has moved; version differences are reported against the
tested baseline in COMPATIBILITY.md, never as "upstream drift".

Skill resolution: callers that already know which copy their host actually
loads (the orchestrator's environment-probing step) SHOULD pass those
authoritative paths explicitly::

    doctor.py --skill-home impeccable=/path/to/impeccable ...

Explicit paths win over auto-discovery and are validated fail-closed (must
exist, be a directory, contain a SKILL.md whose frontmatter ``name:``
matches; a bad explicit path is a critical failure, never a silent fallback).
Auto-discovery is a convenience fallback only — it does NOT claim to
replicate every host's loader precedence; when several installs exist it
reports which copy it selected and says so.

Auto-discovery candidate order (project-level first, first hit wins):
    <project-root>/.agents/skills/     <project-root>/.kimi-code/skills/
    <project-root>/.claude/skills/     ~/.agents/skills/
    ~/.kimi-code/skills/               ~/.claude/skills/   ~/.codex/skills/

Every check prints a one-line ✓/✗/⚠ result; the summary drives the exit
code — any critical check failing exits 1. Warnings (installed impeccable
version differing from the tested baseline, a UUPM search.py found at a
drifted fallback path, a missing DESIGN.md) never fail; a UUPM search.py
that is missing entirely, ambiguous across multiple candidates, or fails the
shared bridge contract probe is a critical failure.

Pure standard library (stdlib only). Python 3.8+.

Usage:
    doctor.py [--project-root PATH] [--skill-home SKILL=PATH ...]

    --project-root   project root to health-check (default: current
                     directory). Used for the project-level skill installs
                     (.agents/.kimi-code/.claude under it) and for the
                     DESIGN.md / tokens.css sync check.
    --skill-home     authoritative install path for one skill, e.g.
                     ``--skill-home impeccable=/path/to/impeccable``.
                     Repeatable; any subset of the five skills may be given.
                     Explicit paths are validated fail-closed and take
                     precedence over auto-discovery; skills without an
                     explicit path fall back to auto-discovery.

Exit codes:
    0  all critical checks passed
    1  at least one critical check failed
    2  usage error (e.g. malformed --skill-home)
"""

import argparse
import json
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
)

# Detector entry preference: scripts/detect.mjs is the current public facade;
# scripts/detector/detect-antipatterns.mjs is the compat fallback; last resort
# is a basename search across $IMP_HOME (different versions move the file).
DETECTOR_PREFERRED = (
    "scripts/detect.mjs",
    "scripts/detector/detect-antipatterns.mjs",
)

# Minimal real probe of UUPM's search.py --design-system --json contract.
UUPM_PROBE_ARGS = (
    "contract probe", "--design-system", "-p", "DoctorProbe",
    "--json", "--variance", "3", "--motion", "4", "--density", "5",
)
UUPM_PROBE_TIMEOUT = 30

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
        os.path.join(project_root, ".kimi-code", "skills"),
        os.path.join(project_root, ".claude", "skills"),
        os.path.join(home, ".agents", "skills"),
        os.path.join(home, ".kimi-code", "skills"),
        os.path.join(home, ".claude", "skills"),
        os.path.join(home, ".codex", "skills"),
    ]


def parse_skill_homes(pairs):
    """Parse repeated --skill-home SKILL=PATH values into {skill: path}.

    Raises ValueError on a malformed pair or an unknown skill name (the
    caller turns that into a usage error, exit 2).
    """
    homes = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError("malformed --skill-home %r (expected SKILL=PATH)" % pair)
        skill, path = pair.split("=", 1)
        skill = skill.strip().lower()
        path = path.strip()
        if skill not in SKILL_NAMES:
            raise ValueError("unknown skill in --skill-home: %r (known: %s)"
                             % (skill, ", ".join(SKILL_NAMES)))
        if not path:
            raise ValueError("empty path in --skill-home %r" % pair)
        homes[skill] = path
    return homes


def validate_explicit_home(skill, path):
    """Validate an explicit --skill-home path. Returns an error string, or
    None when the path is a usable authoritative HOME for ``skill``.

    Fail-closed by design: an explicit path is the caller's claim that the
    host loads THIS copy — silently falling back to another copy would
    re-create the false-green this flag exists to prevent.
    """
    if not os.path.exists(path):
        return "explicit path does not exist: %s" % path
    if not os.path.isdir(path):
        return "explicit path is not a directory: %s" % path
    smd = os.path.join(path, "SKILL.md")
    if not os.path.isfile(smd):
        return "no SKILL.md in explicit path: %s" % path
    name = _read_frontmatter_field(smd, "name")
    if name is None or name.strip().lower() != skill.lower():
        return ("SKILL.md name mismatch in %s: expected %r, found %r"
                % (smd, skill, name))
    return None


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


def _resolve_detector(imp):
    """Locate impeccable's detection entry: preferred -> compat fallback ->
    basename search within $IMP_HOME. Returns (path, note) or (None, None)."""
    for rel in DETECTOR_PREFERRED:
        p = os.path.join(imp, rel)
        if os.path.isfile(p):
            if rel == "scripts/detect.mjs":
                return p, "scripts/detect.mjs (public facade)"
            return p, "scripts/detector/detect-antipatterns.mjs (compat fallback)"
    alt = _find_basename(imp, "detect-antipatterns.mjs")
    if alt:
        return alt, "detect-antipatterns.mjs found at %s (searched $IMP_HOME)" % alt
    return None, None


def _find_all_basenames(root, basename):
    """All files with the given basename under root (follows symlinks,
    guards against symlink cycles)."""
    found = []
    visited = set()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        key = _inode(dirpath)
        if key is not None:
            if key in visited:
                dirnames[:] = []
                continue
            visited.add(key)
        if basename in filenames:
            found.append(os.path.join(dirpath, basename))
    return sorted(found)


def _resolve_search_py(uupm):
    """Locate UUPM's search.py. The standard ``scripts/search.py`` wins; on a
    miss, search $UUPM_HOME for a fallback (upstream may have moved the file).

    Returns (path, status, detail) with status one of:
    ``standard``  — found at the expected path;
    ``fallback``  — exactly one candidate elsewhere (detail = its path);
    ``ambiguous`` — multiple candidates, no reliable way to pick the entry
                    (detail = comma-joined candidates);
    ``missing``   — no search.py anywhere under $UUPM_HOME.
    """
    std = os.path.join(uupm, "scripts", "search.py")
    if os.path.isfile(std):
        return std, "standard", None
    cands = _find_all_basenames(uupm, "search.py")
    if len(cands) == 1:
        return cands[0], "fallback", cands[0]
    if len(cands) > 1:
        return None, "ambiguous", ", ".join(cands)
    return None, "missing", None


def _probe_uupm_contract(search_py):
    """Run a minimal real probe of search.py --design-system --json.

    Runs with cwd in a throwaway temp dir so nothing lands in the user's repo.
    Returns (True, len(colors)) on success, or (False, reason) on failure
    (timeout / non-zero exit / invalid JSON / missing contract fields).
    """
    try:
        with tempfile.TemporaryDirectory(prefix="zedui-uupm-probe-") as td:
            proc = subprocess.run(
                [sys.executable, search_py] + list(UUPM_PROBE_ARGS),
                capture_output=True, timeout=UUPM_PROBE_TIMEOUT,
                cwd=td, text=True)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, "probe could not run: %s" % e
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        detail = detail[0][:160] if detail else "no stderr"
        return False, "probe exited %d (%s)" % (proc.returncode, detail)
    try:
        data = json.loads(proc.stdout or "{}")
    except ValueError as e:
        return False, "probe output is not valid JSON: %s" % e
    if not isinstance(data, dict) or not isinstance(data.get("design_system"), dict):
        return False, "probe JSON lacks an outer 'design_system' object"
    ds = data["design_system"]
    # Share the bridge's schema (single source: utd.COLOR_ROLES) at the KEY
    # level: a required role whose KEY is absent (e.g. cta on older copies)
    # fails the probe exactly where the bridge would fail closed. Empty-string
    # VALUES are data, not schema: UUPM legitimately leaves palette slots ''
    # on a knowledge-base miss (Phase 0.3 confirmation fills them), so they
    # are reported but do not fail the probe.
    colors = ds.get("colors")
    if not isinstance(colors, dict) or not colors:
        return False, "design_system.colors is missing or empty"
    missing = [r for r in utd.COLOR_ROLES if r not in colors]
    if missing:
        return False, ("design_system.colors lacks required role key(s) %s "
                       "(shared bridge contract, utd.COLOR_ROLES)" % ", ".join(missing))
    typo = ds.get("typography")
    if not isinstance(typo, dict) or not str(typo.get("heading") or "").strip() \
            or not str(typo.get("body") or "").strip():
        return False, "design_system.typography is missing heading/body"
    if "spacing_scale" not in ds:
        return False, "design_system.spacing_scale is missing"
    if "dials" not in ds:
        return False, "design_system.dials is missing"
    empty = [r for r in utd.COLOR_ROLES if not str(colors.get(r) or "").strip()]
    note = ""
    if empty:
        note = " (%d role(s) emitted empty — normal on a knowledge-base miss; " \
               "Phase 0.3 fills them)" % len(empty)
    return True, "%d keys%s" % (len(colors), note)


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
    parser.add_argument("--skill-home", action="append", default=[],
                        metavar="SKILL=PATH", dest="skill_home",
                        help="authoritative install path for one skill "
                             "(repeatable); explicit paths are validated "
                             "fail-closed and override auto-discovery")
    args = parser.parse_args(argv)
    project_root = os.path.abspath(args.project_root or os.getcwd())
    try:
        explicit_homes = parse_skill_homes(args.skill_home)
    except ValueError as e:
        parser.error(str(e))  # usage error, exit 2

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
        if skill in explicit_homes:
            path = explicit_homes[skill]
            err = validate_explicit_home(skill, path)
            if err is not None:
                emit(1, "fail", "%s: %s (explicit --skill-home is fail-closed; "
                     "no fallback to auto-discovery)" % (skill, err))
                critical_fail = True
                continue
            homes[skill] = path
            emit(1, "ok", "%s -> %s [explicit]" % (skill, path))
            continue
        hits = resolve_skill(skill, dirs)
        if not hits:
            emit(1, "fail",
                 "%s not found in any candidate skill directory "
                 "(install per zedui README/SETUP)" % skill)
            critical_fail = True
            continue
        idx, cand, smd = hits[0]
        homes[skill] = os.path.dirname(smd)
        emit(1, "ok", "%s -> %s [auto-discovered]" % (skill, homes[skill]))
        for _, dup_cand, dup_smd in hits[1:]:
            emit(1, "warn",
                 "%s also installed at: %s — auto-discovery selected the first "
                 "hit; host-specific precedence may differ. Pass "
                 "--skill-home %s=<path> to validate the copy your host "
                 "actually loads." % (skill, dup_smd, skill))

    # ---- [2/6] impeccable version -----------------------------------------
    print("")
    print("[2/6] impeccable version")
    imp = homes.get("impeccable")
    imp_version = None
    imp_contract = "unknown"
    emit(2, "ok", "tested baseline: %s" % TESTED_IMPECCABLE_VERSION)
    if imp is None:
        emit(2, "warn", "impeccable not resolved - installed version unknown")
    else:
        version = _read_frontmatter_field(os.path.join(imp, "SKILL.md"), "version")
        if version is None:
            emit(2, "warn",
                 "installed version: unknown (SKILL.md has no version field)")
        elif version.strip() == TESTED_IMPECCABLE_VERSION:
            imp_version = version.strip()
            imp_contract = "compatible"
            emit(2, "ok", "installed version: %s matches the tested baseline"
                 % version.strip())
        else:
            imp_version = version.strip()
            emit(2, "warn",
                 "installed version: %s differs from the tested %s - review "
                 "COMPATIBILITY.md before relying on it" % (version.strip(), TESTED_IMPECCABLE_VERSION))
        emit(2, "ok" if imp_contract == "compatible" else "warn",
             "contract: %s" % imp_contract)

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
        det, det_note = _resolve_detector(imp)
        if det is None:
            emit(3, "fail",
                 "detector entry missing - no scripts/detect.mjs, no "
                 "scripts/detector/detect-antipatterns.mjs, and no "
                 "detect-antipatterns.mjs anywhere under %s" % imp)
            critical_fail = True
        else:
            emit(3, "ok", "detector entry: %s" % det_note)

    # ---- [4/6] UUPM search.py contract --------------------------------------
    print("")
    print("[4/6] UUPM search.py contract")
    uupm = homes.get("ui-ux-pro-max")
    if uupm is None:
        emit(4, "warn", "ui-ux-pro-max not resolved - search.py probe skipped")
    else:
        search_py, search_status, search_detail = _resolve_search_py(uupm)
        if search_status == "missing":
            emit(4, "fail",
                 "scripts/search.py missing and no search.py found anywhere "
                 "under %s - incomplete ui-ux-pro-max install: ZedUI Phase 0 "
                 "requires search.py (reinstall per zedui README/SETUP)" % uupm)
            critical_fail = True
        elif search_status == "ambiguous":
            emit(4, "fail",
                 "scripts/search.py missing and multiple search.py candidates "
                 "found under %s (%s) - cannot determine the real entry; "
                 "refusing to guess" % (uupm, search_detail))
            critical_fail = True
        else:
            if search_status == "fallback":
                emit(4, "warn",
                     "scripts/search.py not at the expected path; using %s "
                     "(upstream path drift)" % search_detail)
            ok, res = _probe_uupm_contract(search_py)
            if ok:
                emit(4, "ok",
                     "UUPM contract probe passed: design_system.colors has %s" % res)
            else:
                emit(4, "fail",
                     "UUPM contract probe failed: %s - uupm_to_design.py "
                     "cannot trust this search.py" % res)
                critical_fail = True

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

            # Rebuild the marked body blocks from the frontmatter (the SSOT)
            # and compare byte-for-byte: a hand-edited generated table must be
            # caught even though tokens.css below is still in sync.
            if fm is not None and len(starts) == 4 and len(ends) == 4:
                try:
                    typo = fm["typography"]
                    blocks = {
                        "colors": utd.render_colors_block(fm["colors"]),
                        "typography": utd.render_typography_block(
                            (typo.get("heading") or {}).get("fontFamily"),
                            (typo.get("body") or {}).get("fontFamily"),
                            typo.get("google_fonts_url"),
                            typo.get("css_import"),
                            typo["scale"],
                            mono_font=utd._mono_font(typo)),
                        "spacing": utd.render_spacing_block(fm["spacing"]),
                        "rounded": utd.render_rounded_block(fm["rounded"]),
                    }
                    rebuilt = utd.splice_generated_blocks(design_text, blocks)
                except (KeyError, ValueError, TypeError) as e:
                    emit(6, "fail", "cannot rebuild body generated blocks "
                         "from frontmatter: %s" % e)
                    critical_fail = True
                else:
                    if rebuilt == design_text:
                        emit(6, "ok",
                             "body generated blocks in sync with frontmatter")
                    else:
                        emit(6, "fail",
                             "body generated blocks out of sync with frontmatter "
                             "- re-run uupm_to_design.py --from-design %s "
                             "--tokens-css <tokens.css>" % design_path)
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
                            mono_font=utd._mono_font(typo),
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
    print("impeccable tested version: %s" % TESTED_IMPECCABLE_VERSION)
    print("impeccable installed version: %s"
          % (imp_version if imp_version
             else "unknown (not resolved / no version field)"))
    print("impeccable contract: %s" % imp_contract)
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
