#!/usr/bin/env python3
"""
Balanced Ben Pets — refresh.py
================================
Refreshes shared HTML partials (header, footer, disclosure, author-bio, meta-tags)
across all post-*.html files and key pages.

USAGE
-----
    python3 refresh.py --dry-run        # preview changes, modify nothing
    python3 refresh.py                  # apply changes (auto-backup first)
    python3 refresh.py --only FILE      # refresh only one file
    python3 refresh.py --category dogs  # refresh only one category
    python3 refresh.py --restore        # restore latest backup

HOW IT WORKS
------------
Each managed page contains marker comments like:

    <!-- HEADER:START -->
    ...managed content...
    <!-- HEADER:END -->

refresh.py reads partials/header.html and replaces everything between the
markers. Anything OUTSIDE the markers (your actual article content) is never
touched.

REQUIRES
--------
- Python 3.7+
- No external packages (uses stdlib only)
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG — paths are relative to project root (where this script's parent is)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

PARTIALS_DIR = PROJECT_ROOT / "partials"
DATA_DIR     = PROJECT_ROOT / "data"
BACKUP_DIR   = PROJECT_ROOT / "_backup"

CATEGORIES_FILE = DATA_DIR / "categories.json"

# Map of marker name → partial filename
PARTIALS = {
    "META":        "meta-tags.html",
    "HEADER":      "header.html",
    "DISCLOSURE":  "disclosure.html",
    "AUTHOR-BIO":  "author-bio.html",
    "FOOTER":      "footer.html",
}

# Old brand strings to flag (case-insensitive)
OLD_BRAND_STRINGS = [
    "Paws & Whiskers",
    "Paws and Whiskers",
    "@BalancedPets",
    "Balanced Pets",  # only flag when not followed by " Pets" or "Ben Pets"
]

# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL COLORS (no external lib — ANSI escape codes)
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    CYAN   = "\033[36m"
    MAGENTA = "\033[35m"

def color(text, c):
    return f"{c}{text}{C.RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# REPORT COLLECTOR — accumulates all findings during dry-run / real run
# ─────────────────────────────────────────────────────────────────────────────

class Report:
    def __init__(self):
        self.posts_clean = []          # files that will refresh cleanly
        self.posts_with_issues = {}    # filename → list of issue strings
        self.orphans_on_disk = []      # post files not in categories.json
        self.orphans_in_json = []      # entries in categories.json not on disk
        self.amazon_links_total = 0
        self.amazon_links_ok = 0
        self.amazon_links_missing_rel = []   # (filename, link)
        self.amazon_links_fixed = 0          # auto-fixed during real run
        self.amazon_links_skipped_partial = []  # (filename) — had partial rel, manual fix needed
        self.images_total = 0
        self.images_missing_alt = []         # (filename, count)
        self.images_missing_dims = []        # (filename, count)
        self.old_brand_hits = []             # (filename, line, text)
        self.duplicate_markers = []          # (filename, marker)
        self.unmatched_markers = []          # (filename, marker, type)

    def add_issue(self, filename, issue):
        self.posts_with_issues.setdefault(filename, []).append(issue)


# ─────────────────────────────────────────────────────────────────────────────
# CORE — load partials, categories, files
# ─────────────────────────────────────────────────────────────────────────────

def load_partials():
    """Load every partial HTML file into a dict keyed by marker name."""
    partials = {}
    for marker, filename in PARTIALS.items():
        path = PARTIALS_DIR / filename
        if not path.exists():
            print(color(f"❌ Missing partial: {path}", C.RED))
            sys.exit(1)
        partials[marker] = path.read_text(encoding="utf-8").strip()
    return partials


def load_categories():
    """Load categories.json. Returns dict like {'dogs': [filenames], ...}
    Filters out internal/special keys: _comment, _unpublished.
    Recognizes 'general' as posts that should be processed but not assigned
    to a category page (will appear on home/blog/sitemap only)."""
    if not CATEGORIES_FILE.exists():
        print(color(f"⚠️  No categories.json found at {CATEGORIES_FILE}", C.YELLOW))
        print(color("    Create one with: data/categories.json", C.DIM))
        return {}
    try:
        data = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
        # Strip internal keys (anything starting with _)
        clean = {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, list)}
        return clean
    except json.JSONDecodeError as e:
        print(color(f"❌ Invalid JSON in {CATEGORIES_FILE}: {e}", C.RED))
        sys.exit(1)


def load_unpublished():
    """Load list of unpublished posts that should be skipped entirely."""
    if not CATEGORIES_FILE.exists():
        return set()
    try:
        data = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
        return set(data.get("_unpublished", []))
    except json.JSONDecodeError:
        return set()


def find_post_files():
    """Find all post-*.html files in project root."""
    return sorted(PROJECT_ROOT.glob("post-*.html"))


# Site-wide pages that also need header/footer/meta partials refreshed
# (these have markers but aren't posts)
SITE_PAGES = [
    "index.html",
    "blog.html",
    "dogs.html",
    "cats.html",
    "exotic.html",
    "about.html",
    "contact.html",
    "privacy.html",
    "disclaimer.html",
    "terms.html",
]


def find_site_pages():
    """Find all site-wide pages (non-post) that exist on disk."""
    return [PROJECT_ROOT / name for name in SITE_PAGES if (PROJECT_ROOT / name).exists()]


def get_post_category(filename, categories):
    """Return the category name for a given post filename, or None."""
    for cat_name, posts in categories.items():
        if filename in posts:
            return cat_name
    return None


# ─────────────────────────────────────────────────────────────────────────────
# MARKER LOGIC — find/replace content between <!-- X:START --> and <!-- X:END -->
# ─────────────────────────────────────────────────────────────────────────────

def make_marker_pattern(marker):
    """Build a regex that matches <!-- MARKER:START -->...<!-- MARKER:END -->"""
    return re.compile(
        rf"<!--\s*{re.escape(marker)}:START\s*-->.*?<!--\s*{re.escape(marker)}:END\s*-->",
        re.DOTALL
    )


def has_marker(html, marker):
    """Return (has_start, has_end, count_start, count_end)"""
    start = re.findall(rf"<!--\s*{re.escape(marker)}:START\s*-->", html)
    end = re.findall(rf"<!--\s*{re.escape(marker)}:END\s*-->", html)
    return len(start) > 0, len(end) > 0, len(start), len(end)


def extract_post_metadata(html, filename):
    """Extract per-post metadata to substitute into the META partial placeholders.

    Looks for:
    - <title>...</title> → TITLE (strips ' | Balanced Ben Pets' suffix)
    - <meta name="description" content="..."> → DESCRIPTION
    - First <img src="..."> in post-hero or .post-hero-image → IMAGE
    - filename → SLUG
    - DATE_PUBLISHED → preserved from existing post (schema, <time>, meta tag);
      falls back to today only if nothing found
    - DATE_MODIFIED → always today (this refresh = a modification)

    Returns dict with all template variables.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Title: from existing <title> tag, or from <h1>, or filename fallback
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        # Strip site suffix
        title = re.sub(r"\s*\|\s*Balanced Ben Pets\s*$", "", title)
        title = re.sub(r"\s*-\s*Paws\s*&amp;?\s*Whiskers\s*$", "", title, flags=re.IGNORECASE)
    else:
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            # Strip nested HTML
            title = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()
        else:
            # Filename fallback
            title = filename.replace("post-", "").replace(".html", "").replace("-", " ").title()

    # Description: from existing meta description
    desc_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']',
        html,
        re.IGNORECASE
    )
    description = desc_match.group(1).strip() if desc_match else f"{title} — a practical guide from Balanced Ben Pets."

    # Image: first image in the post-hero or first <img> overall
    image = ""
    hero_img = re.search(r'class="post-hero"[^>]*>\s*.*?<img\s+[^>]*src=["\']([^"\']+)["\']', html, re.DOTALL)
    if hero_img:
        image = hero_img.group(1)
    else:
        any_img = re.search(r'<img\s+[^>]*src=["\']([^"\']+)["\']', html)
        if any_img:
            image = any_img.group(1)
    if not image:
        image = "assets/images/default-hero.jpg"

    # Compute absolute URL for OG/Twitter/Schema:
    # - If image is already absolute (https://...), use as-is
    # - If relative, prefix with site URL
    if image.startswith(("http://", "https://", "//")):
        image_absolute = image
    else:
        image_absolute = f"https://balancedben.com/{image.lstrip('/')}"

    # ─── DATE_PUBLISHED: preserve from existing post ──────────────────────
    # Priority order:
    #   1. JSON-LD schema "datePublished" field
    #   2. <meta property="article:published_time"> (Open Graph)
    #   3. <time datetime="..."> tag in the post (if it looks like a publish date)
    #   4. Today (fallback for brand-new posts)
    date_published = None

    # 1. JSON-LD schema
    schema_match = re.search(
        r'"datePublished"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2})',
        html
    )
    if schema_match:
        date_published = schema_match.group(1)

    # 2. Open Graph article:published_time
    if not date_published:
        og_match = re.search(
            r'<meta\s+property=["\']article:published_time["\']\s+content=["\']([0-9]{4}-[0-9]{2}-[0-9]{2})',
            html,
            re.IGNORECASE
        )
        if og_match:
            date_published = og_match.group(1)

    # 3. First <time datetime="YYYY-MM-DD"> tag — but only if it's NOT inside
    #    the META markers (which would be auto-generated). Look in body.
    if not date_published:
        # Find post-hero meta-line first <time> tag
        time_match = re.search(
            r'<time\s+[^>]*datetime=["\']([0-9]{4}-[0-9]{2}-[0-9]{2})',
            html,
            re.IGNORECASE
        )
        if time_match:
            date_published = time_match.group(1)

    # 4. Fallback: today (only for brand-new posts with no historic date)
    if not date_published:
        date_published = today

    return {
        "TITLE": title,
        "DESCRIPTION": description,
        "SLUG": filename,
        "IMAGE": image,
        "IMAGE_ABSOLUTE": image_absolute,
        "DATE_PUBLISHED": date_published,   # preserved from existing post
        "DATE_MODIFIED": today,              # always today (this is a refresh)
    }


