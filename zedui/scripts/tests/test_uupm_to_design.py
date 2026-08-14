#!/usr/bin/env python3
"""Tests for zedui/scripts/uupm_to_design.py.

Stdlib-only unittest (no pytest). Python 3.8 compatible: no walrus, no
f-string '=' specifier. Assertions follow the *actual* script behavior,
not the docstring.

Run from the repo root:
    python3 -m unittest discover -s zedui/scripts/tests -v
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)  # zedui/scripts/
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import uupm_to_design as ud  # noqa: E402  (sys.path set above)

SCRIPT = os.path.join(SCRIPTS_DIR, "uupm_to_design.py")

# Colour used for the frontmatter-edit round-trip; distinct from every other
# colour in the fixture so sibling rows (ring/cta still #F59E0B) stay provable.
EDITED_ACCENT = "#7C3AED"


def _full_ds():
    """A complete, valid design-system dict (11 roles + extras + dials)."""
    return {
        "project_name": "ZedUI",
        "category": "utility",
        "colors": {
            "primary": "#0F172A",
            "on_primary": "#FFFFFF",
            "secondary": "#64748B",
            "accent": "#F59E0B",
            "background": "#F8FAFC",
            "foreground": "#0F172A",
            "muted": "#94A3B8",
            "border": "#E2E8F0",
            "destructive": "#EF4444",
            "ring": "#F59E0B",
            "cta": "#F59E0B",
            "text": "#111827",
            "notes": "probe note",
            "secondary_text": "#475569",
            "dark_background": "#0B1120",
            "dark_foreground": "#F1F5F9",
        },
        "typography": {
            "heading": "EB Garamond, Noto Serif SC",
            "body": "Inter, Noto Sans SC",
            "google_fonts_url": (
                "https://fonts.googleapis.com/css2?family=EB+Garamond"
                "&family=Inter&display=swap"
            ),
            "css_import": (
                "@import url('https://fonts.googleapis.com/css2?"
                "family=EB+Garamond&family=Inter&display=swap');"
            ),
            "mood": "calm",
            "best_for": "documentation",
        },
        "dials": {
            "variance": 3,
            "motion": 4,
            "density": 6,
            "variance_label": "balanced",
            "motion_label": "restrained",
            "density_label": "airy",
        },
        "spacing_scale": {
            "xs": "4px", "sm": "8px", "md": "12px", "lg": "16px",
            "xl": "24px", "2xl": "32px", "3xl": "64px",
        },
        "style": {
            "name": "Calm Minimal",
            "keywords": "calm, minimal",
            "best_for": "docs",
            "light_mode": "true",
            "dark_mode": "false",
            "performance": "high",
            "accessibility": "WCAG AA",
            "effects": "none",
        },
        "pattern": {
            "name": "Documentation",
            "sections": "nav, content, footer",
            "cta_placement": "top-right",
            "conversion": "signup",
            "color_strategy": "accent for actions",
        },
        "anti_patterns": "clutter\noverload",
        "decision_rules": {"rule1": "use accent sparingly"},
        "motion_snippet": {
            "Category": "fade",
            "Duration": "200ms",
            "Easing": "ease-out",
            "Do": "use for toasts",
            "Don't": "not for core nav",
            "Performance Notes": "GPU friendly",
        },
    }


def run_script(args, cwd=None):
    """Run the bridge script in a subprocess.

    Returns (returncode, stdout, stderr).
    """
    proc = subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _write_json(tmpdir, ds=None, name="input.json"):
    data = {"design_system": ds if ds is not None else _full_ds()}
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _gen_md(tmpdir, extra_args=None, ds=None, name="DESIGN.md"):
    """JSON -> DESIGN.md with marketing dials; returns the MD path."""
    src = _write_json(tmpdir, ds=ds)
    out = os.path.join(tmpdir, name)
    args = [src, "-o", out, "--marketing-dials", "2,5,7"]
    if extra_args:
        args += extra_args
    rc, _so, se = run_script(args)
    if rc != 0:
        raise AssertionError("gen_md failed: %s" % se)
    return out


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _fm_and_body(text):
    """Split a generated DESIGN.md into (frontmatter, body).

    The frontmatter delimiter is a line that is exactly '---'. A naive
    text.split("---") is wrong: markdown table separator rows such as
    '|---|---|---|' also contain '---'.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("file does not start with '---'")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise AssertionError("frontmatter not closed")
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1:])


