#!/usr/bin/env python3
"""uupm_to_design.py — Convert UI-UX-Pro-Max (uipro) design-system JSON to google-labs DESIGN.md.

The input is the JSON emitted by uipro's ``search.py --design-system --json``
(the outer wrapper is fixed to ``{"design_system": {...}}``). The conversion is
mechanical: JSON in, fixed-format markdown out.

Pure standard library (stdlib only). Python 3.8+.

Usage:
    uupm_to_design.py INPUT [-o OUTPUT] [--rounded "0px,4px,8px,12px,16px,24px"]
                            [--type-scale "12px,14px,16px,20px,24px,32px,40px,48px,64px"]
                            [--marketing-dials V,M,D] [--product-dials V,M,D]
                            [--tokens-css TOKENS_CSS] [--force] [--allow-incomplete]

    uupm_to_design.py --from-design DESIGN.md --tokens-css TOKENS_CSS

    INPUT    path to the design-system JSON, or ``-`` to read from stdin.
    -o       output markdown path (default: ./DESIGN.md); refuses to overwrite
             an existing file unless --force is given (exit code 1).
    --tokens-css   also emit a generated CSS-custom-properties token file
                   (colors/typography/type scale/rounded/spacing). This file is
                   a build artifact: always overwritten, never hand-edited.
    --from-design  read the frontmatter of an existing DESIGN.md (the SSOT),
                   regenerate the marked token blocks in its body AND the token
                   CSS file from it. This is the Phase 3 path: edit the DESIGN.md
                   frontmatter, then re-sync body + tokens.css so the document
                   can never disagree with itself.
    --allow-incomplete   accept missing fields/dials and write "TBD"
                   placeholders. Without it the script fails closed on
                   incomplete input (missing colors/fonts/dials/short scales).

DESIGN.md format (zedui-design-schema-v1): the YAML frontmatter is the single
source of truth for every token value. Token tables in the markdown body live
inside ``<!-- zedui:generated:<name>:start/end -->`` markers and are derived
views — ``--from-design`` rebuilds them from the frontmatter. Everything
outside the markers (style intent, strategy notes, ## Components) is
human/agent-maintained and is never touched by this script.
"""

import argparse
import json
import os
import re
import sys
import tempfile

DEFAULT_ROUNDED = "0px,4px,8px,12px,16px,24px"
DEFAULT_TYPE_SCALE = "12px,14px,16px,20px,24px,32px,40px,48px,64px"
DEFAULT_SPACING = "4px,8px,12px,16px,24px,32px,64px"

COLOR_ROLES = [
    "primary",
    "on_primary",
    "secondary",
    "accent",
    "background",
    "foreground",
    "muted",
    "border",
    "destructive",
    "ring",
    "cta",
]

COMPONENTS_PLACEHOLDER = (
    "组件级规范由 interface-design 在构建产品页面时追加到本节"
    "（每个组件记录测量值与用法，复用 ≥2 次才收录）。"
)

LABEL_KEYS = ("variance_label", "motion_label", "density_label")

# Body blocks regenerated from the frontmatter in --from-design mode.
GENERATED_BLOCKS = ("colors", "typography", "spacing", "rounded")


def _color_keys(colors):
    """Ordered color keys for output: fixed COLOR_ROLES, optional `text`
    (only when it differs from foreground), then any extra keys present in
    the UUPM JSON — user-confirmed additions such as secondary_text or
    dark_* tokens must survive the bridge instead of being dropped."""
    keys = list(COLOR_ROLES)
    if colors.get("text") not in (None, "") and colors.get("text") != colors.get("foreground"):
        keys.append("text")
    keys.extend(k for k in colors if k not in keys and k not in ("text", "notes"))
    return keys


# --------------------------------------------------------------------------
# token naming helpers
# --------------------------------------------------------------------------

def _name_for(kind, idx):
    """Return the token name for the idx-th scale step of the given kind.

    rounded: none (handled by caller), sm/md/lg/xl/2xl/3xl, then 4xl/5xl/...
    type:    xs/sm/base/lg/xl/2xl/3xl/4xl/5xl, then 6xl/7xl/...
    spacing: xs/sm/md/lg/xl/2xl/3xl, then 4xl/5xl/6xl/...
    """
    if kind == "rounded":
        base = ["sm", "md", "lg", "xl", "2xl", "3xl"]
        return base[idx] if idx < len(base) else "%dxl" % (idx - 2)
    if kind == "type":
        base = ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl", "5xl"]
        return base[idx] if idx < len(base) else "%dxl" % (idx - 3)
    base = ["xs", "sm", "md", "lg", "xl", "2xl", "3xl"]
    return base[idx] if idx < len(base) else "%dxl" % (idx - 3)


