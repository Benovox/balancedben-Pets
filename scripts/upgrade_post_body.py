#!/usr/bin/env python3
"""
Balanced Ben Pets — upgrade_post_body.py
==========================================
ONE-TIME script that restructures post bodies to match the new editorial design.

USAGE
-----
    python3 scripts/upgrade_post_body.py --dry-run --only post-can-dogs-talk.html
    python3 scripts/upgrade_post_body.py --only post-can-dogs-talk.html
    python3 scripts/upgrade_post_body.py --dry-run    # preview all
    python3 scripts/upgrade_post_body.py              # apply to all

WHAT IT DOES
------------
For each post-*.html that has the markers from refresh.py, it performs three
transformations:

  1. HERO UPGRADE
     <section class="hero">              ──>  <section class="post-hero-wrap">
       <img ... />                              <div class="breadcrumb">...</div>
     </section>                                 <div class="post-hero">
                                                  <img ... />
                                                  <div class="post-hero-content">
                                                    <span class="category-tag">…</span>
                                                    <h1>…</h1>
                                                    <div class="meta-line">…</div>
                                                  </div>
                                                </div>
                                              </section>

     The H1 + .meta + .tags from inside <main> are PULLED UP into the hero overlay.

  2. ARTICLE WRAPPER
     <main>             ──>  <article class="post">
       …content…                  …content unchanged…
     </main>                  </article>

  3. OLD AUTHOR BOX REMOVAL
     Detects and deletes the old <div class="author-box">...Paws & Whiskers...</div>
     since the new <!-- AUTHOR-BIO --> partial replaces it.

WHAT IT DOES NOT TOUCH
----------------------
- Body content: paragraphs, lists, blockquotes, h2-h6, images
- Custom components: carousels, charts, reading-list grids
- Scripts (Google Translate, AdSense, Analytics, carousel JS)
- Markers from refresh.py (HEADER, FOOTER, DISCLOSURE, AUTHOR-BIO, META)
- Post navigation (back/next links)

SAFETY
------
- Dry-run mode shows what would change
- Auto-backup before any modification
- Skips posts that don't have a <section class="hero"> (assumed already upgraded
  or doesn't follow the standard pattern — we error out so user can review)
- After upgrade, refresh.py should still work normally on the file
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = PROJECT_ROOT / "_backup"
CATEGORIES_FILE = DATA_DIR / "categories.json"

CATEGORY_LABELS = {
    "dogs": "Dogs",
    "cats": "Cats",
    "exotic": "Exotic & Other Pets",
    "general": "All Pets",
}

CATEGORY_BREADCRUMB_LINK = {
    "dogs": "dogs.html",
    "cats": "cats.html",
    "exotic": "exotic.html",
    "general": "blog.html",
}

# Author info for the meta line in the hero overlay
AUTHOR_INITIALS = "BL"
AUTHOR_NAME = "Breno Leite"


# ─────────────────────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"; CYAN = "\033[36m"

def color(text, c):
    return f"{c}{text}{C.RESET}"


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def load_categories():
    if not CATEGORIES_FILE.exists():
        print(color(f"❌ {CATEGORIES_FILE} not found", C.RED))
        sys.exit(1)
    return json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))


def find_category_for(filename, categories):
    """Return (category_key, label, link) for a post, or (None, None, None) if not found."""
    for cat_key, posts in categories.items():
        if cat_key.startswith("_") or not isinstance(posts, list):
            continue
        if filename in posts:
            label = CATEGORY_LABELS.get(cat_key, cat_key.title())
            link = CATEGORY_BREADCRUMB_LINK.get(cat_key, "blog.html")
            return cat_key, label, link
    return None, None, None


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def find_hero_section(html):
    """Find the existing <section class="hero">...</section> block.
    Returns (start, end, full_match, image_tag) or None."""
    pattern = re.compile(
        r'<section\s+class="hero"[^>]*>(.*?)</section>',
        re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(html)
    if not match:
        return None
    inner = match.group(1)
    # Find the <img> tag inside
    img_match = re.search(r'<img\s+[^>]*?/?>', inner, re.DOTALL)
    img_tag = img_match.group(0) if img_match else ''
    return match.start(), match.end(), match.group(0), img_tag


def find_h1_meta_block(html):
    """Find the H1 + optional .meta + optional .tags block inside <main>.
    Returns (start, end, h1_text, meta_text, tags_html) or None."""
    # Look for first <h1> after the <main> opening
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    if not h1_match:
        return None

    block_start = h1_match.start()
    h1_text = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()

    # Look for adjacent <div class="meta">...</div> right after the H1
    after_h1 = html[h1_match.end():]
    meta_match = re.match(r'\s*<div\s+class="meta"[^>]*>(.*?)</div>', after_h1, re.DOTALL | re.IGNORECASE)
    meta_text = ''
    cursor = h1_match.end()
    if meta_match:
        meta_text = re.sub(r'<[^>]+>', '', meta_match.group(1)).strip()
        cursor = h1_match.end() + meta_match.end()

    # Look for adjacent <div class="tags">...</div> right after .meta
    after_meta = html[cursor:]
    tags_match = re.match(r'\s*<div\s+class="tags"[^>]*>(.*?)</div>', after_meta, re.DOTALL | re.IGNORECASE)
    tags_html = ''
    if tags_match:
        tags_html = tags_match.group(0)
        cursor = cursor + tags_match.end()

    block_end = cursor
    return block_start, block_end, h1_text, meta_text, tags_html


def parse_meta_line(meta_text):
    """Parse 'By Breno Leite • Updated April 22, 2026 • 14-16 min read' into pieces.
    Returns (author, date, read_time) — any may be empty if not detected."""
    # Common separators: • · — - |
    parts = re.split(r'\s*[\u2022\u00b7\u2014\u2013\|]\s*', meta_text)
    parts = [p.strip() for p in parts if p.strip()]

    author = ''
    date = ''
    read_time = ''

    for part in parts:
        if re.search(r'\d+[-–]?\d*\s*min', part, re.IGNORECASE):
            read_time = part
        elif re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d+', part, re.IGNORECASE) or re.search(r'\b\d{4}\b', part):
            # Looks like a date
            date = re.sub(r'^(updated|published|posted|on)\s+', '', part, flags=re.IGNORECASE).strip()
        elif re.match(r'(by|written by|author:?)\s+', part, re.IGNORECASE):
            author = re.sub(r'^(by|written by|author:?)\s+', '', part, flags=re.IGNORECASE).strip()
        elif not author and len(part) < 50 and not part.startswith('#'):
            # Probably the author if nothing else matched
            author = part

    return author or AUTHOR_NAME, date, read_time


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFORMATIONS
# ─────────────────────────────────────────────────────────────────────────────

def html_escape(text):
    """Minimal escape for text injected into HTML attributes/content."""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))


def build_new_hero(img_tag, h1_text, author, date, read_time, category_label, category_link, breadcrumb_link):
    """Build the new post-hero-wrap markup with title overlay."""
    # Breadcrumb
    breadcrumb_parts = [
        '<a href="index.html">Home</a>',
        '<span class="sep">›</span>',
        f'<a href="{breadcrumb_link}">{html_escape(category_label)}</a>',
        '<span class="sep">›</span>',
        html_escape(h1_text)
    ]
    breadcrumb_html = ''.join(breadcrumb_parts)

    # Meta line pieces
    meta_pieces = [f'<span><strong>{html_escape(author)}</strong></span>']
    if date:
        meta_pieces.append('<span class="dot">·</span>')
        meta_pieces.append(f'<span>{html_escape(date)}</span>')
    if read_time:
        meta_pieces.append('<span class="dot">·</span>')
        meta_pieces.append(f'<span>{html_escape(read_time)}</span>')
    meta_html = '\n        '.join(meta_pieces)

    return f"""<section class="post-hero-wrap">
  <div class="breadcrumb">
    {breadcrumb_html}
  </div>

  <div class="post-hero">
    {img_tag}
    <div class="post-hero-content">
      <span class="category-tag">{html_escape(category_label)}</span>
      <h1>{html_escape(h1_text)}</h1>
      <div class="meta-line">
        <div class="author-thumb">{AUTHOR_INITIALS}</div>
        {meta_html}
      </div>
    </div>
  </div>
