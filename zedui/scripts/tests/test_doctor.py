#!/usr/bin/env python3
"""Tests for zedui/scripts/doctor.py.

The doctor's skill resolution walks the *real* candidate skill directories on
this machine, so every test here constructs its own fake skills tree + fake
project inside a tempfile and patches ``doctor.candidate_dirs`` to point at it.
No test depends on a real local skill install.

Stdlib-only unittest (no pytest). Python 3.8 compatible: no walrus, no
f-string '=' specifier.

Run from the repo root:
    python3 -m unittest discover -s zedui/scripts/tests -v
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)  # zedui/scripts/
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import doctor  # noqa: E402  (sys.path set above)

DESIGN_SCRIPT = os.path.join(SCRIPTS_DIR, "uupm_to_design.py")
TESTED = doctor.TESTED_IMPECCABLE_VERSION

FIVE_SKILLS = ("ui-ux-pro-max", "design-taste-frontend", "interface-design",
               "impeccable", "zedui")


def _write_skill(root, dirname, name, version=None):
    """Write a minimal SKILL.md (frontmatter name: [+ version:]) and return
    its directory. The directory name may differ from the skill name."""
    d = os.path.join(root, dirname)
    os.makedirs(d, exist_ok=True)
    lines = ["---", "name: %s" % name]
    if version is not None:
        lines.append("version: %s" % version)
    lines.append("---")
    lines.append("# %s" % name)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return d


def _full_skill_tree(root, version=None, with_scripts=True):
    """All five skills under root. impeccable gets version (default = the
    tested baseline) plus scripts/context.mjs + scripts/detect.mjs so [3/6]
    passes; zedui gets real copies of the bridge/lint scripts so [5/6]
    py_compile passes. ui-ux-pro-max deliberately has no search.py so the
    real UUPM probe never runs inside a test (warn, not fail).

    Returns {skill_name: skill_dir}.
    """
    if version is None:
        version = TESTED
    dirs = {
        "ui-ux-pro-max": _write_skill(root, "uupm-dir", "ui-ux-pro-max"),
        "design-taste-frontend": _write_skill(root, "taste-dir", "design-taste-frontend"),
        "interface-design": _write_skill(root, "interface-dir", "interface-design"),
        "impeccable": _write_skill(root, "impeccable", "impeccable", version=version),
        "zedui": _write_skill(root, "zedui", "zedui"),
    }
    if with_scripts:
        imp = dirs["impeccable"]
        os.makedirs(os.path.join(imp, "scripts"), exist_ok=True)
        for fn in ("context.mjs", "detect.mjs"):
            with open(os.path.join(imp, "scripts", fn), "w", encoding="utf-8") as fh:
                fh.write("// stub %s\n" % fn)
        zed = dirs["zedui"]
        os.makedirs(os.path.join(zed, "scripts"), exist_ok=True)
        for fn in ("uupm_to_design.py", "token_lint.py"):
            shutil.copy2(os.path.join(SCRIPTS_DIR, fn),
                         os.path.join(zed, "scripts", fn))
    return dirs


def _run_doctor(project_root, skill_dirs):
    """Run doctor.main in-process with candidate_dirs patched to the fake
    skill dirs. Returns (exit_code, full_output)."""
    buf = io.StringIO()
    with mock.patch.object(doctor, "candidate_dirs", return_value=skill_dirs):
        with contextlib.redirect_stdout(buf):
            rc = doctor.main(["--project-root", project_root])
    return rc, buf.getvalue()


def _full_ds():
    """A complete, valid design-system dict for the fake project."""
    return {
        "project_name": "DoctorProbe",
        "category": "utility",
        "colors": {
            "primary": "#0F172A", "on_primary": "#FFFFFF", "secondary": "#64748B",
            "accent": "#F59E0B", "background": "#F8FAFC", "foreground": "#0F172A",
            "muted": "#94A3B8", "border": "#E2E8F0", "destructive": "#EF4444",
            "ring": "#F59E0B", "cta": "#F59E0B",
        },
        "typography": {
            "heading": "EB Garamond, Noto Serif SC",
            "body": "Inter, Noto Sans SC",
            "google_fonts_url": ("https://fonts.googleapis.com/css2?family=EB+Garamond"
                                 "&family=Inter&display=swap"),
            "css_import": ("@import url('https://fonts.googleapis.com/css2?family=EB+Garamond"
                           "&family=Inter&display=swap');"),
            "mood": "calm",
            "best_for": "docs",
        },
        "dials": {
            "variance": 3, "motion": 4, "density": 6,
            "variance_label": "balanced", "motion_label": "restrained",
            "density_label": "airy",
        },
        "spacing_scale": {
            "xs": "4px", "sm": "8px", "md": "12px", "lg": "16px",
            "xl": "24px", "2xl": "32px", "3xl": "64px",
        },
        "style": {
            "name": "Calm", "keywords": "calm", "best_for": "docs",
            "light_mode": "true", "dark_mode": "false", "performance": "high",
            "accessibility": "WCAG AA", "effects": "none",
        },
        "pattern": {
            "name": "Docs", "sections": "nav", "cta_placement": "top",
            "conversion": "signup", "color_strategy": "accent",
        },
        "anti_patterns": "clutter",
        "decision_rules": {"rule1": "use accent sparingly"},
        "motion_snippet": {
            "Category": "fade", "Duration": "200ms", "Easing": "ease-out",
            "Do": "use for toasts", "Don't": "not for nav",
            "Performance Notes": "GPU friendly",
        },
    }


def _gen_design_project(project_root, ds=None):
    """Run the real uupm_to_design.py to land DESIGN.md + tokens.css in the
    fake project. Returns (design_path, tokens_path)."""
    data = {"design_system": ds if ds is not None else _full_ds()}
    src = os.path.join(project_root, "input.json")
    with open(src, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    md = os.path.join(project_root, "DESIGN.md")
    css = os.path.join(project_root, "tokens.css")
    proc = subprocess.run(
        [sys.executable, DESIGN_SCRIPT, src, "-o", md, "--tokens-css", css,
         "--marketing-dials", "2,5,7"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError("uupm_to_design.py failed: %s" % proc.stderr)
    return md, css


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class TestSkillResolution(unittest.TestCase):
    """Resolution matches frontmatter ``name:`` (case-insensitive), never the
    directory name; project-level candidate wins; duplicates are reported."""

    def test_resolve_by_name_not_dirname(self):
        with tempfile.TemporaryDirectory() as td:
            d = _write_skill(td, "taste-dir", "design-taste-frontend")
            hits = doctor.resolve_skill("design-taste-frontend", [td])
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0][2], os.path.join(d, "SKILL.md"))
            # case-insensitive match, as SKILL.md documents
            hits = doctor.resolve_skill("DESIGN-TASTE-FRONTEND", [td])
            self.assertEqual(len(hits), 1)

    def test_project_level_priority(self):
        with tempfile.TemporaryDirectory() as td:
            proj = os.path.join(td, "proj-skills")
            home = os.path.join(td, "home-skills")
            os.makedirs(proj)
            os.makedirs(home)
            # only ui-ux-pro-max is duplicated at project level; the rest of
            # the tree lives in the lower-priority home dir
            _write_skill(proj, "uupm", "ui-ux-pro-max")
            _full_skill_tree(home)
            hits = doctor.resolve_skill("ui-ux-pro-max", [proj, home])
            self.assertEqual(len(hits), 2)
            # first hit = highest-priority candidate
            self.assertTrue(hits[0][2].startswith(proj))
            self.assertTrue(hits[1][2].startswith(home))
            # and the doctor run resolves to the project-level install
            proj_root = os.path.join(td, "proj-root")
            os.makedirs(proj_root)
            rc, out = _run_doctor(proj_root, [proj, home])
            self.assertEqual(rc, 0, out)
            self.assertIn("ui-ux-pro-max -> %s" % os.path.join(proj, "uupm"), out)

    def test_duplicate_install_warning(self):
        with tempfile.TemporaryDirectory() as td:
            d1 = os.path.join(td, "skills-a")
            d2 = os.path.join(td, "skills-b")
            os.makedirs(d1)
            os.makedirs(d2)
            _full_skill_tree(d1)
            # duplicate only impeccable in the second candidate dir
            _write_skill(d2, "impeccable-copy", "impeccable", version=TESTED)
            proj_root = os.path.join(td, "proj-root")
            os.makedirs(proj_root)
            rc, out = _run_doctor(proj_root, [d1, d2])
            self.assertEqual(rc, 0, out)
            self.assertIn("impeccable also installed at:", out)
            self.assertIn("impeccable-copy", out)


class TestVersionDrift(unittest.TestCase):
    """An installed impeccable version that differs from the tested baseline
    is a warning, never a failure; the summary reports it as unknown."""

    def test_drift_warns_but_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _full_skill_tree(td, version="9.9.9")
            proj_root = os.path.join(td, "proj-root")
            os.makedirs(proj_root)
            rc, out = _run_doctor(proj_root, [td])
            self.assertEqual(rc, 0, out)
            self.assertIn("9.9.9 differs from the tested %s" % TESTED, out)
            self.assertIn("impeccable installed version: 9.9.9", out)
            self.assertIn("impeccable contract: unknown", out)
            self.assertNotIn("matches the tested baseline", out)


class TestUupmProbeContract(unittest.TestCase):
    """The UUPM probe validates against the SAME contract the bridge
    enforces: an installed UUPM whose palette lacks a required role (cta on
    older copies) must fail the probe, not just the bridge."""

    def _fake_search_py(self, td, colors):
        import uupm_to_design as utd
        payload = {"design_system": {
            "project_name": "Probe", "colors": colors,
            "typography": {"heading": "Inter", "body": "Inter"},
            "spacing_scale": {"md": "16px"},
            "dials": {"variance": 3, "motion": 4, "density": 5},
        }}
        script = os.path.join(td, "search.py")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("import json\nprint(json.dumps(%r))\n" % payload)
        return script

    def _full_colors(self):
        import uupm_to_design as utd
        return {role: "#112233" for role in utd.COLOR_ROLES}

    def test_probe_passes_with_all_required_roles(self):
        with tempfile.TemporaryDirectory() as td:
            ok, res = doctor._probe_uupm_contract(
                self._fake_search_py(td, self._full_colors()))
            self.assertTrue(ok, res)

    def test_probe_fails_when_cta_missing(self):
        with tempfile.TemporaryDirectory() as td:
            colors = self._full_colors()
            del colors["cta"]
            ok, res = doctor._probe_uupm_contract(
                self._fake_search_py(td, colors))
            self.assertFalse(ok)
            self.assertIn("cta", res)

    def test_probe_tolerates_empty_role_values(self):
        """UUPM leaves palette slots '' on a knowledge-base miss — data, not
        schema. Keys present with empty values must still pass the probe."""
        with tempfile.TemporaryDirectory() as td:
            colors = self._full_colors()
            colors["muted"] = ""
            colors["border"] = ""
            ok, res = doctor._probe_uupm_contract(
                self._fake_search_py(td, colors))
            self.assertTrue(ok, res)
            self.assertIn("empty", res)

    def test_probe_fails_on_bad_json(self):
        with tempfile.TemporaryDirectory() as td:
            script = os.path.join(td, "search.py")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write("print('not json')\n")
            ok, res = doctor._probe_uupm_contract(script)
            self.assertFalse(ok)
            self.assertIn("JSON", res)


class TestMissingSkillEnvironment(unittest.TestCase):
    """The doctor's main entry exits 1 when no skill at all resolves."""

    def test_no_skills_exits_1(self):
        with tempfile.TemporaryDirectory() as td:
            empty = os.path.join(td, "empty-skills")
            os.makedirs(empty)
            proj_root = os.path.join(td, "proj-root")
            os.makedirs(proj_root)
            rc, out = _run_doctor(proj_root, [empty])
            self.assertEqual(rc, 1)
            self.assertEqual(
                out.count("not found in any candidate skill directory"),
                len(FIVE_SKILLS))