def parse_comma_list(s):
    """Split a comma-separated CLI argument into a list of stripped tokens."""
    return [x.strip() for x in s.split(",") if x.strip()]


def build_rounded_scale(values):
    """Map rounded values to tokens. 0px -> 'none'; the rest sm/md/lg/xl/2xl/3xl..."""
    seen, unique = set(), []
    for v in values:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    out = {}
    idx = 0
    for v in unique:
        if v in ("0px", "0"):
            out["none"] = v
        else:
            out[_name_for("rounded", idx)] = v
            idx += 1
    if "none" in out:
        out = {**{"none": out["none"]}, **{k: val for k, val in out.items() if k != "none"}}
    return out


def build_type_scale(values):
    """Map font-size values to tokens: xs/sm/base/lg/xl/2xl/3xl/4xl/5xl..."""
    seen, unique = set(), []
    for v in values:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return {_name_for("type", i): v for i, v in enumerate(unique)}


def build_spacing_scale(scale):
    """Spacing from JSON spacing_scale; falls back to the default step list."""
    if not scale:  # None or {}
        values = parse_comma_list(DEFAULT_SPACING)
        return {_name_for("spacing", i): v for i, v in enumerate(values)}
    out = {}
    for name, val in scale.items():
        if val is not None and str(val).strip() != "":
            out[name] = str(val)
    return out


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def _dials_complete(d):
    return d is not None and len(d) == 3 and all(v is not None for v in d)


def validate_design_system(ds, mkt, prod, type_scale):
    """Fail-closed validation for the Phase 0 landing path.

    Returns a list of human-readable problems; empty means the DESIGN.md is
    safe to write. The point: a syntactically valid DESIGN.md full of "TBD"
    is worse than no file, because the workflow treats "DESIGN.md exists" as
    "the spec was confirmed".
    """
    errors = []
    proj = ds.get("project_name")
    if proj is None or not str(proj).strip():
        errors.append("project_name is missing")
    colors = ds.get("colors")
    if not isinstance(colors, dict) or not colors:
        errors.append("colors map is missing")
    else:
        for role in COLOR_ROLES:
            v = colors.get(role)
            if v is None or not str(v).strip():
                errors.append(
                    "colors.%s is missing (UUPM emits 10 roles; confirm and add "
                    "'%s' during Phase 0.3 before landing)" % (role, role))
    typo = ds.get("typography")
    if not isinstance(typo, dict):
        errors.append("typography is missing")
    else:
        if not str(typo.get("heading") or "").strip():
            errors.append("typography.heading font is missing")
        if not str(typo.get("body") or "").strip():
            errors.append("typography.body font is missing")
    if "base" not in type_scale or "2xl" not in type_scale:
        errors.append(
            "type scale needs at least 6 steps (xs..2xl) so body/heading sizes "
            "can be derived; got %d step(s)" % len(type_scale))
    if not _dials_complete(mkt):
        errors.append("marketing dials missing: pass --marketing-dials V,M,D "
                      "(values confirmed in Phase 0.3)")
    if not _dials_complete(prod):
        errors.append("product dials missing: pass --product-dials V,M,D "
                      "or provide JSON dials (variance/motion/density)")
    return errors


