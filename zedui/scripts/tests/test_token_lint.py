#!/usr/bin/env python3
"""Tests for zedui/scripts/token_lint.py.

Stdlib-only unittest (no pytest). Python 3.8 compatible: no walrus, no
f-string '=' specifier.

Run from the repo root:
    python3 -m unittest discover -s zedui/scripts/tests -v
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)  # zedui/scripts/
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import token_lint as tl  # noqa: E402  (sys.path set above)

SCRIPT = os.path.join(SCRIPTS_DIR, "token_lint.py")

BAD_CSS = ".a { padding: 17px; }\n"


class TokenLintCoreTests(unittest.TestCase):
    """False negatives: every historical hole must now be caught."""

    def test_var_mixed_value_flags(self):
        cases = [
            "padding: var(--space-sm) 17px;",
            "gap: calc(var(--space-md) + 3px);",
            "margin: 8px var(--space-lg);",
        ]
        for case in cases:
            self.assertTrue(tl.lint_text(case),
                            "expected finding for %r" % case)

    def test_var_mixed_value_flag_kinds(self):
        finds = tl.lint_text("padding: var(--space-sm) 17px;")
        self.assertEqual(len(finds), 1)
        self.assertEqual(finds[0][1], "padding")

    def test_logical_properties_flags(self):
        logical = [
            "margin-inline", "margin-inline-start", "margin-inline-end",
            "margin-block", "margin-block-start", "margin-block-end",
            "padding-inline", "padding-inline-start", "padding-inline-end",
            "padding-block", "padding-block-start", "padding-block-end",
            "inset-inline", "inset-inline-start", "inset-inline-end",
            "inset-block", "inset-block-start", "inset-block-end",
        ]
        for prop in logical:
            self.assertTrue(tl.lint_text("%s: 12px;" % prop),
                            "expected finding for %s" % prop)

    def test_react_bare_number_flags(self):
        self.assertTrue(tl.lint_text("style={{ padding: 17 }}"))
        self.assertTrue(tl.lint_text("style={{ margin: 1.5 }}"))
        self.assertTrue(tl.lint_text("const style = { padding: 17 };"))
        # quoted numbers are px too in React
        self.assertTrue(tl.lint_text('style={{ padding: "17" }}'))

    def test_tailwind_arbitrary_flags(self):
        cases = [
            '<div class="p-[17px]"></div>',
            '<div class="px-[8px]"></div>',
            '<div class="mt-[-8px]"></div>',
            '<div class="-m-[4px]"></div>',
            '<div class="gap-[13px] space-x-[8px]"></div>',
            '<div class="inset-x-[4px] scroll-mt-[8px]"></div>',
            '<div class="pl-[1.5rem]"></div>',
        ]
        for case in cases:
            self.assertTrue(tl.lint_text(case),
                            "expected finding for %r" % case)

    def test_tailwind_arbitrary_finding_shape(self):
        finds = tl.lint_text('<div class="p-[17px]"></div>')
        self.assertEqual(finds[0][1], "class")
        self.assertEqual(finds[0][2], "p-[17px]")

    def test_prune_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "node_modules"))
            os.makedirs(os.path.join(td, ".next"))
            os.makedirs(os.path.join(td, "src"))
            for sub in ("node_modules", ".next"):
                with open(os.path.join(td, sub, "dep.css"), "w") as fh:
                    fh.write(BAD_CSS)
            with open(os.path.join(td, "src", "a.css"), "w") as fh:
                fh.write(BAD_CSS)
            files = list(tl.walk_files(td, [".css"]))
            self.assertIn(os.path.join(td, "src", "a.css"), files)
            self.assertFalse(
                any("node_modules" in p or ".next" in p for p in files))

    def test_default_prune_constant(self):
        for name in ("node_modules", ".next", "dist", "build", "coverage",
                     "vendor", "out", ".nuxt", ".cache", "__pycache__"):
            self.assertIn(name, tl.DEFAULT_PRUNE_DIRS)


class TokenLintFalsePositiveTests(unittest.TestCase):
    """Clean code must stay clean."""

    def test_pure_var_allowed(self):
        self.assertFalse(tl.lint_text("padding: var(--space-sm);"))
        self.assertFalse(tl.lint_text("margin: 0 var(--space-lg);"))
        self.assertFalse(tl.lint_text("margin: var(--space-sm) var(--space-lg);"))
        self.assertFalse(tl.lint_text("padding: var(--space-md, 8px);"))
        self.assertFalse(tl.lint_text("gap: calc(var(--space-md) * 2);"))

    def test_zero_and_keywords_allowed(self):
        self.assertFalse(tl.lint_text("margin: 0;"))
        self.assertFalse(tl.lint_text("padding: 0px;"))
        self.assertFalse(tl.lint_text("top: auto;"))
        self.assertFalse(tl.lint_text("left: 0 0;"))

    def test_non_spacing_bare_numbers_allowed(self):
        self.assertFalse(tl.lint_text("line-height: 1.5;"))
        self.assertFalse(tl.lint_text("flex: 1;"))
        self.assertFalse(tl.lint_text("z-index: 10;"))

    def test_tailwind_allow_list(self):
        allowed = [
            '<div class="leading-[1.1]"></div>',
            '<div class="min-h-[100dvh]"></div>',
            '<div class="w-[300px] h-[200px] max-w-[400px]"></div>',
            '<div class="text-[17px] bg-[#fff]"></div>',
            '<div class="p-4 mt-2 -mx-3"></div>',
        ]
        for case in allowed:
            self.assertFalse(tl.lint_text(case),
                             "expected clean for %r" % case)


class TokenLintCliTests(unittest.TestCase):
    """Exit-code contract and file-level behaviors (0 clean / 1 / 2)."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, SCRIPT] + list(args),
            capture_output=True, text=True)

    def test_exit_0_clean(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "clean.css")
            with open(path, "w") as fh:
                fh.write(".a { padding: var(--space-sm); margin: 0; }\n")
            r = self._run(path)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("OK", r.stdout)

    def test_exit_1_finding(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "bad.css")
            with open(path, "w") as fh:
                fh.write(".a { padding: var(--space-sm) 17px; }\n")
            r = self._run(path)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("Summary", r.stdout)
            self.assertIn("17px", r.stdout)

    def test_exit_2_usage_error(self):
        r = self._run("no-such-target-xyz")
        self.assertEqual(r.returncode, 2)
        self.assertIn("error: target not found", r.stderr)

    def test_generated_file_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "tokens.css")
            with open(path, "w") as fh:
                fh.write("/* GENERATED FILE -- DO NOT EDIT BY HAND */\n"
                         ".pad { padding: 17px; }\n")
            self.assertTrue(tl.is_generated_file(path))
            r = self._run(path)
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_node_modules_pruned_cli(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "node_modules"))
            os.makedirs(os.path.join(td, "src"))
            for sub in ("node_modules", "src"):
                with open(os.path.join(td, sub, "x.css"), "w") as fh:
                    fh.write(BAD_CSS)
            r = self._run(td)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("src" + os.sep + "x.css", r.stdout)
            self.assertNotIn("node_modules", r.stdout)

    def test_exclude_still_works(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "legacy.css")
            with open(path, "w") as fh:
                fh.write(BAD_CSS)
            r = self._run(path, "--exclude", "legacy.css")
            self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