def substitute_placeholders(content, metadata):
    """Replace {{TITLE}}, {{DESCRIPTION}}, etc. with actual values."""
    for key, value in metadata.items():
        # Escape special chars in value to keep HTML/JSON safe
        safe_value = value.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;') if key in ("TITLE", "DESCRIPTION") else value
        content = content.replace(f"{{{{{key}}}}}", safe_value)
    return content


def inject_partial(html, marker, partial_content, metadata=None):
    """Replace content between markers with the new partial.
    If metadata is provided, substitute {{PLACEHOLDER}} tokens first."""
    if metadata:
        partial_content = substitute_placeholders(partial_content, metadata)
    pattern = make_marker_pattern(marker)
    replacement = f"<!-- {marker}:START -->\n{partial_content}\n<!-- {marker}:END -->"
    new_html, count = pattern.subn(replacement, html)
    return new_html, count


# ─────────────────────────────────────────────────────────────────────────────
# AUDITS — checks that run during dry-run AND real run (to populate report)
# ─────────────────────────────────────────────────────────────────────────────

def audit_amazon_links(html, filename, report):
    """Find Amazon affiliate links and check rel attributes."""
    # Match <a href="...amazon..." or <a href="...amzn..."
    pattern = re.compile(r'<a\s+[^>]*href="([^"]*(?:amazon\.|amzn\.)[^"]*)"[^>]*>', re.IGNORECASE)
    for match in pattern.finditer(html):
        full_tag = match.group(0)
        href = match.group(1)
        report.amazon_links_total += 1
        if 'rel=' in full_tag.lower() and 'nofollow' in full_tag.lower() and 'sponsored' in full_tag.lower():
            report.amazon_links_ok += 1
        else:
            report.amazon_links_missing_rel.append((filename, href))


