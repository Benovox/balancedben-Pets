#!/usr/bin/env python3
"""
Balanced Ben Pets — build_indexes.py
=====================================
Auto-generates the homepage post grid, blog index, category landing pages,
and sitemap.xml — all from categories.json + per-post metadata.

USAGE
-----
    python3 scripts/build_indexes.py --dry-run    # preview, generate nothing
    python3 scripts/build_indexes.py              # generate all index pages
    python3 scripts/build_indexes.py --only blog  # generate only blog.html
    python3 scripts/build_indexes.py --only sitemap  # generate only sitemap.xml

WHAT IT GENERATES
-----------------
1. blog.html        — all posts grouped by category, sorted newest first
2. dogs.html        — Dogs category landing page
3. cats.html        — Cats category landing page
4. exotic.html      — Exotic & Other Pets landing page
5. sitemap.xml      — all URLs for Google

WHAT IT DOES NOT TOUCH
----------------------
- Individual post files (those are managed by refresh.py)
- index.html (homepage stays under your manual control — but generates a
  drop-in fragment you can paste into it)
- about.html, contact.html, privacy.html, etc.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CATEGORIES_FILE = DATA_DIR / "categories.json"

SITE_URL = "https://balancedben.com"

CATEGORY_INFO = {
    "dogs": {
        "label": "Dogs",
        "emoji": "🐶",
        "slug": "dogs",
        "intro": "Practical, science-aware guides for dog owners — from training and nutrition to communication and senior care. Written by Breno, who shares his life with two Maltese rescues, Bonnie and Bellina.",
    },
    "cats": {
        "label": "Cats",
        "emoji": "🐱",
        "slug": "cats",
        "intro": "Honest cat care: nutrition, behavior, and the things that make our feline companions tick. No fluff, no clickbait — just practical advice from one cat-loving owner to another.",
    },
    "exotic": {
        "label": "Exotic & Other Pets",
        "emoji": "🦜",
        "slug": "exotic",
        "intro": "From aquariums and parrots to capybaras and comfort animals — thoughtful guides about the pets less commonly written about, with honest takes on what owning them actually involves.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"; CYAN = "\033[36m"

def color(text, c):
    return f"{c}{text}{C.RESET}"


def smart_truncate(text, max_chars=155):
    """Truncate text at word boundary, never cutting mid-word.
    Returns text with no trailing partial words and a soft '…' if truncated."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # Cut at max_chars, then walk back to last whitespace
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    # Strip trailing punctuation that would look weird before ellipsis
    truncated = truncated.rstrip(",;:.-—– ")
    return truncated + "…"


# ─────────────────────────────────────────────────────────────────────────────
# METADATA EXTRACTION (per post)
# ─────────────────────────────────────────────────────────────────────────────