class TestGoldenJsonToDesignMd(unittest.TestCase):
    """UUPM JSON -> DESIGN.md golden: frontmatter sections, 4 marker pairs,
    dial table."""

    def test_full_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = _write_json(tmp)
            out = os.path.join(tmp, "DESIGN.md")
            css = os.path.join(tmp, "tokens.css")
            rc, _so, se = run_script(
                [src, "-o", out, "--tokens-css", css,
                 "--marketing-dials", "2,5,7"])
            self.assertEqual(rc, 0, se)
            text = _read(out)

            # --- frontmatter sections ---
            fm, body = _fm_and_body(text)
            self.assertIn('name: "ZedUI Design System"', fm)
            # 11 roles present
            for role in ud.COLOR_ROLES:
                self.assertRegex(fm, r"\n  %s: \"#" % role)
            # extra tokens survive in the frontmatter
            self.assertIn('secondary_text: "#475569"', fm)
            self.assertIn('dark_background: "#0B1120"', fm)
            # typography section: heading/body/scale
            self.assertIn('fontFamily: "EB Garamond, Noto Serif SC"', fm)
            self.assertIn('fontSize: "32px"', fm)
            self.assertIn('    base: "16px"', fm)
            self.assertIn('    2xl: "32px"', fm)
            # rounded / spacing sections
            self.assertIn("rounded:", fm)
            self.assertIn('  none: "0px"', fm)
            self.assertIn('  md: "8px"', fm)
            self.assertIn("spacing:", fm)
            self.assertIn('  md: "12px"', fm)
            self.assertIn('  3xl: "64px"', fm)

            # --- 4 pairs of generated markers in the body ---
            for block in ("colors", "typography", "spacing", "rounded"):
                self.assertIn(
                    "<!-- zedui:generated:%s:start -->" % block, body)
                self.assertIn(
                    "<!-- zedui:generated:%s:end -->" % block, body)
            self.assertEqual(
                body.count("<!-- zedui:generated:"), 4 * 2)

            # --- dial table rows ---
            self.assertIn("| Marketing | 2 | 5 | 7 |", body)
            self.assertIn(
                "| Product | 3 (balanced) | 4 (restrained) | 6 (airy) |",
                body)

            # --- colors table has the 11 roles + extras ---
            self.assertIn("| accent | #F59E0B |", body)
            self.assertIn("| cta | #F59E0B |", body)
            self.assertIn("| secondary_text | #475569 |", body)

            # --- Components placeholder section present ---
            self.assertIn("## Components", body)

            # --- tokens.css also written ---
            self.assertTrue(os.path.exists(css))