def fix_amazon_links(html, filename, report):
    """Auto-fix Amazon links by adding rel='nofollow sponsored' target='_blank'.

    SAFETY: Only fixes links with NO existing rel= attribute at all.
    Links that have a partial rel (e.g. rel='nofollow' but no 'sponsored')
    are LEFT ALONE — user must fix those manually to avoid corrupting tags.

    Returns (new_html, count_fixed, count_skipped_partial).
    """
    pattern = re.compile(
        r'(<a\s+)([^>]*?href="(?:[^"]*(?:amazon\.|amzn\.)[^"]*)"[^>]*?)(>)',
        re.IGNORECASE
    )

    fixed_count = 0
    skipped_partial = 0

    def replace(match):
        nonlocal fixed_count, skipped_partial
        prefix = match.group(1)
        attrs = match.group(2)
        suffix = match.group(3)

        # If link already has rel= attribute (even partial), skip — too risky to modify
        if re.search(r'\brel\s*=', attrs, re.IGNORECASE):
            # Check if it's already complete; if not, count as skipped
            if not (re.search(r'rel\s*=\s*["\'][^"\']*nofollow', attrs, re.IGNORECASE) and
                    re.search(r'rel\s*=\s*["\'][^"\']*sponsored', attrs, re.IGNORECASE)):
                skipped_partial += 1
            return match.group(0)

        # Safe to add rel and target
        new_attrs = attrs.rstrip()
        # Add target=_blank if missing
        if not re.search(r'\btarget\s*=', new_attrs, re.IGNORECASE):
            new_attrs += ' target="_blank"'
        new_attrs += ' rel="nofollow sponsored noopener"'

        fixed_count += 1
        return f"{prefix}{new_attrs}{suffix}"

    new_html = pattern.sub(replace, html)
    return new_html, fixed_count, skipped_partial


