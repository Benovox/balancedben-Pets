#!/usr/bin/env python3
"""
Balanced Ben Pets — scaffold.py
================================
ONE-TIME script that adds marker comments to existing post-*.html files so that
refresh.py can manage them.

USAGE
-----
    python3 scaffold.py --dry-run        # preview, modify nothing
    python3 scaffold.py                  # apply (auto-backup first)
    python3 scaffold.py --only FILE      # scaffold one file only

WHAT IT DOES
------------
For each post that doesn't already have markers, scaffold.py wraps existing
sections with <!-- MARKER:START --> ... <!-- MARKER:END --> comments:

    META       → wraps <head> contents
    HEADER     → wraps existing <header>...</header>
    DISCLOSURE → inserts EMPTY block at top of <main> (or after <header>)
    AUTHOR-BIO → inserts EMPTY block at end of <main> (or before <footer>)
    FOOTER     → wraps existing <footer>...</footer>

After scaffold runs once, refresh.py can fill the markers with real content.

WHAT IT WON'T TOUCH
-------------------
- Article body, headings, paragraphs, images
- Links, scripts in body, embedded videos
- Any custom HTML outside the structural shells (head/header/footer)

SAFETY
------
- Dry-run mode shows exactly what would change
- Auto-backup before any modification
- Skips files that already have markers
- Won't run if markers are partially present (avoids corruption)
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKUP_DIR = PROJECT_ROOT / "_backup"

MARKERS = ["META", "HEADER", "DISCLOSURE", "AUTHOR-BIO", "FOOTER"]

# Empty placeholder content — refresh.py fills these later
PLACEHOLDER = "<!-- (placeholder — will be filled by refresh.py) -->"

# ─────────────────────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    CYAN   = "\033[36m"

def color(text, c):
    return f"{c}{text}{C.RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# DETECTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def detect_existing_markers(html):
    """Return a set of marker names already present in the file."""
    found = set()
    for marker in MARKERS:
        if re.search(rf"<!--\s*{re.escape(marker)}:START\s*-->", html):
            found.add(marker)
    return found


def find_section(html, tag):
    """Find the first <tag>...</tag> block (case-insensitive). Returns (start, end, content) or None."""
    pattern = re.compile(rf"<{tag}\b[^>]*>(.*?)</{tag}>", re.DOTALL | re.IGNORECASE)
    match = pattern.search(html)
    if match:
        return match.start(), match.end(), match.group(0)
    return None


def find_head(html):
    """Find the <head>...</head> block."""
    return find_section(html, "head")


def find_header(html):
    """Find the first <header>...</header> block."""
    return find_section(html, "header")


def find_footer(html):
    """Find the last <footer>...</footer> block."""
    pattern = re.compile(r"<footer\b[^>]*>(.*?)</footer>", re.DOTALL | re.IGNORECASE)
    matches = list(pattern.finditer(html))
    if matches:
        last = matches[-1]
        return last.start(), last.end(), last.group(0)
    return None


def find_main_open(html):
    """Find the position right after <main> opening tag."""
    match = re.search(r"<main\b[^>]*>", html, re.IGNORECASE)
    if match:
        return match.end()
    return None


def find_main_close(html):
    """Find the position of </main> closing tag."""
    match = re.search(r"</main>", html, re.IGNORECASE)
    if match:
        return match.start()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SCAFFOLDING LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def wrap_with_markers(content, marker):
    """Wrap content between START/END marker comments."""
    return f"<!-- {marker}:START -->\n{content}\n<!-- {marker}:END -->"


def scaffold_html(html):
    """
    Add markers to an HTML document. Returns (new_html, summary_dict).
    summary_dict tells what was done: {marker: 'wrapped'/'inserted'/'skipped'/'failed'}
    """
    summary = {m: "not done" for m in MARKERS}
    existing = detect_existing_markers(html)

    # ─── META: wrap contents of <head> ───
    if "META" in existing:
        summary["META"] = "skipped (already present)"
    else:
        head = find_head(html)
        if head:
            start, end, full = head
            # Extract content between <head> and </head>
            inner_match = re.match(r"(<head\b[^>]*>)(.*?)(</head>)", full, re.DOTALL | re.IGNORECASE)
            if inner_match:
                head_open, head_inner, head_close = inner_match.groups()
                wrapped = head_open + "\n" + wrap_with_markers(head_inner.strip(), "META") + "\n" + head_close
                html = html[:start] + wrapped + html[end:]
                summary["META"] = "wrapped"
            else:
                summary["META"] = "failed (could not parse <head>)"
        else:
            summary["META"] = "failed (no <head> found)"

    # ─── HEADER: wrap entire <header>...</header> ───
    if "HEADER" in existing:
        summary["HEADER"] = "skipped (already present)"
    else:
        header = find_header(html)
        if header:
            start, end, full = header
            wrapped = wrap_with_markers(full, "HEADER")
            html = html[:start] + wrapped + html[end:]
            summary["HEADER"] = "wrapped"
        else:
            summary["HEADER"] = "failed (no <header> found)"

    # ─── FOOTER: wrap entire <footer>...</footer> ───
    if "FOOTER" in existing:
        summary["FOOTER"] = "skipped (already present)"
    else:
        footer = find_footer(html)
        if footer:
            start, end, full = footer
            wrapped = wrap_with_markers(full, "FOOTER")
            html = html[:start] + wrapped + html[end:]
            summary["FOOTER"] = "wrapped"
        else:
            summary["FOOTER"] = "failed (no <footer> found)"

    # ─── DISCLOSURE: insert empty block right after <main> opening ───
    if "DISCLOSURE" in existing:
        summary["DISCLOSURE"] = "skipped (already present)"
    else:
        main_open = find_main_open(html)
        if main_open is not None:
            placeholder = "\n" + wrap_with_markers(PLACEHOLDER, "DISCLOSURE") + "\n"
            html = html[:main_open] + placeholder + html[main_open:]
            summary["DISCLOSURE"] = "inserted"
        else:
            summary["DISCLOSURE"] = "failed (no <main> found)"

    # ─── AUTHOR-BIO: insert empty block right before </main> ───
    if "AUTHOR-BIO" in existing:
        summary["AUTHOR-BIO"] = "skipped (already present)"
    else:
        main_close = find_main_close(html)
        if main_close is not None:
            placeholder = "\n" + wrap_with_markers(PLACEHOLDER, "AUTHOR-BIO") + "\n"
            html = html[:main_close] + placeholder + html[main_close:]
            summary["AUTHOR-BIO"] = "inserted"
        else:
            summary["AUTHOR-BIO"] = "failed (no </main> found)"

    return html, summary


# ─────────────────────────────────────────────────────────────────────────────
# BACKUP
# ─────────────────────────────────────────────────────────────────────────────

def make_backup(files_to_backup):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M_scaffold")
    target = BACKUP_DIR / timestamp
    target.mkdir(parents=True, exist_ok=True)
    for f in files_to_backup:
        shutil.copy2(f, target / f.name)
    return target


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def find_post_files():
    return sorted(PROJECT_ROOT.glob("post-*.html"))


def print_header(dry_run):
    title = "DRY RUN — NOTHING WILL BE MODIFIED" if dry_run else "SCAFFOLD RUN — APPLYING CHANGES"
    print()
    print(color("🐾 Balanced Ben Pets — scaffold.py", C.BOLD + C.CYAN))
    print(color("─" * 50, C.DIM))
    print(color(title, C.BOLD + (C.YELLOW if dry_run else C.GREEN)))
    print(color("─" * 50, C.DIM))
    print()


def main():
    parser = argparse.ArgumentParser(description="Add marker comments to existing posts.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    parser.add_argument("--only", help="Scaffold only one file")
    args = parser.parse_args()

    print_header(args.dry_run)

    all_posts = find_post_files()
    if args.only:
        all_posts = [p for p in all_posts if p.name == args.only]
        if not all_posts:
            print(color(f"❌ File not found: {args.only}", C.RED))
            sys.exit(1)

    if not all_posts:
        print(color("❌ No post-*.html files found.", C.RED))
        sys.exit(1)

    print(color(f"📋 Found {len(all_posts)} post files", C.BOLD))
    print()

    # Backup before real run
    if not args.dry_run:
        backup_path = make_backup(all_posts)
        print(color(f"💾 Backed up to: {backup_path.relative_to(PROJECT_ROOT)}", C.CYAN))
        print()

    # Process each file
    fully_scaffolded = []
    partially_scaffolded = []
    already_done = []
    failed = []

    for path in all_posts:
        html = path.read_text(encoding="utf-8")
        existing = detect_existing_markers(html)

        # Already fully done
        if len(existing) == len(MARKERS):
            already_done.append(path.name)
            print(f"   {color('✓', C.GREEN)} {path.name} {color('(already scaffolded, skipped)', C.DIM)}")
            continue

        # Partially done — risky, skip
        if 0 < len(existing) < len(MARKERS):
            partially_scaffolded.append((path.name, existing))
            print(f"   {color('⚠', C.YELLOW)} {path.name} {color(f'(has {len(existing)} markers — manual review needed)', C.YELLOW)}")
            continue

        # Fresh scaffold
        new_html, summary = scaffold_html(html)
        any_failed = any("failed" in v for v in summary.values())
        all_done = all(v in ("wrapped", "inserted") for v in summary.values())

        status_icon = color("✓", C.GREEN) if all_done else (color("✗", C.RED) if any_failed else color("~", C.YELLOW))
        print(f"   {status_icon} {path.name}")
        for marker, status in summary.items():
            icon = "·" if "skipped" in status or status == "not done" else ("✓" if status in ("wrapped", "inserted") else "✗")
            color_code = C.DIM if status in ("not done", "skipped") else (C.GREEN if status in ("wrapped", "inserted") else C.RED)
            print(color(f"      {icon} {marker:12} {status}", color_code))

        if all_done:
            fully_scaffolded.append(path.name)
            if not args.dry_run:
                path.write_text(new_html, encoding="utf-8")
        elif any_failed:
            failed.append((path.name, [m for m, s in summary.items() if "failed" in s]))

    # ─── SUMMARY ───
    print()
    print(color("═" * 50, C.DIM))
    print(color("SUMMARY", C.BOLD))
    print(f"   {color(str(len(fully_scaffolded)), C.GREEN)} fully scaffolded")
    print(f"   {color(str(len(already_done)), C.DIM)} already had markers (skipped)")
    print(f"   {color(str(len(partially_scaffolded)), C.YELLOW)} partial markers (manual review)")
    print(f"   {color(str(len(failed)), C.RED)} failed (missing structural tags)")

    if failed:
        print()
        print(color("FAILED FILES (need manual structure fix):", C.RED))
        for filename, missing in failed:
            print(f"   {filename}: missing {', '.join(missing)}")

    if partially_scaffolded:
        print()
        print(color("PARTIAL FILES (manual review):", C.YELLOW))
        for filename, existing in partially_scaffolded:
            present = ", ".join(existing)
            absent = ", ".join(set(MARKERS) - existing)
            print(f"   {filename}")
            print(color(f"      has: {present}", C.DIM))
            print(color(f"      missing: {absent}", C.DIM))

    print(color("═" * 50, C.DIM))
    if args.dry_run:
        print(color("Run without --dry-run to apply.", C.DIM))
    else:
        print(color("Next step: python3 scripts/refresh.py --dry-run", C.CYAN))
    print()


if __name__ == "__main__":
    main()