def validate_frontmatter_tokens(fm):
    """Validate the parsed DESIGN.md frontmatter for --from-design mode.

    Besides presence, every token value must be a scalar: a nested map where a
    value belongs means a hand edit broke the subset (classic case: an
    unquoted hex like ``cta: #0066FF`` — the ``#`` starts a YAML comment, the
    value vanishes, and the line parses as an empty map).
    """
    errors = []
    for key in ("colors", "rounded", "spacing"):
        m = fm.get(key)
        if not isinstance(m, dict) or not m:
            errors.append("frontmatter.%s is missing or empty" % key)
            continue
        for k, v in m.items():
            if not isinstance(v, str):
                errors.append("frontmatter.%s.%s is not a scalar (unquoted value? "
                              "strings must be quoted, e.g. \"%s: \\\"#0066FF\\\"\")"
                              % (key, k, k))
    typo = fm.get("typography")
    if not isinstance(typo, dict):
        errors.append("frontmatter.typography is missing")
    else:
        for role in ("heading", "body"):
            r = typo.get(role)
            if not isinstance(r, dict) or not str(r.get("fontFamily") or "").strip():
                errors.append("frontmatter.typography.%s.fontFamily is missing" % role)
        scale = typo.get("scale")
        if not isinstance(scale, dict) or not scale:
            errors.append("frontmatter.typography.scale is missing or empty")
        else:
            for k, v in scale.items():
                if not isinstance(v, str):
                    errors.append("frontmatter.typography.scale.%s is not a scalar "
                                  "(unquoted value?)" % k)
    return errors


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------