def audit_images(html, filename, report):
    """Check images for missing alt and width/height attributes."""
    img_pattern = re.compile(r'<img\s+[^>]*>', re.IGNORECASE)
    missing_alt = 0
    missing_dims = 0
    for match in img_pattern.finditer(html):
        tag = match.group(0)
        report.images_total += 1
        if not re.search(r'\balt\s*=\s*"[^"]*"', tag, re.IGNORECASE):
            missing_alt += 1
        has_w = re.search(r'\bwidth\s*=\s*"', tag, re.IGNORECASE)
        has_h = re.search(r'\bheight\s*=\s*"', tag, re.IGNORECASE)
        if not (has_w and has_h):
            missing_dims += 1
    if missing_alt:
        report.images_missing_alt.append((filename, missing_alt))
    if missing_dims:
        report.images_missing_dims.append((filename, missing_dims))


def audit_old_brand(html, filename, report):
    """Find old brand strings."""
    for line_num, line in enumerate(html.splitlines(), 1):
        for old in OLD_BRAND_STRINGS:
            if old.lower() in line.lower():
                # Skip false positive: "Balanced Pets" inside "Balanced Ben Pets"
                if old == "Balanced Pets" and "Balanced Ben Pets" in line:
                    continue
                report.old_brand_hits.append((filename, line_num, old))


def audit_markers(html, filename, report):
    """Check that every marker has matching START + END (no duplicates, no orphans).
    Note: DISCLOSURE and AUTHOR-BIO markers are only required on post-*.html files,
    since they only make sense on individual articles (not on category/index pages)."""
    has_any_marker = False
    is_post = filename.startswith("post-")
    # Markers that are required on every page type
    universal_markers = ["META", "HEADER", "FOOTER"]
    # Markers that are only required on individual posts
    post_only_markers = ["DISCLOSURE", "AUTHOR-BIO"]

    for marker in PARTIALS.keys():
        is_required = marker in universal_markers or (is_post and marker in post_only_markers)
        has_start, has_end, count_start, count_end = has_marker(html, marker)
        if has_start or has_end:
            has_any_marker = True
        # Duplicates (always flag)
        if count_start > 1 or count_end > 1:
            report.duplicate_markers.append((filename, marker))
            report.add_issue(filename, f"duplicate {marker} marker")
        # Mismatched (always flag)
        if has_start and not has_end:
            report.unmatched_markers.append((filename, marker, "missing END"))
            report.add_issue(filename, f"{marker} has START but no END")
        elif has_end and not has_start:
            report.unmatched_markers.append((filename, marker, "missing START"))
            report.add_issue(filename, f"{marker} has END but no START")
        elif not has_start and not has_end and is_required:
            # Only flag missing markers if required for this page type
            report.add_issue(filename, f"missing {marker} marker entirely")
    return has_any_marker


