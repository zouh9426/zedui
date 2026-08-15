#!/usr/bin/env python3
"""token_lint.py — ZedUI spacing-literal linter (hard rule 6 fallback).

Impeccable's design-system detector compares font/color/radius/font-size
against DESIGN.md, but NOT spacing: ``padding: 17px`` is never flagged
upstream. This script closes that gap. It scans CSS declarations of
spacing-like properties — margin/padding/gap (physical *and* logical
directional forms) — and reports any value that carries a length literal
(17px, 1.5rem, 50%, ...) outside a var() reference. Positioning properties
(inset and its logical forms, top/right/bottom/left) are also scanned, but
only for ABSOLUTE length literals: percentages there are almost always
component-internal placement (``top: 50%`` centering, decorative glows at
``top: -20%``), not spacing rhythm — flagging them produced forced, worse
rewrites (measured in the 2026-08 A/B pilot). ``padding: 5%`` on a spacing
property is still flagged.
``var(...)`` references are stripped whole (nested parens handled with a
simple balance count) before the remaining value is tokenized, so
``padding: var(--space-sm) 17px`` and ``gap: calc(var(--space-md) + 3px)``
are caught while ``gap: calc(var(--space-md) * 2)`` stays clean. Bare
non-zero numbers (React inline styles such as ``style={{ padding: 17 }}``)
are findings too; ``0`` and CSS keywords stay exempt. Tailwind
arbitrary-value spacing classes (``p-[17px]``, ``mt-[-8px]``, ``-m-[4px]``,
``inset-x-[4px]``, ...) are flagged; non-spacing arbitrary classes
(``w-[300px]``, ``text-[17px]``, ``leading-[1.1]``, ``min-h-[100dvh]``,
``bg-[#fff]``, ...) and standard staircase classes (``p-4``, ``mt-2``) are
not.

Inline exemption: a line whose raw text contains ``token-lint-ignore``
(typically in a trailing comment, e.g. ``top: -20%; /* token-lint-ignore:
decorative glow placement */``) is skipped entirely — this is the mechanical
outlet for dispositioned findings, so the gate's exit code stays meaningful
(0 = clean, 1 = undispositioned findings). Exemptions are visible in source
and auditable by grep, unlike out-of-band config.

The token definition layer is exempt: a file whose header carries the
"GENERATED FILE — DO NOT EDIT BY HAND" marker (tokens.css and friends) is
skipped entirely; --exclude accepts explicit globs such as 'tokens.css'.
Directory walks prune DEFAULT_PRUNE_DIRS (node_modules, .next, dist, build,
coverage, vendor, out, .nuxt, .cache, __pycache__) in addition to .git.

Pure standard library (stdlib only). Python 3.8+.

Usage:
    token_lint.py TARGET... [--ext .css,.scss,.less,.html,.vue,.jsx,.tsx]
                            [--exclude GLOB...]

    TARGET     a file or a directory; directories are walked recursively
               (symlinks followed, cycles guarded).
    --ext      comma-separated extensions scanned inside directories
               (default: the list above). Explicitly listed files are always
               linted regardless of extension.
    --exclude  glob pattern(s); a file matching any pattern (against the
               absolute path, the scan-root-relative path or the basename)
               is skipped.

Exit codes:
    0  clean — no spacing-literal findings
    1  one or more findings
    2  usage error (bad arguments / target not found / unreadable input
       files — a gate that could not read its input never reports OK)
"""

import argparse
import fnmatch
import os
import re
import sys

DEFAULT_EXTS = [".css", ".scss", ".less", ".html", ".vue", ".jsx", ".tsx"]

# Directories pruned during recursive walks, in addition to .git. Only
# basenames are compared, so these names never match user source dirs.
DEFAULT_PRUNE_DIRS = frozenset([
    ".git",
    "node_modules", ".next", "dist", "build", "coverage",
    "vendor", "out", ".nuxt", ".cache", "__pycache__",
])