def _q(v, fallback="TBD"):
    """Quote a scalar for the minimal-YAML frontmatter (double quotes)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return '"%s"' % fallback
    s = str(v).strip().replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return '"%s"' % s


def build_frontmatter(ds, rounded_scale, type_scale, spacing_scale):
    lines = ["---"]

    proj = ds.get("project_name")
    name = ((proj if proj else "TBD") + " Design System")
    lines.append("name: %s" % _q(name))

    colors = ds.get("colors") or {}
    color_keys = _color_keys(colors)
    lines.append("colors:")
    for k in color_keys:
        lines.append("  %s: %s" % (k, _q(colors.get(k))))

    typo = ds.get("typography") or {}
    lines.append("typography:")
    lines.append("  heading:")
    lines.append("    fontFamily: %s" % _q(typo.get("heading")))
    lines.append("    fontSize: %s" % _q(type_scale.get("2xl")))
    lines.append("  body:")
    lines.append("    fontFamily: %s" % _q(typo.get("body")))
    lines.append("    fontSize: %s" % _q(type_scale.get("base")))
    # Font-loading hints are token-adjacent: if the heading/body fonts change
    # in the frontmatter, these go stale unless they live in the SSOT too.
    lines.append("  google_fonts_url: %s" % _q(typo.get("google_fonts_url")))
    lines.append("  css_import: %s" % _q(typo.get("css_import")))
    lines.append("  scale:")
    for tname, tval in type_scale.items():
        lines.append("    %s: %s" % (tname, _q(tval)))

    lines.append("rounded:")
    for rname, rval in rounded_scale.items():
        lines.append("  %s: %s" % (rname, _q(rval)))

    lines.append("spacing:")
    for sname, sval in spacing_scale.items():
        lines.append("  %s: %s" % (sname, _q(sval)))

    lines.append("---")
    return lines


# --------------------------------------------------------------------------
# body
# --------------------------------------------------------------------------

def _s(x, fallback="TBD"):
    """Body scalar: None / '' become the fallback."""
    if x is None:
        return fallback
    if isinstance(x, str) and not x.strip():
        return fallback
    return str(x)


def _cell(v):
    """Markdown table cell with pipe escaping."""
    return str(v).replace("|", "\\|")


def _marker(name, kind):
    """Generated-block boundary marker, e.g. <!-- zedui:generated:colors:start -->."""
    return "<!-- zedui:generated:%s:%s -->" % (name, kind)


def _marked(name, content_lines):
    return [_marker(name, "start")] + content_lines + [_marker(name, "end")]


# --- generated token blocks (derived views of the frontmatter) -------------

def render_colors_block(colors):
    lines = ["| Token | Value |", "|---|---|"]
    for k in _color_keys(colors):
        lines.append("| %s | %s |" % (k, _cell(_s(colors.get(k)))))
    return lines


def render_typography_block(heading_font, body_font, gf_url, css_import, type_scale):
    lines = [
        "**Heading font**: %s" % _s(heading_font),
        "**Body font**: %s" % _s(body_font),
        "**Google Fonts URL**: %s" % _s(gf_url),
        "",
        "```css",
        "%s" % _s(css_import),
        "```",
        "",
        "| Step | Size |",
        "|---|---|",
    ]
    for tname, tval in type_scale.items():
        lines.append("| %s | %s |" % (tname, _cell(tval)))
    return lines


def render_spacing_block(spacing_scale):
    lines = ["**Spacing scale**:", "", "| Token | Value |", "|---|---|"]
    for sname, sval in spacing_scale.items():
        lines.append("| %s | %s |" % (sname, _cell(sval)))
    return lines


def render_rounded_block(rounded_scale):
    lines = ["| Token | Radius |", "|---|---|"]
    for rname, rval in rounded_scale.items():
        lines.append("| %s | %s |" % (rname, _cell(rval)))
    return lines


def splice_generated_blocks(text, blocks):
    """Replace the content of each marked generated block in the DESIGN.md body.

    Only the text between the start/end markers is touched; everything else —
    including ## Components and all strategy prose — is preserved byte-for-byte.
    Raises ValueError when a marker pair is missing (pre-0.4 format).
    """
    lines = text.splitlines()
    for name in GENERATED_BLOCKS:
        if name not in blocks:
            continue
        start_m = _marker(name, "start")
        end_m = _marker(name, "end")
        try:
            si = lines.index(start_m)
            ei = lines.index(end_m)
        except ValueError:
            raise ValueError(
                "generated block markers for '%s' not found in the DESIGN.md body. "
                "This file predates the zedui-design-schema-v1 marker format: "
                "regenerate it from the UUPM JSON with --force (then edit the "
                "frontmatter only), or add the marker pairs manually." % name)
        if ei <= si:
            raise ValueError("generated block '%s' end marker precedes start marker" % name)
        lines[si + 1:ei] = blocks[name]
    return "\n".join(lines) + "\n"


# --- dials ------------------------------------------------------------------

def parse_dials(s):
    """Parse 'V,M,D' into three integers in the range 1..10."""
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 3 or any(not p for p in parts):
        raise argparse.ArgumentTypeError("dials must be three integers V,M,D (e.g. 3,4,8)")
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        raise argparse.ArgumentTypeError("dials values must be integers (e.g. 3,4,8)")
    for v in vals:
        if v < 1 or v > 10:
            raise argparse.ArgumentTypeError("dials values must be between 1 and 10")
    return vals


def _norm_int(x):
    try:
        return int(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def resolve_dials(dials, mkt_flag, prod_flag):
    """Return (marketing dials, product dials, product labels).

    marketing dials come only from the CLI flag; product dials come from the
    CLI flag, or from JSON `dials` when the flag is absent. JSON-fallback
    values get the same 1..10 range check as the CLI path (raises ValueError).
    """
    prod_labels = {}
    if prod_flag is None and isinstance(dials, dict):
        if dials.get("variance") is not None or dials.get("motion") is not None or dials.get("density") is not None:
            prod_flag = [
                _norm_int(dials.get("variance")),
                _norm_int(dials.get("motion")),
                _norm_int(dials.get("density")),
            ]
            for v in prod_flag:
                if v is not None and not (1 <= v <= 10):
                    raise ValueError("JSON dials values must be between 1 and 10, got %r" % v)
            prod_labels = {
                "variance_label": dials.get("variance_label"),
                "motion_label": dials.get("motion_label"),
                "density_label": dials.get("density_label"),
            }
    return mkt_flag, prod_flag, prod_labels


def dial_row(dials, labels=None):
    labels = labels or {}
    if dials is None:
        return "TBD", "TBD", "TBD"
    cells = []
    for i, v in enumerate(dials):
        if v is None:
            cells.append("TBD")
        else:
            lbl = labels.get(LABEL_KEYS[i])
            cells.append("%s (%s)" % (v, lbl) if lbl else str(v))
    return tuple(cells)


def split_items(text):
    """Split a multi-item string into a list (' + ' or newline separated)."""
    if text is None:
        return []
    if isinstance(text, list):
        return [str(x).strip() for x in text if str(x).strip()]
    text = str(text).strip()
    for sep in ("\n", " + "):
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        if len(parts) > 1:
            return parts
    return [text] if text else []


def build_body(ds, rounded_scale, type_scale, spacing_scale, mkt, prod, prod_labels):
    style = ds.get("style") or {}
    pattern = ds.get("pattern") or {}
    colors = ds.get("colors") or {}
    typo = ds.get("typography") or {}
    sections = []

    # ---- 1. Overview ----
    mkt_cells = dial_row(mkt)
    prod_cells = dial_row(prod, prod_labels)
    overview = [
        "## Overview",
        "",
        "**Project**: %s" % _s(ds.get("project_name")),
        "**Category**: %s" % _s(ds.get("category")),
        "**Style**: %s" % _s(style.get("name")),
        "**Keywords**: %s" % _s(style.get("keywords")),
        "**Best for**: %s" % _s(style.get("best_for")),
        "**Light mode**: %s" % _s(style.get("light_mode")),
        "**Dark mode**: %s" % _s(style.get("dark_mode")),
        "**Performance**: %s" % _s(style.get("performance")),
        "**Accessibility**: %s" % _s(style.get("accessibility")),
        "",
        "| Dials | Variance | Motion | Density |",
        "|---|---|---|---|",
        "| Marketing | %s | %s | %s |" % tuple(_cell(c) for c in mkt_cells),
        "| Product | %s | %s | %s |" % tuple(_cell(c) for c in prod_cells),
    ]
    sections.append("\n".join(overview))

    # ---- 2. Colors (token table is a generated block) ----
    color_lines = ["## Colors", ""]
    color_lines += _marked("colors", render_colors_block(colors))
    color_lines.append("")
    color_lines.append("**Color strategy**: %s" % _s(pattern.get("color_strategy", ds.get("color_strategy"))))
    color_lines.append("**Notes**: %s" % _s(colors.get("notes")))
    sections.append("\n".join(color_lines))

    # ---- 3. Typography (fonts/URL/import/scale are a generated block) ----
    typo_lines = ["## Typography", ""]
    typo_lines += _marked("typography", render_typography_block(
        typo.get("heading"), typo.get("body"),
        typo.get("google_fonts_url"), typo.get("css_import"),
        type_scale))
    typo_lines.append("")
    typo_lines.append("**Mood**: %s" % _s(typo.get("mood")))
    typo_lines.append("**Best for**: %s" % _s(typo.get("best_for")))
    sections.append("\n".join(typo_lines))

    # ---- 4. Layout (spacing table is a generated block) ----
    layout_lines = [
        "## Layout",
        "",
        "**Pattern**: %s" % _s(pattern.get("name")),
        "**Sections**: %s" % _s(pattern.get("sections")),
        "**CTA placement**: %s" % _s(pattern.get("cta_placement")),
        "**Conversion**: %s" % _s(pattern.get("conversion")),
        "",
    ]
    layout_lines += _marked("spacing", render_spacing_block(spacing_scale))
    sections.append("\n".join(layout_lines))

    # ---- 5. Elevation & Depth ----
    sections.append(
        "\n".join([
            "## Elevation & Depth",
            "",
            "**Effects**: %s" % _s(style.get("effects")),
            "**Key effects**: %s" % _s(ds.get("key_effects")),
        ])
    )

    # ---- 6. Shapes (radius table is a generated block) ----
    shape_lines = ["## Shapes", ""]
    shape_lines += _marked("rounded", render_rounded_block(rounded_scale))
    sections.append("\n".join(shape_lines))

    # ---- 7. Components ----
    sections.append("\n".join(["## Components", "", COMPONENTS_PLACEHOLDER]))

    # ---- 8. Do's and Don'ts ----
    dd = ["## Do's and Don'ts", ""]
    anti = split_items(ds.get("anti_patterns"))
    dd.append("**Don't**:")
    if anti:
        dd.extend("- %s" % item for item in anti)
    else:
        dd.append("- TBD")
    dd.append("")
    dd.append("**Conditional rules** (decision_rules):")
    dr = ds.get("decision_rules")
    if isinstance(dr, dict) and dr:
        dd.extend("- %s: %s" % (k, v) for k, v in dr.items())
    elif dr:
        dd.append("- %s" % _s(dr))
    else:
        dd.append("- TBD")
    dd.append("")
    dd.append("**Accessibility**: %s" % _s(style.get("accessibility")))
    ms = ds.get("motion_snippet")
    if isinstance(ms, dict) and any(ms.get(k) not in (None, "") for k in ("Category", "Duration", "Easing", "Do", "Don't", "Performance Notes")):
        dd.append("")
        dd.append("**Motion snippet**:")
        for k in ("Category", "Duration", "Easing", "Do", "Don't", "Performance Notes"):
            if ms.get(k) not in (None, ""):
                dd.append("- **%s**: %s" % (k, ms[k]))
    sections.append("\n".join(dd))

    return "\n\n".join(sections)


# --------------------------------------------------------------------------
# tokens.css generation (DESIGN.md frontmatter -> CSS custom properties)
# --------------------------------------------------------------------------

_CSS_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _css_name_part(key):
    """Validate a token key and normalize it (underscores -> hyphens).

    Raises ValueError on keys that cannot become a valid CSS custom property
    (e.g. names containing spaces) instead of silently emitting broken CSS.
    """
    k = str(key).strip()
    if not _CSS_KEY_RE.match(k):
        raise ValueError("invalid token key for a CSS custom property: %r" % key)
    return k.replace("_", "-")


def _css_var_name(key):
    """frontmatter key -> full CSS var name ("--" + normalized key)."""
    return "--" + _css_name_part(key)


def _css_value(v):
    """Validate a token value before it is interpolated into CSS."""
    s = str(v).strip()
    if not s:
        raise ValueError("empty token value")
    if any(c in s for c in (";", "{", "}")) or "\n" in s or "\r" in s:
        raise ValueError("token value is not a single CSS value: %r" % v)
    return s


def build_tokens_css(colors, heading_font, body_font, type_scale, rounded_scale,
                     spacing_scale, source_desc):
    """Render the token layer as CSS custom properties on :root.

    Pure derivation: every value comes from the DESIGN.md frontmatter maps;
    nothing is invented here. Empty/TBD values are skipped. Raises ValueError
    on keys/values that would produce invalid CSS.
    """
    def _ok(v):
        return v is not None and str(v).strip() not in ("", "TBD")

    lines = [
        "/* -----------------------------------------------------------------------",
        " * GENERATED FILE — DO NOT EDIT BY HAND.",
        " * Single source of truth: DESIGN.md frontmatter (%s)." % os.path.basename(source_desc),
        " * Regenerate after any frontmatter change:",
        " *   uupm_to_design.py --from-design DESIGN.md --tokens-css <this file>",
        " * Usage invariant: component code references these variables; literal",
        " * values belong only in the token definition layer (they are drift).",
        " * ----------------------------------------------------------------------- */",
        ":root {",
    ]
    for k in _color_keys(colors):
        v = colors.get(k)
        if _ok(v):
            lines.append("  %s: %s;" % (_css_var_name(k), _css_value(v)))
    if _ok(heading_font):
        lines.append("  --font-heading: %s;" % _css_value(heading_font))
    if _ok(body_font):
        lines.append("  --font-body: %s;" % _css_value(body_font))
    for tname, tval in type_scale.items():
        if _ok(tval):
            lines.append("  --text-%s: %s;" % (_css_name_part(tname), _css_value(tval)))
    for rname, rval in rounded_scale.items():
        if _ok(rval):
            lines.append("  --radius-%s: %s;" % (_css_name_part(rname), _css_value(rval)))
    for sname, sval in spacing_scale.items():
        if _ok(sval):
            lines.append("  --space-%s: %s;" % (_css_name_part(sname), _css_value(sval)))
    lines.append("}")
    return "\n".join(lines) + "\n"


def _unquote(val):
    """Unquote a quoted scalar from the minimal-YAML frontmatter.

    Strips one matching pair of double or single quotes. Values and keys share
    this handling, so a quoted key like ``"20"`` cannot leak its quotes into a
    generated CSS variable name.
    """
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        quote = val[0]
        inner = val[1:-1]
        if quote == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        else:
            inner = inner.replace("\\'", "'").replace("\\\\", "\\")
        return inner
    return val


def _find_top_level_colon(s):
    """Index of the first ':' outside single/double quotes, or -1.

    Mirrors the behavior of impeccable's findTopLevelColon() so both tools
    read the same frontmatter the same way (e.g. a quoted key "20": "16px"
    or a value containing a colon inside quotes).
    """
    in_quote = None
    i = 0
    while i < len(s):
        ch = s[i]
        if in_quote is not None:
            if ch == "\\" and i + 1 < len(s):
                i += 2
                continue
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            in_quote = ch
        elif ch == ":":
            return i
        i += 1
    return -1


def _strip_inline_comment(s):
    """Strip a trailing `` # comment`` that sits outside quotes.

    A '#' inside quotes, or one not preceded by whitespace, is part of the
    value (hex colors like #0066FF must survive).
    """
    in_quote = None
    i = 0
    while i < len(s):
        ch = s[i]
        if in_quote is not None:
            if ch == "\\" and i + 1 < len(s):
                i += 2
                continue
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            in_quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in (" ", "\t")):
            return s[:i].rstrip()
        i += 1
    return s


def parse_design_frontmatter(text):
    """Parse the restricted-YAML frontmatter this script emits (nested maps,
    2-space indents, double- or single-quoted scalars, no lists) into nested
    dicts.

    Key/value splitting follows the same rules as impeccable's parser
    (top-level colon outside quotes, inline comments outside quotes), so a
    file readable by one tool is readable by the other.

    Raises ValueError on anything outside the subset.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block (expected '---' on line 1)")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("frontmatter block not closed (missing second '---')")
    root = {}
    stack = [(-1, root)]  # (indent, container)
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.lstrip() != raw and not raw.startswith(" "):
            raise ValueError("tabs are not supported in frontmatter: %r" % raw)
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        colon = _find_top_level_colon(stripped)
        if colon == -1:
            raise ValueError("unsupported frontmatter line: %r" % raw)
        key = _unquote(stripped[:colon])
        val = _strip_inline_comment(stripped[colon + 1:]).strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        if indent <= stack[-1][0]:
            raise ValueError("bad indentation near line: %r" % raw)
        parent = stack[-1][1]
        if val == "":
            child = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _unquote(val)
    return root


def write_atomic(path, content):
    """Write content to path atomically (temp file + os.replace).

    Creates the parent directory on demand, so a --tokens-css target inside a
    not-yet-existing directory succeeds instead of raising a bare traceback.
    A crash mid-write never leaves a truncated file behind.
    """
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".zedui-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def build_document(ds, rounded_scale, type_scale, spacing_scale, mkt, prod, prod_labels):
    fm = "\n".join(build_frontmatter(ds, rounded_scale, type_scale, spacing_scale))
    body = build_body(ds, rounded_scale, type_scale, spacing_scale, mkt, prod, prod_labels)
    return fm + "\n" + body + "\n"


def _fail(msg):
    print("error: %s" % msg, file=sys.stderr)
    sys.exit(1)


def _fail_list(header, errors):
    print("error: %s" % header, file=sys.stderr)
    for e in errors:
        print("  - %s" % e, file=sys.stderr)
    sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="uupm_to_design.py",
        description=(
            "Convert UI-UX-Pro-Max (uipro) design-system JSON "
            "(search.py --design-system --json) into google-labs DESIGN.md. "
            "Stdlib only."
        ),
    )
    parser.add_argument("input", metavar="INPUT", nargs="?",
                        help="path to the design-system JSON, or '-' to read from stdin")
    parser.add_argument("-o", "--output", default=None,
                        help="output markdown path (default: ./DESIGN.md)")
    parser.add_argument("--from-design", default=None, metavar="DESIGN_MD",
                        help="read tokens from an existing DESIGN.md frontmatter instead of "
                             "a UUPM JSON; regenerates the marked token blocks in the body "
                             "AND the token CSS file; requires --tokens-css")
    parser.add_argument("--rounded", default=DEFAULT_ROUNDED, metavar="LIST",
                        help="comma-separated corner-radius steps (default: %s)" % DEFAULT_ROUNDED)
    parser.add_argument("--type-scale", default=DEFAULT_TYPE_SCALE, metavar="LIST",
                        help="comma-separated font-size steps, at least 6 (default: %s)" % DEFAULT_TYPE_SCALE)
    parser.add_argument("--marketing-dials", type=parse_dials, default=None, metavar="V,M,D",
                        help="marketing dials: variance,motion,density (1-10 each)")
    parser.add_argument("--product-dials", type=parse_dials, default=None, metavar="V,M,D",
                        help="product dials: variance,motion,density (1-10 each)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite the output file if it already exists")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="accept missing fields/dials and write TBD placeholders "
                             "(default: fail closed on incomplete input)")
    parser.add_argument("--tokens-css", default=None, metavar="PATH",
                        help="also emit a generated CSS-custom-properties token file "
                             "(always overwritten, never hand-edited)")
    args = parser.parse_args(argv)

    # ---- --from-design mode: DESIGN.md frontmatter -> body blocks + tokens.css ----
    if args.from_design is not None:
        if not args.tokens_css:
            _fail("--from-design requires --tokens-css")
        if args.output is not None:
            _fail("--from-design re-syncs the DESIGN.md in place; -o/--output is not supported")
        if args.input is not None:
            _fail("--from-design reads DESIGN.md instead of a UUPM JSON; "
                  "positional INPUT must be omitted")
        try:
            with open(args.from_design, "r", encoding="utf-8") as fh:
                design_text = fh.read()
        except OSError as e:
            _fail("cannot read DESIGN.md: %s" % e)
        try:
            fm = parse_design_frontmatter(design_text)
        except ValueError as e:
            _fail("cannot parse frontmatter: %s" % e)
        errors = validate_frontmatter_tokens(fm)
        if errors:
            _fail_list("frontmatter is incomplete; fix these before re-syncing", errors)
        typo = fm["typography"]
        try:
            blocks = {
                "colors": render_colors_block(fm["colors"]),
                "typography": render_typography_block(
                    (typo.get("heading") or {}).get("fontFamily"),
                    (typo.get("body") or {}).get("fontFamily"),
                    typo.get("google_fonts_url"),
                    typo.get("css_import"),
                    typo["scale"]),
                "spacing": render_spacing_block(fm["spacing"]),
                "rounded": render_rounded_block(fm["rounded"]),
            }
            new_text = splice_generated_blocks(design_text, blocks)
            css = build_tokens_css(
                fm["colors"],
                (typo.get("heading") or {}).get("fontFamily"),
                (typo.get("body") or {}).get("fontFamily"),
                typo["scale"],
                fm["rounded"],
                fm["spacing"],
                args.from_design,
            )
        except ValueError as e:
            _fail(str(e))
        # Both outputs are fully built before anything is written; each write
        # is atomic, so a failure here can never leave a truncated file.
        if new_text != design_text:
            write_atomic(args.from_design, new_text)
        write_atomic(args.tokens_css, css)
        return

    if args.output is None:
        args.output = "DESIGN.md"

    if args.input is None:
        _fail("INPUT is required (or use --from-design)")

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as e:
            _fail("cannot read input: %s" % e)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        _fail("invalid JSON: %s" % e)

    if isinstance(data, dict) and "design_system" in data:
        ds = data["design_system"]
    elif isinstance(data, dict):
        ds = data
    else:
        _fail("expected a JSON object, got %s" % type(data).__name__)
    if not isinstance(ds, dict):
        _fail("design_system must be a JSON object")

    rounded_values = parse_comma_list(args.rounded) or parse_comma_list(DEFAULT_ROUNDED)
    type_values = parse_comma_list(args.type_scale) or parse_comma_list(DEFAULT_TYPE_SCALE)
    rounded_scale = build_rounded_scale(rounded_values)
    type_scale = build_type_scale(type_values)
    spacing_scale = build_spacing_scale(ds.get("spacing_scale"))

    try:
        mkt, prod, prod_labels = resolve_dials(ds.get("dials"), args.marketing_dials, args.product_dials)
    except ValueError as e:
        _fail(str(e))

    if not args.allow_incomplete:
        errors = validate_design_system(ds, mkt, prod, type_scale)
        if errors:
            _fail_list("incomplete design system (re-run with --allow-incomplete to "
                       "land TBD placeholders anyway)", errors)

    try:
        document = build_document(ds, rounded_scale, type_scale, spacing_scale, mkt, prod, prod_labels)
        css = None
        if args.tokens_css:
            typo = ds.get("typography") or {}
            css = build_tokens_css(
                ds.get("colors") or {},
                typo.get("heading"),
                typo.get("body"),
                type_scale,
                rounded_scale,
                spacing_scale,
                args.output,
            )
    except ValueError as e:
        _fail(str(e))

    if os.path.exists(args.output) and not args.force:
        _fail("output file already exists: %s (use --force to overwrite)" % args.output)

    # Everything is built and validated above; writes are atomic per file.
    write_atomic(args.output, document)
    if css is not None:
        write_atomic(args.tokens_css, css)


if __name__ == "__main__":
    main()