</section>"""


def remove_old_author_box(html):
    """Remove old <div class="author-box">...</div> blocks.
    Returns (new_html, count_removed)."""
    pattern = re.compile(
        r'\s*<div\s+class="author-box"[^>]*>.*?</div>\s*',
        re.DOTALL | re.IGNORECASE
    )
    new_html, n = pattern.subn('\n\n', html)
    return new_html, n


def swap_main_to_article(html):
    """Swap <main>...</main> wrapping to <article class="post">...</article>.
    Returns (new_html, swapped_bool)."""
    # Replace opening tag
    new_html, opens = re.subn(r'<main\b[^>]*>', '<article class="post">', html, count=1, flags=re.IGNORECASE)
    # Replace closing tag
    new_html, closes = re.subn(r'</main>', '</article>', new_html, count=1, flags=re.IGNORECASE)
    return new_html, (opens > 0 and closes > 0)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN UPGRADE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_already_upgraded(html):
    """Return True if the post body has already been upgraded."""
    return ('class="post-hero-wrap"' in html and
            '<article class="post">' in html)


def upgrade_post(html, filename, categories):
    """Apply all 3 transformations to a single post HTML.
    Returns (new_html, summary_dict).
    summary keys: hero_upgrade, main_swap, author_box_removed, status, errors"""
    summary = {
        'hero_upgrade': False,
        'main_swap': False,
        'author_box_removed': 0,
        'status': 'pending',
        'errors': [],
    }

    # Pre-check: already upgraded?
    if detect_already_upgraded(html):
        summary['status'] = 'already-upgraded'
        return html, summary

    # Lookup category
    cat_key, cat_label, cat_link = find_category_for(filename, categories)
    if cat_key is None:
        summary['status'] = 'failed'
        summary['errors'].append(f'not in categories.json — cannot determine category')
        return html, summary

    # ─── TRANSFORM 1: HERO UPGRADE ────────────────────────────────────────
    hero_info = find_hero_section(html)
    if hero_info is None:
        summary['status'] = 'failed'
        summary['errors'].append('no <section class="hero"> found — manual review needed')
        return html, summary

    hero_start, hero_end, hero_full, img_tag = hero_info

    # Find H1 + meta block (which lives INSIDE <main>, AFTER the hero section)
    h1_info = find_h1_meta_block(html[hero_end:])
    if h1_info is None:
        summary['status'] = 'failed'
        summary['errors'].append('no <h1> found after hero')
        return html, summary

    rel_h1_start, rel_h1_end, h1_text, meta_text, tags_html = h1_info
    h1_start = hero_end + rel_h1_start
    h1_end = hero_end + rel_h1_end

    # Parse meta line
    author, date, read_time = parse_meta_line(meta_text) if meta_text else (AUTHOR_NAME, '', '')

    # Build new hero
    new_hero = build_new_hero(
        img_tag=img_tag,
        h1_text=h1_text,
        author=author,
        date=date,
        read_time=read_time,
        category_label=cat_label,
        category_link=cat_link,
        breadcrumb_link=cat_link,
    )

    # Replace OLD hero with new hero
    new_html = html[:hero_start] + new_hero + html[hero_end:]
    # Recalculate H1 block position (new hero may have changed length)
    delta = len(new_hero) - (hero_end - hero_start)
    new_h1_start = h1_start + delta
    new_h1_end = h1_end + delta
    # Remove the old H1 + meta + tags block from inside <main>
    new_html = new_html[:new_h1_start] + new_html[new_h1_end:]
    summary['hero_upgrade'] = True

    # ─── TRANSFORM 2: SWAP <main> → <article class="post"> ────────────────
    new_html, swapped = swap_main_to_article(new_html)
    summary['main_swap'] = swapped
    if not swapped:
        summary['errors'].append('could not find <main>...</main> to swap')

    # ─── TRANSFORM 3: REMOVE OLD AUTHOR BOX ───────────────────────────────
    new_html, removed = remove_old_author_box(new_html)
    summary['author_box_removed'] = removed

    if summary['hero_upgrade'] and summary['main_swap']:
        summary['status'] = 'upgraded'
    else:
        summary['status'] = 'partial'

    return new_html, summary


# ─────────────────────────────────────────────────────────────────────────────
# BACKUP
# ─────────────────────────────────────────────────────────────────────────────

def make_backup(files):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M_body-upgrade")
    target = BACKUP_DIR / timestamp
    target.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, target / f.name)
    return target


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def find_post_files():
    return sorted(PROJECT_ROOT.glob("post-*.html"))


def main():
    parser = argparse.ArgumentParser(description="Upgrade post bodies to new editorial design.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    parser.add_argument("--only", help="Process only one file")
    args = parser.parse_args()

    print()
    print(color("🐾 Balanced Ben Pets — upgrade_post_body.py", C.BOLD + C.CYAN))
    print(color("─" * 50, C.DIM))
    print(color("DRY RUN — NOTHING WILL BE MODIFIED" if args.dry_run else "UPGRADE RUN — APPLYING CHANGES",
                C.BOLD + (C.YELLOW if args.dry_run else C.GREEN)))
    print(color("─" * 50, C.DIM))
    print()

    categories = load_categories()
    all_posts = find_post_files()

    if args.only:
        all_posts = [p for p in all_posts if p.name == args.only]
        if not all_posts:
            print(color(f"❌ File not found: {args.only}", C.RED))
            sys.exit(1)

    print(color(f"📋 Found {len(all_posts)} post file(s)", C.BOLD))
    print()

    if not args.dry_run:
        backup = make_backup(all_posts)
        print(color(f"💾 Backed up to: {backup.relative_to(PROJECT_ROOT)}", C.CYAN))
        print()

    # Process each file
    upgraded = []
    already_done = []
    failed = []
    partial = []

    for path in all_posts:
        html = path.read_text(encoding="utf-8")
        new_html, summary = upgrade_post(html, path.name, categories)
        status = summary['status']

        # Print per-file result
        if status == 'upgraded':
            print(f"   {color('✓', C.GREEN)} {path.name}")
            print(color(f"      ✓ hero upgraded", C.DIM))
            print(color(f"      ✓ <main> → <article class=\"post\">", C.DIM))
            if summary['author_box_removed']:
                print(color(f"      ✓ {summary['author_box_removed']} old author-box removed", C.DIM))
            upgraded.append(path.name)
            if not args.dry_run:
                path.write_text(new_html, encoding="utf-8")
        elif status == 'already-upgraded':
            print(f"   {color('·', C.DIM)} {path.name} {color('(already upgraded, skipped)', C.DIM)}")
            already_done.append(path.name)
        elif status == 'partial':
            print(f"   {color('~', C.YELLOW)} {path.name}")
            for err in summary['errors']:
                print(color(f"      ⚠ {err}", C.YELLOW))
            partial.append(path.name)
            if not args.dry_run:
                path.write_text(new_html, encoding="utf-8")
        else:  # failed
            print(f"   {color('✗', C.RED)} {path.name}")
            for err in summary['errors']:
                print(color(f"      ✗ {err}", C.RED))
            failed.append((path.name, summary['errors']))

    # ─── SUMMARY ─────────────────────────────────────────────────────────
    print()
    print(color("═" * 50, C.DIM))
    print(color("SUMMARY", C.BOLD))
    print(f"   {color(str(len(upgraded)), C.GREEN)} fully upgraded")
    print(f"   {color(str(len(already_done)), C.DIM)} already done (skipped)")
    print(f"   {color(str(len(partial)), C.YELLOW)} partial (review needed)")
    print(f"   {color(str(len(failed)), C.RED)} failed (manual fix needed)")

    if failed:
        print()
        print(color("FAILED FILES:", C.RED))
        for filename, errs in failed:
            print(f"   {filename}")
            for e in errs:
                print(color(f"      → {e}", C.DIM))

    print(color("═" * 50, C.DIM))
    if args.dry_run:
        print(color("Run without --dry-run to apply.", C.DIM))
    else:
        print(color("Next: open the file in your browser to verify.", C.CYAN))
    print()


if __name__ == "__main__":
    main()