class TestFromDesignTokensCss(unittest.TestCase):
    """DESIGN.md frontmatter -> tokens.css golden: var names/values."""

    def _prep(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        md = _gen_md(tmp.name)
        return tmp.name, md

    def test_golden_css_vars(self):
        tmp, md = self._prep()
        before = _read(md)
        css = os.path.join(tmp, "tokens.css")
        rc, _so, se = run_script(["--from-design", md, "--tokens-css", css])
        self.assertEqual(rc, 0, se)
        css_text = _read(css)

        self.assertIn("GENERATED FILE", css_text)
        self.assertIn("--accent: #F59E0B;", css_text)
        self.assertIn("--on-primary: #FFFFFF;", css_text)
        self.assertIn("--font-heading: EB Garamond, Noto Serif SC;", css_text)
        self.assertIn("--font-body: Inter, Noto Sans SC;", css_text)
        self.assertIn("--text-2xl: 32px;", css_text)
        self.assertIn("--radius-md: 8px;", css_text)
        self.assertIn("--space-md: 12px;", css_text)
        # underscore -> hyphen on colour extras
        self.assertIn("--secondary-text: #475569;", css_text)
        self.assertIn("--dark-background: #0B1120;", css_text)

        # a no-op re-sync must not rewrite the DESIGN.md
        after = _read(md)
        self.assertEqual(after, before)

    def test_from_design_requires_tokens_css(self):
        _tmp, md = self._prep()
        rc, _so, se = run_script(["--from-design", md])
        self.assertEqual(rc, 1)
        self.assertIn("requires --tokens-css", se)


class TestRoundTrip(unittest.TestCase):
    """Edit a frontmatter colour -> --from-design -> body table AND tokens.css
    reflect the new value; the ## Components human area is untouched."""

    def test_frontmatter_edit_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = _gen_md(tmp)
            text = _read(md)
            # Human-maintained line inside ## Components.
            text = text.replace(
                "## Components\n\n",
                "## Components\n\nHUMAN-KEPT-LINE\n\n")
            # Edit only the frontmatter accent value.
            lines = text.splitlines()
            for i, ln in enumerate(lines):
                if ln.strip().startswith("accent:") and "|" not in ln:
                    lines[i] = '  accent: "%s"' % EDITED_ACCENT
                    break
            else:
                self.fail("frontmatter accent line not found")
            md_edited = os.path.join(tmp, "DESIGN.md")
            with open(md_edited, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))

            css = os.path.join(tmp, "tokens.css")
            rc, _so, se = run_script(
                ["--from-design", md_edited, "--tokens-css", css])
            self.assertEqual(rc, 0, se)

            _fm, body = _fm_and_body(_read(md_edited))
            # body colours table row updated...
            self.assertIn("| accent | %s |" % EDITED_ACCENT, body)
            # ...and siblings untouched
            self.assertIn("| ring | #F59E0B |", body)
            self.assertIn("| cta | #F59E0B |", body)
            # tokens.css updated
            self.assertIn("--accent: %s;" % EDITED_ACCENT, _read(css))
            # human section preserved byte-for-byte
            self.assertIn("HUMAN-KEPT-LINE", body)
            self.assertNotIn("%s|" % EDITED_ACCENT, body.replace(
                "| accent | %s |" % EDITED_ACCENT, ""))


class TestCjkFontStack(unittest.TestCase):
    """Font families containing a CJK font in a comma stack survive
    write + parse + round-trip."""

    def test_cjk_family_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = _gen_md(tmp)
            text = _read(md)
            fm, body = _fm_and_body(text)
            self.assertIn(
                'fontFamily: "EB Garamond, Noto Serif SC"', fm)
            self.assertIn(
                'fontFamily: "Inter, Noto Sans SC"', fm)
            self.assertIn(
                "**Heading font**: EB Garamond, Noto Serif SC", body)
            self.assertIn("**Body font**: Inter, Noto Sans SC", body)

            # parse back the frontmatter directly
            parsed = ud.parse_design_frontmatter(text)
            self.assertEqual(
                parsed["typography"]["heading"]["fontFamily"],
                "EB Garamond, Noto Serif SC")
            self.assertEqual(
                parsed["typography"]["body"]["fontFamily"],
                "Inter, Noto Sans SC")

            # and the CSS value keeps the full comma stack
            css = os.path.join(tmp, "tokens.css")
            rc, _so, se = run_script(
                ["--from-design", md, "--tokens-css", css])
            self.assertEqual(rc, 0, se)
            css_text = _read(css)
            self.assertIn(
                "--font-heading: EB Garamond, Noto Serif SC;", css_text)
            self.assertIn("--font-body: Inter, Noto Sans SC;", css_text)