def extract_post_card_data(path):
    """Extract title, description, image, date, read-time from a single post file.
    Returns dict ready to pass into the card template."""
    if not path.exists():
        return None

    html = path.read_text(encoding="utf-8")

    # Title
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        title = re.sub(r"\s*\|\s*Balanced Ben Pets\s*$", "", title)
        title = re.sub(r"\s*-\s*Paws\s*&amp;?\s*Whiskers\s*$", "", title, flags=re.IGNORECASE)
    else:
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1:
            title = re.sub(r"<[^>]+>", "", h1.group(1)).strip()
        else:
            title = path.stem.replace("post-", "").replace("-", " ").title()

    # Description
    desc_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    )
    description = desc_match.group(1).strip() if desc_match else ""
    if not description:
        # Fallback: try to grab first paragraph from article body
        para = re.search(r'<p[^>]*class="lead"[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        if para:
            description = re.sub(r"<[^>]+>", "", para.group(1)).strip()
    # Always truncate to ~155 chars on word boundary for clean card excerpts
    description = smart_truncate(description, 155) if description else ""

    # Hero image — try post-hero <img>, then any <img>
    image = ""
    hero_img = re.search(
        r'class="post-hero"[^>]*>\s*.*?<img\s+[^>]*src=["\']([^"\']+)["\']',
        html, re.DOTALL
    )
    if hero_img:
        image = hero_img.group(1)
    else:
        any_img = re.search(r'<img\s+[^>]*src=["\']([^"\']+)["\']', html)
        if any_img:
            image = any_img.group(1)
    if not image:
        image = "assets/images/default-hero.jpg"

    # Date — same priority as refresh.py
    date_str = None
    schema = re.search(r'"datePublished"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2})', html)
    if schema:
        date_str = schema.group(1)
    if not date_str:
        og = re.search(
            r'<meta\s+property=["\']article:published_time["\']\s+content=["\']([0-9]{4}-[0-9]{2}-[0-9]{2})',
            html, re.IGNORECASE
        )
        if og:
            date_str = og.group(1)
    if not date_str:
        time_tag = re.search(
            r'<time\s+[^>]*datetime=["\']([0-9]{4}-[0-9]{2}-[0-9]{2})',
            html, re.IGNORECASE
        )
        if time_tag:
            date_str = time_tag.group(1)
    if not date_str:
        date_str = "2026-01-01"  # safe fallback for sorting

    # Date modified — for sitemap. Falls back to date_published if not found.
    date_modified = None
    schema_mod = re.search(r'"dateModified"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2})', html)
    if schema_mod:
        date_modified = schema_mod.group(1)
    if not date_modified:
        og_mod = re.search(
            r'<meta\s+property=["\']article:modified_time["\']\s+content=["\']([0-9]{4}-[0-9]{2}-[0-9]{2})',
            html, re.IGNORECASE
        )
        if og_mod:
            date_modified = og_mod.group(1)
    if not date_modified:
        date_modified = date_str  # fall back to published date

    # Read time estimate from article body word count
    body_match = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL | re.IGNORECASE)
    body_text = body_match.group(1) if body_match else html
    body_text = re.sub(r"<[^>]+>", " ", body_text)
    word_count = len(body_text.split())
    read_minutes = max(2, round(word_count / 220))  # ~220 wpm reading pace

    return {
        "filename": path.name,
        "title": title,
        "description": description or f"Read more about {title.lower()}.",
        "image": image,
        "date": date_str,
        "date_modified": date_modified,
        "date_human": format_date_human(date_str),
        "word_count": word_count,
        "read_time": f"{read_minutes} min read",
    }


def format_date_human(iso_date):
    """Convert '2026-04-30' → 'April 30, 2026'."""
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except Exception:
        return iso_date


# ─────────────────────────────────────────────────────────────────────────────
# HTML TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

def render_card(post, category_label, category_slug):
    """Render a single post card."""
    return f"""    <article class="card">
      <a href="{post['filename']}" class="card-image-link">
        <div class="card-image">
          <img src="{post['image']}" alt="{post['title']}" loading="lazy" width="400" height="250" />
        </div>
      </a>
      <div class="card-body">
        <a href="{category_slug}.html" class="card-category">{category_label}</a>
        <h3 class="card-title"><a href="{post['filename']}">{post['title']}</a></h3>
        <p class="card-excerpt">{post['description']}</p>
        <div class="card-meta">{post['date_human']} · {post['read_time']}</div>
      </div>
    </article>"""


def render_card_grid(posts, category_label, category_slug):
    """Render a card grid for a list of posts."""
    if not posts:
        return f'<p class="text-center text-muted">No posts yet in {category_label}.</p>'
    cards = "\n".join(render_card(p, category_label, category_slug) for p in posts)
    return f'<div class="card-grid">\n{cards}\n  </div>'


