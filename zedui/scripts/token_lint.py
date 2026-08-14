#!/usr/bin/env python3
"""token_lint.py — ZedUI spacing-literal linter (hard rule 6 fallback).

Impeccable's design-system detector compares font/color/radius/font-size
against DESIGN.md, but NOT spacing: ``padding: 17px`` is never flagged
upstream. This script closes that gap. It scans CSS declarations of
spacing-like properties — margin/padding/gap/inset and their directional
forms, plus top/right/bottom/left — and reports any value that contains a
length literal (17px, 1.5rem, 50%, ...) without a var() reference.

The token definition layer is exempt: a file whose header carries the
"GENERATED FILE — DO NOT EDIT BY HAND" marker (tokens.css and friends) is
skipped entirely; --exclude accepts explicit globs such as 'tokens.css'.

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
    2  usage error (bad arguments / target not found)
"""

import argparse
import fnmatch
import os
import re
import sys

DEFAULT_EXTS = [".css", ".scss", ".less", ".html", ".vue", ".jsx", ".tsx"]

SPACING_PROPERTIES = frozenset([
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "gap", "row-gap", "column-gap",
    "inset", "inset-top", "inset-right", "inset-bottom", "inset-left",
    "top", "right", "bottom", "left",
])

# A length literal: optional sign, integer or decimal digits, a CSS unit.
LENGTH_LITERAL_RE = re.compile(
    r"(?<![\w.-])-?(?:\d+(?:\.\d*)?|\.\d+)(?:px|rem|em|vh|vw|%)",
    re.IGNORECASE,
)

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


def _has_bad_literal(value):
    """True when the value carries a non-exempt spacing length literal."""
    if "var(" in value:
        return False
    for comp in re.split(r"[\s,]+", value.strip()):
        if not comp:
            continue
        if comp in ZERO_AND_KEYWORD_EXEMPT:
            continue
        if LENGTH_LITERAL_RE.search(comp):
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


def lint_text(text):
    """Return a list of (lineno, property, value) findings in the text."""
    findings = []
    for lineno, line in _iter_clean_lines(text):
        for m in DECL_RE.finditer(line):
            prop = m.group(1).lower()
            if prop not in SPACING_PROPERTIES:
                continue
            value = m.group(2).strip()
            if _has_bad_literal(value):
                findings.append((lineno, prop, value))
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
    followed, symlink cycles and .git pruned, extension-filtered)."""
    visited = set()
    for root, dirs, files in os.walk(target, followlinks=True):
        key = _inode(root)
        if key is not None:
            if key in visited:
                dirs[:] = []
                continue
            visited.add(key)
        dirs[:] = [d for d in dirs if d != ".git"]
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
                print("error: cannot read %s: %s" % (path, e), file=sys.stderr)
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
    print("OK: no spacing-literal findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