class TestQuotedKeyYamlBoundary(unittest.TestCase):
    """parse_design_frontmatter handles quoted keys, colons inside values,
    inline comments, and hex values that must not be clipped."""

    SAMPLE = (
        "---\n"
        "colors:\n"
        '  "20": "16px"\n'
        '  cta: "#0066FF" # inline comment\n'
        '  dark_primary: "#000000"\n'
        '  spacing_key: "4px,8px" # another # comment\n'
        "typography:\n"
        "  heading:\n"
        '    fontFamily: "EB Garamond, Noto Serif SC"\n'
        '  google_fonts_url: "https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter&display=swap"\n'
        "  scale:\n"
        '    base: "16px"\n'
        '    2xl: "32px"\n'
        "---\n"
    )

    def test_quoted_key_colon_url_inline_comment(self):
        r = ud.parse_design_frontmatter(self.SAMPLE)
        self.assertEqual(r["colors"]["20"], "16px")       # quoted key
        self.assertEqual(r["colors"]["cta"], "#0066FF")   # hex survives comment
        self.assertEqual(r["colors"]["dark_primary"], "#000000")
        self.assertEqual(r["colors"]["spacing_key"], "4px,8px")
        self.assertEqual(
            r["typography"]["google_fonts_url"],
            "https://fonts.googleapis.com/css2?family=EB+Garamond"
            "&family=Inter&display=swap")
        self.assertEqual(r["typography"]["scale"]["2xl"], "32px")

    def test_generated_frontmatter_parses_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = _gen_md(tmp)
            parsed = ud.parse_design_frontmatter(_read(md))
            self.assertEqual(parsed["colors"]["accent"], "#F59E0B")
            self.assertEqual(parsed["colors"]["secondary_text"], "#475569")
            self.assertEqual(
                parsed["typography"]["heading"]["fontFamily"],
                "EB Garamond, Noto Serif SC")
            self.assertEqual(parsed["rounded"]["md"], "8px")
            self.assertEqual(parsed["spacing"]["2xl"], "32px")

    def test_hex_value_not_clipped_as_comment(self):
        # '#' immediately followed by hex digits, quoted: not a comment.
        fm = "---\ncolors:\n  accent: \"#0066FF\"\n---\n"
        r = ud.parse_design_frontmatter(fm)
        self.assertEqual(r["colors"]["accent"], "#0066FF")


class TestExtraColorTokens(unittest.TestCase):
    """secondary_text / dark_* extra tokens survive frontmatter, body table
    and tokens.css."""

    def test_extra_tokens_survive_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = _gen_md(tmp)
            text = _read(md)
            fm, body = _fm_and_body(text)
            self.assertIn('secondary_text: "#475569"', fm)
            self.assertIn('dark_background: "#0B1120"', fm)
            self.assertIn('dark_foreground: "#F1F5F9"', fm)
            self.assertIn("| secondary_text | #475569 |", body)
            self.assertIn("| dark_background | #0B1120 |", body)

            css = os.path.join(tmp, "tokens.css")
            rc, _so, se = run_script(
                ["--from-design", md, "--tokens-css", css])
            self.assertEqual(rc, 0, se)
            css_text = _read(css)
            self.assertIn("--secondary-text: #475569;", css_text)
            self.assertIn("--dark-background: #0B1120;", css_text)
            self.assertIn("--dark-foreground: #F1F5F9;", css_text)

            # body table still shows them after a re-sync
            after_body = _fm_and_body(_read(md))[1]
            self.assertIn("| secondary_text | #475569 |", after_body)