SPACING_PROPERTIES = frozenset([
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-inline", "margin-inline-start", "margin-inline-end",
    "margin-block", "margin-block-start", "margin-block-end",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "padding-inline", "padding-inline-start", "padding-inline-end",
    "padding-block", "padding-block-start", "padding-block-end",
    "gap", "row-gap", "column-gap",
])

# Positioning properties: scanned too, but only absolute length literals are
# findings — percentages here are placement, not spacing rhythm.
POSITION_PROPERTIES = frozenset([
    "inset", "inset-top", "inset-right", "inset-bottom", "inset-left",
    "inset-inline", "inset-inline-start", "inset-inline-end",
    "inset-block", "inset-block-start", "inset-block-end",
    "top", "right", "bottom", "left",
])

# A line carrying this marker in its raw text is skipped entirely (inline
# exemption for dispositioned findings; auditable by grep).
IGNORE_MARKER = "token-lint-ignore"

# A length literal: optional sign, integer or decimal digits, a CSS unit
# (modern viewport units included: dvh/dvw/svh/svw/lvh/lvw/vmin/vmax).
# Group 1 captures the numeric part (so zero literals can be exempted).
_LENGTH_BODY = (r"(?<![\w.-])(-?(?:\d+(?:\.\d*)?|\.\d+))"
                r"(?:px|rem|em|dvh|dvw|svh|svw|lvh|lvw|vmin|vmax|vh|vw")
LENGTH_LITERAL_RE = re.compile(_LENGTH_BODY + r"|%)", re.IGNORECASE)
# Positioning-property variant: no % — percentages there are placement.
LENGTH_LITERAL_NO_PCT_RE = re.compile(_LENGTH_BODY + r")", re.IGNORECASE)

# A bare number with no unit at all (React inline styles: `padding: 17`).
BARE_NUMBER_RE = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)")

# Whole-component exemptions: zero lengths and CSS keywords.
ZERO_AND_KEYWORD_EXEMPT = frozenset([
    "0", "0px", "0%", "0em", "0rem", "0vh", "0vw",
    "auto", "inherit", "initial", "unset", "normal",
])

# Header marker of generated token files (see uupm_to_design.py build_tokens_css).
GENERATED_HEADER_RE = re.compile(r"GENERATED FILE[^\n]{0,40}DO NOT EDIT BY HAND")

# A CSS declaration on one line. The value capture stops at ; { } , or a
# newline, so the last declaration of a block and multiple JSX style props on
# one line are each scanned independently. Property names are broad here; the
# spacing-property filter below decides what actually counts.
DECL_RE = re.compile(r"([A-Za-z-]+)\s*:\s*([^;{}\r\n,]+)")

# Tailwind arbitrary-value spacing prefixes. Only these are flagged when they
# appear as `prefix-[length-literal]`. Non-spacing prefixes (w-, h-, text-,
# leading-, min-h-, max-w-, bg-, ...) are intentionally absent so arbitrary
# classes built on them pass through untouched.
TAILWIND_SPACING_PREFIXES = (
    "px", "py", "pt", "pr", "pb", "pl", "p",
    "mx", "my", "mt", "mr", "mb", "ml", "m",
    "gap-x", "gap-y", "gap",
    "space-x", "space-y",
    "inset-x", "inset-y", "inset",
    "top", "right", "bottom", "left",
    "scroll-mx", "scroll-my", "scroll-mt", "scroll-mr",
    "scroll-mb", "scroll-ml", "scroll-m",
    "scroll-px", "scroll-py", "scroll-pt", "scroll-pr",
    "scroll-pb", "scroll-pl", "scroll-p",
)

ARBITRARY_SPACING_RE = re.compile(
    r"(?<![\w-])-?(?:%s)-\[([^\[\]]*)\]"
    % "|".join(sorted(TAILWIND_SPACING_PREFIXES, key=len, reverse=True)),
    re.IGNORECASE,
)