class TestProjectDesignSync(unittest.TestCase):
    """A DESIGN.md generated by uupm_to_design passes the project checks;
    hand edits to the body generated tables or to tokens.css are caught."""

    def _clean(self):
        """Fake skills tree + a project whose DESIGN.md/tokens.css were
        generated by the real uupm_to_design.py. Returns
        (skill_root, project_root, design_path, tokens_path)."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        _full_skill_tree(td.name)
        proj_root = os.path.join(td.name, "proj-root")
        os.makedirs(proj_root)
        md, css = _gen_design_project(proj_root)
        return td.name, proj_root, md, css

    def test_clean_project_passes(self):
        skill_root, proj_root, md, css = self._clean()
        rc, out = _run_doctor(proj_root, [skill_root])
        self.assertEqual(rc, 0, out)
        self.assertIn("body generated blocks in sync with frontmatter", out)
        self.assertIn("%s in sync with DESIGN.md" % css, out)
        self.assertIn("impeccable contract: compatible", out)

    def test_hand_edited_body_table_detected(self):
        skill_root, proj_root, md, css = self._clean()
        text = _read(md)
        self.assertIn("| accent | #F59E0B |", text)
        _write(md, text.replace("| accent | #F59E0B |", "| accent | #112233 |"))
        rc, out = _run_doctor(proj_root, [skill_root])
        self.assertEqual(rc, 1)
        self.assertIn("body generated blocks out of sync with frontmatter", out)

    def test_hand_edited_tokens_css_detected(self):
        skill_root, proj_root, md, css = self._clean()
        text = _read(css)
        self.assertIn("--accent: #F59E0B;", text)
        _write(css, text.replace("--accent: #F59E0B;", "--accent: #654321;"))
        rc, out = _run_doctor(proj_root, [skill_root])
        self.assertEqual(rc, 1)
        self.assertIn("%s is out of sync with DESIGN.md" % css, out)

    def test_editing_human_section_stays_in_sync(self):
        # Edits OUTSIDE the generated markers must NOT trip the body check:
        # only the marked blocks are derived views of the frontmatter.
        skill_root, proj_root, md, css = self._clean()
        text = _read(md)
        self.assertIn("## Components", text)
        _write(md, text.replace(
            "## Components\n",
            "## Components\n\nHUMAN-KEPT-LINE\n\n"))
        rc, out = _run_doctor(proj_root, [skill_root])
        self.assertEqual(rc, 0, out)
        self.assertIn("body generated blocks in sync with frontmatter", out)


if __name__ == "__main__":
    unittest.main()