class TestCustomScales(unittest.TestCase):
    """--rounded/--type-scale custom ladders take effect; spacing stays driven
    by the JSON spacing_scale."""

    def test_custom_rounded_and_type_scale(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = _gen_md(tmp, extra_args=[
                "--rounded", "0px,6px,10px",
                "--type-scale", "10px,12px,16px,22px,30px,42px,58px",
            ])
            text = _read(md)
            fm, body = _fm_and_body(text)

            # rounded ladder from the flag
            self.assertIn('  none: "0px"', fm)
            self.assertIn('  sm: "6px"', fm)
            self.assertIn('  md: "10px"', fm)
            self.assertIn("| none | 0px |", body)
            self.assertIn("| sm | 6px |", body)
            self.assertIn("| md | 10px |", body)

            # type scale from the flag: index 1 -> sm, index 5 -> 2xl
            self.assertIn('    sm: "12px"', fm)
            self.assertIn('    2xl: "42px"', fm)
            self.assertIn("| sm | 12px |", body)
            self.assertIn("| 2xl | 42px |", body)

            # spacing still driven by the JSON spacing_scale, not the flags
            self.assertIn('  md: "12px"', fm)
            self.assertIn('  2xl: "32px"', fm)
            self.assertIn("| md | 12px |", body)
            self.assertIn("| 2xl | 32px |", body)

            css = os.path.join(tmp, "tokens.css")
            rc, _so, se = run_script(
                ["--from-design", md, "--tokens-css", css])
            self.assertEqual(rc, 0, se)
            css_text = _read(css)
            self.assertIn("--radius-sm: 6px;", css_text)
            self.assertIn("--radius-md: 10px;", css_text)
            self.assertIn("--text-sm: 12px;", css_text)
            self.assertIn("--text-2xl: 42px;", css_text)
            self.assertIn("--space-md: 12px;", css_text)
            self.assertNotIn("--space-md: 10px;", css_text)


class TestDials(unittest.TestCase):
    """CLI/JSON dial range checks, missing-marketing strict failure and the
    --allow-incomplete TBD escape hatch."""

    def test_cli_dial_zero_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = _write_json(tmp)
            rc, _so, se = run_script(
                [src, "-o", os.path.join(tmp, "d0.md"),
                 "--marketing-dials", "0,4,8"])
            self.assertEqual(rc, 2)  # argparse error
            self.assertIn("between 1 and 10", se)

    def test_cli_dial_eleven_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = _write_json(tmp)
            rc, _so, se = run_script(
                [src, "-o", os.path.join(tmp, "d11.md"),
                 "--marketing-dials", "11,4,8"])
            self.assertEqual(rc, 2)
            self.assertIn("between 1 and 10", se)

    def test_json_fallback_dial_out_of_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            ds = _full_ds()
            ds["dials"]["variance"] = 11
            src = _write_json(tmp, ds=ds)
            rc, _so, se = run_script(
                [src, "-o", os.path.join(tmp, "j11.md"),
                 "--marketing-dials", "3,4,8"])
            self.assertEqual(rc, 1)
            self.assertIn("JSON dials values must be between 1 and 10", se)
            self.assertFalse(os.path.exists(os.path.join(tmp, "j11.md")))

    def test_missing_marketing_dials_strict_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            ds = _full_ds()
            ds.pop("dials")
            src = _write_json(tmp, ds=ds)
            out = os.path.join(tmp, "nodials.md")
            rc, _so, se = run_script([src, "-o", out])
            self.assertEqual(rc, 1)
            self.assertIn("marketing dials missing", se)
            self.assertFalse(os.path.exists(out))

    def test_allow_incomplete_writes_tbd_dials(self):
        with tempfile.TemporaryDirectory() as tmp:
            ds = _full_ds()
            ds.pop("dials")
            src = _write_json(tmp, ds=ds)
            out = os.path.join(tmp, "tbd.md")
            rc, _so, se = run_script(
                [src, "-o", out, "--allow-incomplete"])
            self.assertEqual(rc, 0, se)
            _fm, body = _fm_and_body(_read(out))
            self.assertIn("| Marketing | TBD | TBD | TBD |", body)
            self.assertIn("| Product | TBD | TBD | TBD |", body)


class TestIncompleteJson(unittest.TestCase):
    """{} fails closed (exit 1, no file) unless --allow-incomplete."""

    def test_empty_strict_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "empty.json")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("{}")
            out = os.path.join(tmp, "DESIGN.md")
            rc, _so, se = run_script([src, "-o", out])
            self.assertEqual(rc, 1)
            self.assertIn("incomplete design system", se)
            self.assertFalse(os.path.exists(out))

    def test_empty_allow_incomplete_lands_tbd(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "empty.json")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("{}")
            out = os.path.join(tmp, "DESIGN.md")
            rc, _so, se = run_script(
                [src, "-o", out, "--allow-incomplete"])
            self.assertEqual(rc, 0, se)
            text = _read(out)
            self.assertIn('name: "TBD Design System"', text)
            fm, body = _fm_and_body(text)
            self.assertIn('  primary: "TBD"', fm)
            self.assertIn("| Marketing | TBD | TBD | TBD |", body)
            # the whole colour ladder is TBD placeholders
            for role in ud.COLOR_ROLES:
                self.assertIn("| %s | TBD |" % role, body)


