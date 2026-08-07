#!/usr/bin/env python3
"""uupm_to_design.py — Convert UI-UX-Pro-Max (uipro) design-system JSON to google-labs DESIGN.md.

The input is the JSON emitted by uipro's ``search.py --design-system --json``
(the outer wrapper is fixed to ``{"design_system": {...}}``). The conversion is
mechanical: JSON in, fixed-format markdown out.

Pure standard library (stdlib only).

Usage:
    uupm_to_design.py INPUT [-o OUTPUT] [--rounded "0px,4px,8px,12px,16px,24px"]
                            [--type-scale "12px,14px,16px,20px,24px,32px,40px,48px,64px"]
                            [--marketing-dials V,M,D] [--product-dials V,M,D] [--force]

    INPUT    path to the design-system JSON, or ``-`` to read from stdin.
    -o       output markdown path (default: ./DESIGN.md); refuses to overwrite
             an existing file unless --force is given (exit code 1).
"""

import argparse
import json
import os
import sys

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
        out = {"none": out["none"]} | {k: val for k, val in out.items() if k != "none"}
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
    color_keys = list(COLOR_ROLES)
    if colors.get("text") not in (None, "") and colors.get("text") != colors.get("foreground"):
        color_keys.append("text")
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
    CLI flag, or from JSON `dials` when the flag is absent.
    """
    prod_labels = {}
    if prod_flag is None and isinstance(dials, dict):
        if dials.get("variance") is not None or dials.get("motion") is not None or dials.get("density") is not None:
            prod_flag = [
                _norm_int(dials.get("variance")),
                _norm_int(dials.get("motion")),
                _norm_int(dials.get("density")),
            ]
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

    # ---- 2. Colors ----
    color_keys = list(COLOR_ROLES)
    if colors.get("text") not in (None, "") and colors.get("text") != colors.get("foreground"):
        color_keys.append("text")
    color_lines = ["## Colors", "", "| Token | Value |", "|---|---|"]
    for k in color_keys:
        color_lines.append("| %s | %s |" % (k, _cell(_s(colors.get(k)))))
    color_lines.append("")
    color_lines.append("**Color strategy**: %s" % _s(pattern.get("color_strategy", ds.get("color_strategy"))))
    color_lines.append("**Notes**: %s" % _s(colors.get("notes")))
    sections.append("\n".join(color_lines))

    # ---- 3. Typography ----
    typo_lines = [
        "## Typography",
        "",
        "**Heading font**: %s" % _s(typo.get("heading")),
        "**Body font**: %s" % _s(typo.get("body")),
        "**Mood**: %s" % _s(typo.get("mood")),
        "**Best for**: %s" % _s(typo.get("best_for")),
        "**Google Fonts URL**: %s" % _s(typo.get("google_fonts_url")),
        "",
        "```css",
        "%s" % _s(typo.get("css_import")),
        "```",
        "",
        "| Step | Size |",
        "|---|---|",
    ]
    for tname, tval in type_scale.items():
        typo_lines.append("| %s | %s |" % (tname, _cell(tval)))
    sections.append("\n".join(typo_lines))

    # ---- 4. Layout ----
    layout_lines = [
        "## Layout",
        "",
        "**Pattern**: %s" % _s(pattern.get("name")),
        "**Sections**: %s" % _s(pattern.get("sections")),
        "**CTA placement**: %s" % _s(pattern.get("cta_placement")),
        "**Conversion**: %s" % _s(pattern.get("conversion")),
        "",
        "**Spacing scale**:",
        "",
        "| Token | Value |",
        "|---|---|",
    ]
    for sname, sval in spacing_scale.items():
        layout_lines.append("| %s | %s |" % (sname, _cell(sval)))
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

    # ---- 6. Shapes ----
    shape_lines = ["## Shapes", "", "| Token | Radius |", "|---|---|"]
    for rname, rval in rounded_scale.items():
        shape_lines.append("| %s | %s |" % (rname, _cell(rval)))
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
# main
# --------------------------------------------------------------------------

def build_document(ds, rounded_scale, type_scale, spacing_scale, mkt, prod, prod_labels):
    fm = "\n".join(build_frontmatter(ds, rounded_scale, type_scale, spacing_scale))
    body = build_body(ds, rounded_scale, type_scale, spacing_scale, mkt, prod, prod_labels)
    return fm + "\n" + body + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="uupm_to_design.py",
        description=(
            "Convert UI-UX-Pro-Max (uipro) design-system JSON "
            "(search.py --design-system --json) into google-labs DESIGN.md. "
            "Stdlib only."
        ),
    )
    parser.add_argument("input", metavar="INPUT",
                        help="path to the design-system JSON, or '-' to read from stdin")
    parser.add_argument("-o", "--output", default="DESIGN.md",
                        help="output markdown path (default: ./DESIGN.md)")
    parser.add_argument("--rounded", default=DEFAULT_ROUNDED, metavar="LIST",
                        help="comma-separated corner-radius steps (default: %s)" % DEFAULT_ROUNDED)
    parser.add_argument("--type-scale", default=DEFAULT_TYPE_SCALE, metavar="LIST",
                        help="comma-separated font-size steps (default: %s)" % DEFAULT_TYPE_SCALE)
    parser.add_argument("--marketing-dials", type=parse_dials, default=None, metavar="V,M,D",
                        help="marketing dials: variance,motion,density (1-10 each)")
    parser.add_argument("--product-dials", type=parse_dials, default=None, metavar="V,M,D",
                        help="product dials: variance,motion,density (1-10 each)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite the output file if it already exists")
    args = parser.parse_args(argv)

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as e:
            print("error: cannot read input: %s" % e, file=sys.stderr)
            sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print("error: invalid JSON: %s" % e, file=sys.stderr)
        sys.exit(1)

    if isinstance(data, dict) and "design_system" in data:
        ds = data["design_system"]
    elif isinstance(data, dict):
        ds = data
    else:
        print("error: expected a JSON object, got %s" % type(data).__name__, file=sys.stderr)
        sys.exit(1)
    if not isinstance(ds, dict):
        print("error: design_system must be a JSON object", file=sys.stderr)
        sys.exit(1)

    rounded_values = parse_comma_list(args.rounded) or parse_comma_list(DEFAULT_ROUNDED)
    type_values = parse_comma_list(args.type_scale) or parse_comma_list(DEFAULT_TYPE_SCALE)
    rounded_scale = build_rounded_scale(rounded_values)
    type_scale = build_type_scale(type_values)
    spacing_scale = build_spacing_scale(ds.get("spacing_scale"))

    mkt, prod, prod_labels = resolve_dials(ds.get("dials"), args.marketing_dials, args.product_dials)
    document = build_document(ds, rounded_scale, type_scale, spacing_scale, mkt, prod, prod_labels)

    if os.path.exists(args.output) and not args.force:
        print("error: output file already exists: %s (use --force to overwrite)" % args.output,
              file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(document)


if __name__ == "__main__":
    main()