def render_category_page(category_key, posts):
    """Render a full category landing page."""
    info = CATEGORY_INFO[category_key]
    label = info["label"]
    intro = info["intro"]
    emoji = info["emoji"]
    cards_html = render_card_grid(posts, label, info["slug"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<!-- META:START -->
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{label} — Balanced Ben Pets</title>
<meta name="description" content="{smart_truncate(intro, 155)}" />
<link rel="canonical" href="{SITE_URL}/{info['slug']}.html" />
<link rel="stylesheet" href="assets/css/style.css">
<!-- META:END -->
</head>
<body>

<!-- HEADER:START -->
<!-- (placeholder — refresh.py will inject the real header here) -->
<!-- HEADER:END -->

<main>
  <section class="category-hero text-center" style="margin: 3rem auto 1rem; max-width: 720px;">
    <div style="font-size: 3rem; margin-bottom: 0.5rem;">{emoji}</div>
    <h1 class="section-title" style="margin-top: 0;">{label}</h1>
    <p class="section-subtitle">{intro}</p>
  </section>

  <section style="margin: 2rem 0 4rem;">
    {cards_html}
  </section>
</main>

<!-- FOOTER:START -->
<!-- (placeholder — refresh.py will inject the real footer here) -->
<!-- FOOTER:END -->

</body>
</html>
"""


def render_blog_page(categories_data):
    """Render the full blog.html — all posts grouped by category."""
    sections = []
    for cat_key in ["dogs", "cats", "exotic"]:
        posts = categories_data.get(cat_key, [])
        if not posts:
            continue
        info = CATEGORY_INFO[cat_key]
        cards = render_card_grid(posts, info["label"], info["slug"])
        sections.append(f"""
  <section style="margin: 4rem 0;">
    <div class="text-center" style="margin-bottom: 1.5rem;">
      <h2 class="section-title">{info['emoji']} {info['label']}</h2>
      <a href="{info['slug']}.html" class="btn-ghost">View all {info['label'].lower()} →</a>
    </div>
    {cards}
  </section>""")

    # General posts at the bottom (cross-category)
    general_posts = categories_data.get("general", [])
    if general_posts:
        cards = render_card_grid(general_posts, "All Pets", "blog")
        sections.append(f"""
  <section style="margin: 4rem 0;">
    <div class="text-center" style="margin-bottom: 1.5rem;">
      <h2 class="section-title">📋 General Guides</h2>
      <p class="section-subtitle">Cross-category articles for any pet parent.</p>
    </div>
    {cards}
  </section>""")

    body_inner = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<!-- META:START -->
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Blog — Balanced Ben Pets</title>
<meta name="description" content="All articles on Balanced Ben Pets — practical, science-aware pet care guides for dogs, cats, and exotic pets." />
<link rel="canonical" href="{SITE_URL}/blog.html" />
<link rel="stylesheet" href="assets/css/style.css">
<!-- META:END -->
</head>
<body>

<!-- HEADER:START -->
<!-- (placeholder — refresh.py will inject the real header here) -->
<!-- HEADER:END -->

<main>
  <section class="text-center" style="margin: 3rem auto 1rem; max-width: 720px;">
    <h1 class="section-title">All Stories</h1>
    <p class="section-subtitle">Practical guides written by Breno, with Bonnie and Bellina at his feet.</p>
  </section>
{body_inner}
</main>

<!-- FOOTER:START -->
<!-- (placeholder — refresh.py will inject the real footer here) -->
<!-- FOOTER:END -->

</body>
</html>
"""


def render_sitemap(post_data_with_dates):
    """Render sitemap.xml with per-post lastmod dates.

    post_data_with_dates: list of dicts with 'filename' and 'date' keys.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    urls = []

    # Static priority pages — use today (these change with site updates)
    static_pages = [
        ("", "1.0", "weekly"),
        ("blog.html", "0.9", "weekly"),
        ("dogs.html", "0.9", "weekly"),
        ("cats.html", "0.9", "weekly"),
        ("exotic.html", "0.9", "weekly"),
        ("about.html", "0.8", "monthly"),
        ("contact.html", "0.7", "monthly"),
        ("privacy.html", "0.5", "yearly"),
        ("disclaimer.html", "0.5", "yearly"),
        ("terms.html", "0.5", "yearly"),
    ]
    for path, priority, freq in static_pages:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/{path}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>""")

    # Posts — use each post's actual date (publish or modified)
    sorted_posts = sorted(post_data_with_dates, key=lambda p: p['filename'])
    for post in sorted_posts:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/{post['filename']}</loc>
    <lastmod>{post['date']}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""")

    body = "\n".join(urls)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""


def render_homepage_fragment(categories_data):
    """Render a 'Latest Stories' grid that user can paste into index.html.
    Picks the 6 most recent posts across all categories."""
    all_posts = []
    for cat_key, posts in categories_data.items():
        if cat_key.startswith("_"):
            continue
        for p in posts:
            all_posts.append((cat_key, p))

    # Sort by date (newest first)
    all_posts.sort(key=lambda x: x[1]["date"], reverse=True)
    latest = all_posts[:6]

    cards = []
    for cat_key, post in latest:
        info = CATEGORY_INFO.get(cat_key, {"label": cat_key.title(), "slug": cat_key})
        cards.append(render_card(post, info["label"], info["slug"]))

    cards_html = "\n".join(cards)
    return f"""<!--
  HOMEPAGE FRAGMENT — paste this <section> into your index.html
  where you want the "Latest Stories" grid to appear.
  Regenerate by running: python3 scripts/build_indexes.py
-->
<section class="latest-stories">
  <div class="text-center">
    <h2 class="section-title">Latest Stories</h2>
    <p class="section-subtitle">Practical, science-aware pet care from Breno, Bonnie, and Bellina.</p>
  </div>

  <div class="card-grid">
{cards_html}
  </div>

  <div class="text-center" style="margin-top: 2rem;">
    <a href="blog.html" class="btn btn-primary">View all stories</a>
  </div>
</section>
"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILD LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def load_categories():
    if not CATEGORIES_FILE.exists():
        print(color(f"❌ {CATEGORIES_FILE} not found", C.RED))
        sys.exit(1)
    return json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))