class TestValidationErrors(unittest.TestCase):
    """Short type scale, illegal CSS key, and pre-marker DESIGN.md all fail
    with clear errors."""

    def test_short_type_scale_strict_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = _write_json(tmp)
            rc, _so, se = run_script(
                [src, "-o", os.path.join(tmp, "short.md"),
                 "--type-scale", "12px,14px,16px,20px,24px",
                 "--marketing-dials", "2,5,7"])
            self.assertEqual(rc, 1)
            self.assertIn("at least 6 steps", se)
            self.assertFalse(os.path.exists(os.path.join(tmp, "short.md")))

    def test_invalid_css_key_from_design_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = _gen_md(tmp)
            lines = _read(md).splitlines()
            injected = []
            done = False
            for ln in lines:
                injected.append(ln)
                if not done and ln.strip() == "colors:":
                    injected.append('  secondary text: "#475569"')
                    done = True
            bad = os.path.join(tmp, "badkey.md")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("\n".join(injected))
            rc, _so, se = run_script(
                ["--from-design", bad, "--tokens-css",
                 os.path.join(tmp, "badkey.css")])
            self.assertEqual(rc, 1)
            self.assertIn(
                "invalid token key for a CSS custom property", se)

    def test_missing_markers_from_design_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = _gen_md(tmp)
            stripped = re.sub(
                r"^\s*<!-- zedui:generated:[^>]*-->\s*$", "",
                _read(md), flags=re.M)
            old = os.path.join(tmp, "nomarker.md")
            with open(old, "w", encoding="utf-8") as fh:
                fh.write(stripped)
            rc, _so, se = run_script(
                ["--from-design", old, "--tokens-css",
                 os.path.join(tmp, "nomarker.css")])
            self.assertEqual(rc, 1)
            self.assertIn(
                "generated block markers for 'colors' not found", se)


class TestAtomicWriteAndForce(unittest.TestCase):
    """Existing output refuses to overwrite unless --force."""

    def test_existing_output_requires_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = _write_json(tmp)
            out = os.path.join(tmp, "DESIGN.md")
            with open(out, "w", encoding="utf-8") as fh:
                fh.write("OLD-CONTENT")
            rc, _so, se = run_script(
                [src, "-o", out, "--marketing-dials", "2,5,7"])
            self.assertEqual(rc, 1)
            self.assertIn("output file already exists", se)
            self.assertEqual(_read(out), "OLD-CONTENT")  # untouched

            rc, _so, se = run_script(
                [src, "-o", out, "--marketing-dials", "2,5,7", "--force"])
            self.assertEqual(rc, 0, se)
            self.assertTrue(_read(out).startswith("---"))

    def test_tokens_css_always_overwritten(self):
        # tokens.css is a build artifact: no existence check.
        with tempfile.TemporaryDirectory() as tmp:
            src = _write_json(tmp)
            out = os.path.join(tmp, "DESIGN.md")
            css = os.path.join(tmp, "tokens.css")
            with open(css, "w", encoding="utf-8") as fh:
                fh.write("OLD-CSS")
            rc, _so, se = run_script(
                [src, "-o", out, "--tokens-css", css,
                 "--marketing-dials", "2,5,7"])
            self.assertEqual(rc, 0, se)
            self.assertNotEqual(_read(css), "OLD-CSS")
            self.assertIn("--accent: #F59E0B;", _read(css))


if __name__ == "__main__":
    unittest.main()