def _strip_var_refs(value):
    """Return *value* with every ``var(...)`` reference removed.

    Nested parentheses (``var(--a, var(--b))``) are handled with a simple
    open-paren balance count; the match is case-insensitive (``VAR(...)`` is
    legal CSS). An unterminated ``var(`` consumes the rest of the value.
    """
    out = []
    i = 0
    n = len(value)
    low = value.lower()
    while True:
        j = low.find("var(", i)
        if j == -1:
            out.append(value[i:])
            return "".join(out)
        out.append(value[i:j])
        depth = 1
        k = j + 4
        while k < n and depth:
            if low[k] == "(":
                depth += 1
            elif low[k] == ")":
                depth -= 1
            k += 1
        i = k


def _strip_quotes(comp):
    """Remove a matched pair of surrounding quotes (JSX ``"17"`` -> ``17``)."""
    if len(comp) >= 2 and comp[0] in "\"'" and comp[-1] == comp[0]:
        return comp[1:-1]
    return comp


def _literal_is_zero(match):
    try:
        return float(match.group(1)) == 0
    except ValueError:
        return False


def _has_nonzero_length_literal(comp, pattern=LENGTH_LITERAL_RE):
    """True when *comp* contains a length literal whose value is not zero."""
    for m in pattern.finditer(comp):
        if not _literal_is_zero(m):
            return True
    return False


def _is_nonzero_bare_number(comp):
    """True when the whole token is a bare number that is not zero."""
    if not BARE_NUMBER_RE.fullmatch(comp):
        return False
    try:
        return float(comp) != 0
    except ValueError:
        return False


def _token_is_bad(comp, pattern=LENGTH_LITERAL_RE):
    """True when a single value token carries a flaggable literal."""
    comp = _strip_quotes(comp)
    if not comp:
        return False
    if comp in ZERO_AND_KEYWORD_EXEMPT:
        return False
    if _is_nonzero_bare_number(comp):
        return True
    return _has_nonzero_length_literal(comp, pattern)


def _has_bad_literal(value, pattern=LENGTH_LITERAL_RE):
    """True when the value carries a non-exempt spacing length literal.

    var(...) references are stripped whole first, so a pure-token value like
    ``var(--space-md)`` or ``calc(var(--space-md) * 2)`` is clean, while
    ``calc(var(--space-md) + 3px)`` still trips on the ``3px``.
    """
    stripped = _strip_var_refs(value)
    for comp in re.split(r"[\s,]+", stripped.strip()):
        if not comp:
            continue
        if _token_is_bad(comp, pattern):
            return True
    return False


def _iter_clean_lines(text):
    """Yield (lineno, line) pairs with /* */ block comments removed."""
    in_comment = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw
        if in_comment:
            end = line.find("*/")
            if end == -1:
                continue
            line = line[end + 2:]
            in_comment = False
        while True:
            start = line.find("/*")
            if start == -1:
                break
            end = line.find("*/", start + 2)
            if end == -1:
                line = line[:start]
                in_comment = True
                break
            line = line[:start] + line[end + 2:]
        yield lineno, line


def _tailwind_findings(line):
    """Yield Tailwind arbitrary-value spacing classes found on one line.

    Every whitespace token of the comment-stripped line is checked, which
    covers class="..." and className="..." attributes, JSX template strings
    and dynamic class expressions alike. Only the spacing prefixes above
    match; ``w-[300px]``, ``text-[17px]``, ``leading-[1.1]`` and standard
    staircase classes like ``p-4`` (no ``-[...]``) pass.
    """
    for tok in line.split():
        m = ARBITRARY_SPACING_RE.search(tok)
        if m and _has_nonzero_length_literal(m.group(1)):
            yield m.group(0)


def lint_text(text):
    """Return a list of (lineno, property, value) findings in the text."""
    findings = []
    raw_lines = text.splitlines()
    for lineno, line in _iter_clean_lines(text):
        if IGNORE_MARKER in raw_lines[lineno - 1]:
            continue
        for m in DECL_RE.finditer(line):
            prop = m.group(1).lower()
            if prop in SPACING_PROPERTIES:
                pattern = LENGTH_LITERAL_RE
            elif prop in POSITION_PROPERTIES:
                pattern = LENGTH_LITERAL_NO_PCT_RE
            else:
                continue
            value = m.group(2).strip()
            if _has_bad_literal(value, pattern):
                findings.append((lineno, prop, value))
        for cls in _tailwind_findings(line):
            findings.append((lineno, "class", cls))
    return findings