# ─────────────────────────────────────────────────────────────────────────────
# BACKUP — timestamped copies before modifying
# ─────────────────────────────────────────────────────────────────────────────

def make_backup(files_to_backup):
    """Copy files to _backup/YYYY-MM-DD_HH-MM/ and return the backup path."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    target = BACKUP_DIR / timestamp
    target.mkdir(parents=True, exist_ok=True)
    for f in files_to_backup:
        shutil.copy2(f, target / f.name)
    return target


def restore_latest_backup():
    """Restore from the most recent backup folder."""
    if not BACKUP_DIR.exists():
        print(color("❌ No _backup/ folder found. Nothing to restore.", C.RED))
        sys.exit(1)
    backups = sorted([d for d in BACKUP_DIR.iterdir() if d.is_dir()], reverse=True)
    if not backups:
        print(color("❌ No backups found inside _backup/", C.RED))
        sys.exit(1)
    latest = backups[0]
    print(color(f"🔄 Restoring from: {latest.name}", C.CYAN))
    confirm = input(color("Type 'yes' to confirm restore: ", C.YELLOW))
    if confirm.strip().lower() != "yes":
        print("Cancelled.")
        return
    count = 0
    for f in latest.iterdir():
        if f.is_file():
            shutil.copy2(f, PROJECT_ROOT / f.name)
            count += 1
    print(color(f"✅ Restored {count} files from {latest.name}", C.GREEN))


# ─────────────────────────────────────────────────────────────────────────────
# REPORT PRINTING
# ─────────────────────────────────────────────────────────────────────────────

def print_header(dry_run):
    title = "DRY RUN — NOTHING WILL BE MODIFIED" if dry_run else "REFRESH RUN — APPLYING CHANGES"
    print()
    print(color("🐾 Balanced Ben Pets — refresh.py", C.BOLD + C.CYAN))
    print(color("─" * 50, C.DIM))
    print(color(title, C.BOLD + (C.YELLOW if dry_run else C.GREEN)))
    print(color("─" * 50, C.DIM))
    print()


def print_report(report, categories, post_files, dry_run):
    # ─── SCAN RESULTS ───
    print(color("📋 SCAN RESULTS", C.BOLD))
    print(f"   Found {len(post_files)} post-*.html files in root")
    total_in_json = sum(len(v) for v in categories.values())
    print(f"   {total_in_json} posts listed in categories.json")
    print(f"   {len(PARTIALS)} partials loaded from partials/")
    print()

    # ─── BY CATEGORY ───
    if categories:
        print(color("📊 BY CATEGORY", C.BOLD))
        for cat, posts in categories.items():
            print(f"   {cat.capitalize():10} {len(posts):3} posts")
        print()

    # ─── ORPHANS ───
    if report.orphans_on_disk:
        print(color(f"⚠️  POSTS NOT IN categories.json ({len(report.orphans_on_disk)})", C.YELLOW + C.BOLD))
        for f in report.orphans_on_disk:
            print(f"   {f}")
        print(color("   → Add these to data/categories.json", C.DIM))
        print()

    if report.orphans_in_json:
        print(color(f"⚠️  POSTS IN categories.json BUT NOT ON DISK ({len(report.orphans_in_json)})", C.YELLOW + C.BOLD))
        for f in report.orphans_in_json:
            print(f"   {f}")
        print()

    # ─── CLEAN FILES ───
    if report.posts_clean:
        print(color(f"✅ READY TO REFRESH ({len(report.posts_clean)} files)", C.GREEN + C.BOLD))
        for f in report.posts_clean[:10]:
            print(f"   {f}")
        if len(report.posts_clean) > 10:
            print(color(f"   ... and {len(report.posts_clean) - 10} more", C.DIM))
        print()

    # ─── ISSUES ───
    if report.posts_with_issues:
        print(color(f"⚠️  POSTS NEEDING ATTENTION ({len(report.posts_with_issues)})", C.YELLOW + C.BOLD))
        for filename, issues in report.posts_with_issues.items():
            print(f"   {color(filename, C.BOLD)}")
            for issue in issues:
                print(f"      └─ {issue}")
        print()

    # ─── AMAZON LINKS ───
    if report.amazon_links_total > 0:
        print(color("🔗 AMAZON LINKS AUDIT", C.BOLD))
        print(f"   {report.amazon_links_total} Amazon links found")
        print(color(f"   ✓ {report.amazon_links_ok} have rel='nofollow sponsored'", C.GREEN))
        if report.amazon_links_missing_rel:
            print(color(f"   ⚠ {len(report.amazon_links_missing_rel)} missing rel attributes", C.YELLOW))
            for filename, href in report.amazon_links_missing_rel[:5]:
                short_href = href if len(href) <= 50 else href[:47] + "..."
                print(color(f"      {filename}: {short_href}", C.DIM))
            if len(report.amazon_links_missing_rel) > 5:
                print(color(f"      ... and {len(report.amazon_links_missing_rel) - 5} more", C.DIM))
        if not dry_run and report.amazon_links_fixed > 0:
            print(color(f"   🔧 {report.amazon_links_fixed} links auto-fixed (added rel + target)", C.GREEN))
        if report.amazon_links_skipped_partial:
            total_skipped = sum(c for _, c in report.amazon_links_skipped_partial)
            print(color(f"   ⚠ {total_skipped} links skipped (had partial rel — fix manually):", C.YELLOW))
            for filename, count in report.amazon_links_skipped_partial[:5]:
                print(color(f"      {filename}: {count} link(s)", C.DIM))
        print()

    # ─── IMAGES ───
    if report.images_total > 0:
        print(color("🖼️  IMAGE AUDIT", C.BOLD))
        print(f"   {report.images_total} <img> tags scanned")
        if report.images_missing_alt:
            total_missing_alt = sum(c for _, c in report.images_missing_alt)
            print(color(f"   ⚠ {total_missing_alt} images missing alt across {len(report.images_missing_alt)} files", C.YELLOW))
        else:
            print(color("   ✓ All images have alt text", C.GREEN))
        if report.images_missing_dims:
            total_missing_dims = sum(c for _, c in report.images_missing_dims)
            print(color(f"   ⚠ {total_missing_dims} images missing width/height across {len(report.images_missing_dims)} files (causes CLS)", C.YELLOW))
        else:
            print(color("   ✓ All images have width/height", C.GREEN))
        print()

    # ─── OLD BRAND ───
    if report.old_brand_hits:
        print(color(f"🏷️  OLD BRAND MENTIONS ({len(report.old_brand_hits)} hits)", C.YELLOW + C.BOLD))
        seen = {}
        for filename, line_num, text in report.old_brand_hits:
            seen.setdefault(filename, []).append((line_num, text))
        for filename, hits in list(seen.items())[:5]:
            print(f"   {color(filename, C.BOLD)}")
            for line_num, text in hits[:3]:
                print(f"      line {line_num}: '{text}'")
        if len(seen) > 5:
            print(color(f"   ... and {len(seen) - 5} more files", C.DIM))
        print(color("   → These are inside markers and will be auto-replaced.", C.DIM))
        print(color("   → If outside markers, manual fix needed.", C.DIM))
        print()

    # ─── SUMMARY ───
    print(color("═" * 50, C.DIM))
    ready = len(report.posts_clean)
    issues = len(report.posts_with_issues)
    blocking = sum(1 for issues_list in report.posts_with_issues.values()
                   if any("missing" in i and "marker entirely" in i for i in issues_list))
    summary = f"SUMMARY: {color(str(ready), C.GREEN)} ready · {color(str(issues), C.YELLOW)} need attention · {color(str(blocking), C.RED)} blocking errors"
    print(summary)
    if dry_run:
        print(color("Run without --dry-run to apply changes.", C.DIM))
    print(color("═" * 50, C.DIM))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def process_file(path, partials, dry_run, report, fix_amazon=True):
    """Process a single file: audit + (if not dry-run) inject + write."""
    html = path.read_text(encoding="utf-8")
    filename = path.name

    # Run audits (always — populates report)
    audit_amazon_links(html, filename, report)
    audit_images(html, filename, report)
    audit_old_brand(html, filename, report)
    has_any_marker = audit_markers(html, filename, report)

    if not has_any_marker:
        # File has no markers — needs scaffolding, can't process
        return False

    # Determine if file is "clean" (no issues for this file)
    if filename not in report.posts_with_issues:
        report.posts_clean.append(filename)

    if dry_run:
        return True

    # Real run begins — start with the original HTML
    new_html = html

    # Auto-fix Amazon links (safe: only adds rel/target to links with NO existing rel)
    if fix_amazon:
        new_html, fixed, skipped = fix_amazon_links(new_html, filename, report)
        report.amazon_links_fixed += fixed
        if skipped > 0:
            report.amazon_links_skipped_partial.append((filename, skipped))

    # Extract per-post metadata for template substitution
    metadata = extract_post_metadata(new_html, filename)

    # Inject partials with metadata substitution
    for marker, content in partials.items():
        new_html, _ = inject_partial(new_html, marker, content, metadata)

    if new_html != html:
        path.write_text(new_html, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="Refresh shared partials across Balanced Ben Pets posts.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--only", help="Refresh only one specific file (e.g. post-can-dogs-talk.html)")
    parser.add_argument("--category", help="Refresh only files in one category (e.g. dogs)")
    parser.add_argument("--restore", action="store_true", help="Restore from latest backup")
    parser.add_argument("--no-fix-amazon", action="store_true",
                        help="Audit but do NOT auto-fix Amazon link rel attributes")
    args = parser.parse_args()

    if args.restore:
        restore_latest_backup()
        return

    print_header(args.dry_run)

    # Load everything
    partials = load_partials()
    categories = load_categories()
    unpublished = load_unpublished()
    all_posts = find_post_files()
    posts_in_json = set()
    for posts in categories.values():
        posts_in_json.update(posts)
    posts_on_disk = {p.name for p in all_posts}

    # Skip unpublished posts entirely
    if unpublished:
        skipped_unpub = unpublished & posts_on_disk
        if skipped_unpub:
            print(color(f"🚫 Skipping {len(skipped_unpub)} unpublished post(s):", C.DIM))
            for f in sorted(skipped_unpub):
                print(color(f"   {f}", C.DIM))
            print()
        all_posts = [p for p in all_posts if p.name not in unpublished]
        posts_on_disk = posts_on_disk - unpublished

    report = Report()
    # Orphans should not include unpublished posts
    report.orphans_on_disk = sorted(posts_on_disk - posts_in_json)
    report.orphans_in_json = sorted(posts_in_json - posts_on_disk)

    # Filter posts based on --only / --category
    if args.only:
        # --only can accept ANY HTML file (post, category page, or other)
        target_path = PROJECT_ROOT / args.only
        if not target_path.exists():
            print(color(f"❌ File not found: {args.only}", C.RED))
            sys.exit(1)
        posts_to_process = [target_path]
    elif args.category:
        cat_files = set(categories.get(args.category, []))
        posts_to_process = [p for p in all_posts if p.name in cat_files]
        if not posts_to_process:
            print(color(f"❌ No posts found in category '{args.category}'", C.RED))
            sys.exit(1)
    else:
        # Default: process ALL posts + ALL site pages with markers
        posts_to_process = list(all_posts) + find_site_pages()

    # Backup before real run (not dry-run)
    if not args.dry_run and posts_to_process:
        backup_path = make_backup(posts_to_process)
        print(color(f"💾 Backed up {len(posts_to_process)} files to: {backup_path.relative_to(PROJECT_ROOT)}", C.CYAN))
        print()

    # Process each file
    for path in posts_to_process:
        process_file(path, partials, args.dry_run, report, fix_amazon=not args.no_fix_amazon)

    # Print the report
    print_report(report, categories, posts_to_process, args.dry_run)


if __name__ == "__main__":
    main()