def gather_post_data(categories_raw):
    """For each category, replace filenames with full post-data dicts."""
    enriched = {}
    missing = []
    unpublished = set(categories_raw.get("_unpublished", []))

    for cat_key, posts in categories_raw.items():
        if cat_key.startswith("_") or not isinstance(posts, list):
            continue
        post_objs = []
        for filename in posts:
            if filename in unpublished:
                continue
            path = PROJECT_ROOT / filename
            data = extract_post_card_data(path)
            if data is None:
                missing.append(filename)
            else:
                post_objs.append(data)
        # Sort newest first
        post_objs.sort(key=lambda p: p["date"], reverse=True)
        enriched[cat_key] = post_objs
    return enriched, missing


def main():
    parser = argparse.ArgumentParser(description="Build blog/category/sitemap index pages.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--only", choices=["blog", "categories", "sitemap", "homepage"],
                        help="Generate only one type of output")
    args = parser.parse_args()

    print()
    print(color("🐾 Balanced Ben Pets — build_indexes.py", C.BOLD + C.CYAN))
    print(color("─" * 50, C.DIM))
    title = "DRY RUN — NOTHING WILL BE WRITTEN" if args.dry_run else "BUILD RUN"
    print(color(title, C.BOLD + (C.YELLOW if args.dry_run else C.GREEN)))
    print(color("─" * 50, C.DIM))
    print()

    categories_raw = load_categories()
    enriched, missing = gather_post_data(categories_raw)

    # Stats
    print(color("📊 POST DATA EXTRACTED", C.BOLD))
    total = 0
    for cat_key, posts in enriched.items():
        info = CATEGORY_INFO.get(cat_key, {"label": cat_key.title()})
        label = info["label"]
        print(f"   {label:25} {len(posts):3} posts")
        total += len(posts)
    print(f"   {'TOTAL':25} {total:3} posts")
    print()

    if missing:
        print(color(f"⚠️  MISSING FILES ({len(missing)})", C.YELLOW + C.BOLD))
        for f in missing:
            print(f"   {f}")
        print(color("   → These are in categories.json but the files don't exist on disk", C.DIM))
        print()

    # ─── Generate outputs ───
    outputs = []

    # Category pages
    if args.only in (None, "categories"):
        for cat_key in ["dogs", "cats", "exotic"]:
            posts = enriched.get(cat_key, [])
            html = render_category_page(cat_key, posts)
            outputs.append((PROJECT_ROOT / f"{cat_key}.html", html, f"{cat_key}.html ({len(posts)} posts)"))

    # Blog index
    if args.only in (None, "blog"):
        html = render_blog_page(enriched)
        total_blog = sum(len(p) for p in enriched.values())
        outputs.append((PROJECT_ROOT / "blog.html", html, f"blog.html ({total_blog} posts)"))

    # Sitemap
    if args.only in (None, "sitemap"):
        post_objs = []
        for posts in enriched.values():
            for p in posts:
                # Use date_modified (most recent timestamp) for accurate sitemap signals
                post_objs.append({"filename": p["filename"], "date": p["date_modified"]})
        xml = render_sitemap(post_objs)
        outputs.append((PROJECT_ROOT / "sitemap.xml", xml, f"sitemap.xml ({len(post_objs)} posts + 10 static)"))

    # Homepage fragment
    if args.only in (None, "homepage"):
        fragment = render_homepage_fragment(enriched)
        outputs.append((PROJECT_ROOT / "_homepage-fragment.html", fragment, "_homepage-fragment.html (paste into index.html)"))

    # Print/write
    print(color("📄 OUTPUTS", C.BOLD))
    for path, content, label in outputs:
        if args.dry_run:
            print(color(f"   [dry-run] would write: {label}", C.DIM))
        else:
            path.write_text(content, encoding="utf-8")
            print(color(f"   ✓ wrote: {label}", C.GREEN))

    print()
    print(color("═" * 50, C.DIM))
    if args.dry_run:
        print(color("Run without --dry-run to generate files.", C.DIM))
    else:
        print(color("Next: run python3 scripts/refresh.py to inject header/footer into category pages.", C.CYAN))
    print(color("═" * 50, C.DIM))
    print()


if __name__ == "__main__":
    main()