def is_generated_file(path):
    """True when the file header carries the generated-file marker."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            head = "".join(fh.readline() for _ in range(20))
    except OSError:
        return False
    return GENERATED_HEADER_RE.search(head) is not None


def _inode(path):
    try:
        st = os.stat(path, follow_symlinks=True)
        return (st.st_dev, st.st_ino)
    except OSError:
        return None


def walk_files(target, exts):
    """Yield files under target; directories walked recursively (symlinks
    followed, symlink cycles guarded, DEFAULT_PRUNE_DIRS pruned,
    extension-filtered)."""
    visited = set()
    for root, dirs, files in os.walk(target, followlinks=True):
        key = _inode(root)
        if key is not None:
            if key in visited:
                dirs[:] = []
                continue
            visited.add(key)
        dirs[:] = [d for d in dirs if d not in DEFAULT_PRUNE_DIRS]
        for f in files:
            if exts and os.path.splitext(f)[1].lower() not in exts:
                continue
            yield os.path.join(root, f)


def _is_excluded(path, root, patterns):
    """True when the file matches any --exclude glob (absolute path,
    root-relative path or basename)."""
    if not patterns:
        return False
    abspath = os.path.abspath(path)
    try:
        rel = os.path.relpath(abspath, root)
    except ValueError:
        rel = abspath
    rel = rel.replace(os.sep, "/")
    base = os.path.basename(abspath)
    candidates = (abspath, rel, base)
    for pat in patterns:
        p = pat.replace(os.sep, "/")
        for c in candidates:
            if fnmatch.fnmatch(c, p) or fnmatch.fnmatch(c, p.lstrip("./")):
                return True
    return False


def _parse_exts(s):
    exts = []
    for part in s.split(","):
        part = part.strip().lower()
        if not part:
            continue
        if not part.startswith("."):
            part = "." + part
        exts.append(part)
    return exts


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="token_lint.py",
        description="Lint CSS spacing-property values for non-token length "
                    "literals (ZedUI hard rule 6 fallback). Stdlib only.",
    )
    parser.add_argument("targets", metavar="TARGET", nargs="+",
                        help="file or directory to lint")
    parser.add_argument(
        "--ext",
        default=",".join(DEFAULT_EXTS),
        help="comma-separated file extensions to scan inside directories "
             "(default: %s)" % ",".join(DEFAULT_EXTS),
    )
    parser.add_argument("--exclude", metavar="GLOB", nargs="+", default=[],
                        help="glob pattern(s) of files to skip, e.g. 'tokens.css'")
    args = parser.parse_args(argv)

    findings_total = 0
    files_flagged = 0
    read_errors = 0
    for target in args.targets:
        if not os.path.exists(target):
            print("error: target not found: %s" % target, file=sys.stderr)
            return 2
        if os.path.isfile(target):
            candidates = [target]
        elif os.path.isdir(target):
            candidates = walk_files(target, _parse_exts(args.ext))
        else:
            print("error: not a file or directory: %s" % target, file=sys.stderr)
            return 2

        for path in candidates:
            if _is_excluded(path, target, args.exclude):
                continue
            if is_generated_file(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError as e:
                # A hard gate that cannot read its input must not report OK.
                print("error: cannot read %s: %s" % (path, e), file=sys.stderr)
                read_errors += 1
                continue
            finds = lint_text(text)
            for lineno, prop, value in finds:
                print("%s:%d: %s: %s" % (path, lineno, prop, value))
            if finds:
                findings_total += len(finds)
                files_flagged += 1

    if findings_total:
        print("")
        print("Summary: %d spacing-literal finding(s) in %d file(s)."
              % (findings_total, files_flagged))
        print("Component-layer spacing values must reference var(--space-*) tokens.")
        return 1
    if read_errors:
        print("error: %d file(s) could not be read; gate result is unreliable."
              % read_errors, file=sys.stderr)
        return 2
    print("OK: no spacing-literal findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
