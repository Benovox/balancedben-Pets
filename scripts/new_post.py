#!/usr/bin/env python3
"""
Balanced Ben Pets — new_post.py
================================
Scaffolds a brand-new blog post with all markers, design hooks, and metadata
in place. After running this, you only need to write the article content.

USAGE
-----
    # Interactive mode (recommended) — asks for title, category, etc.
    python3 scripts/new_post.py

    # Quick mode — provide title and category as args
    python3 scripts/new_post.py --title "Why Dogs Sleep So Much" --category dogs

    # Dry-run — show what would be created without creating
    python3 scripts/new_post.py --dry-run --title "..." --category dogs

WHAT IT CREATES
---------------
1. A new file: post-{slug}.html in project root
   - All 5 markers in place (META, HEADER, DISCLOSURE, AUTHOR-BIO, FOOTER)
   - Design-system HTML structure (post-hero, breadcrumbs, article body)
   - Placeholder hero image (you replace with real image later)
   - Placeholder lead paragraph and section headings (you replace with content)

2. Auto-adds the new filename to data/categories.json under the chosen category

NEXT STEPS AFTER RUNNING
------------------------
1. Write your article content (replace placeholders)
2. Add a real hero image to assets/images/
3. Update meta description in markers (or run refresh.py later)
4. Run: python3 scripts/refresh.py --only post-{slug}.html  (to inject partials)
5. Run: python3 scripts/build_indexes.py  (to update blog/category pages)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CATEGORIES_FILE = DATA_DIR / "categories.json"

# Categories that exist as actual category pages (dogs.html, cats.html, exotic.html)
DISPLAY_CATEGORIES = ["dogs", "cats", "exotic"]
# Plus 'general' for cross-category posts that show on home/blog only
ALL_CATEGORIES = DISPLAY_CATEGORIES + ["general"]


# ─────────────────────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"; CYAN = "\033[36m"

def color(text, c):
    return f"{c}{text}{C.RESET}"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def slugify(title):
    """Convert 'Why Dogs Sleep So Much!' → 'why-dogs-sleep-so-much'"""
    s = title.lower().strip()
    # Replace any non-alphanumeric with hyphen
    s = re.sub(r"[^a-z0-9]+", "-", s)
    # Trim hyphens from start/end
    s = s.strip("-")
    # Collapse multiple hyphens
    s = re.sub(r"-+", "-", s)
    return s


def category_label(cat):
    """Display name for a category."""
    return {
        "dogs": "Dogs",
        "cats": "Cats",
        "exotic": "Exotic & Other Pets",
        "general": "General",
    }.get(cat, cat.capitalize())


def category_page(cat):
    """Filename of the category landing page."""
    if cat == "general":
        return "blog.html"
    return f"{cat}.html"


# ─────────────────────────────────────────────────────────────────────────────
# POST TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

def build_post_html(title, category, slug, description, hero_image):
    """Build the new post HTML with all markers and design structure in place."""
    today = datetime.now().strftime("%B %d, %Y")
    today_iso = datetime.now().strftime("%Y-%m-%d")
    cat_label = category_label(category)
    cat_page = category_page(category)

    # The breadcrumb skips category for 'general' posts
    if category == "general":
        breadcrumb_html = f'<a href="index.html">Home</a><span class="sep">›</span><a href="blog.html">Blog</a><span class="sep">›</span>{title}'
    else:
        breadcrumb_html = f'<a href="index.html">Home</a><span class="sep">›</span><a href="{cat_page}">{cat_label}</a><span class="sep">›</span>{title}'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<!-- META:START -->
<!-- (placeholder — refresh.py will inject the real meta tags here) -->
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title} | Balanced Ben Pets</title>
<meta name="description" content="{description}" />
<link rel="stylesheet" href="assets/css/style.css">
<!-- META:END -->
</head>
<body>

<!-- HEADER:START -->
<!-- (placeholder — refresh.py will inject the real header here) -->
<!-- HEADER:END -->

<section class="post-hero-wrap">
  <div class="breadcrumb">
    {breadcrumb_html}
  </div>

  <div class="post-hero">
    <img src="{hero_image}" alt="{title}" width="1100" height="560" />
    <div class="post-hero-content">
      <span class="category-tag">{cat_label}</span>
      <h1>{title}</h1>
      <div class="meta-line">
        <div class="author-thumb">BL</div>
        <span><strong>Breno Leite</strong></span>
        <span class="dot">·</span>
        <span>{today}</span>
        <span class="dot">·</span>
        <span><time datetime="{today_iso}">Updated today</time></span>
      </div>
    </div>
  </div>
</section>

<article class="post">
<!-- DISCLOSURE:START -->
<!-- (placeholder — refresh.py will inject the affiliate disclosure here) -->
<!-- DISCLOSURE:END -->

  <p class="lead">
    [LEAD PARAGRAPH] Replace this with a 2–3 sentence opening that hooks the reader.
    Speak directly to the question or pain point this post addresses.
  </p>

  <h2>[Section Heading 1]</h2>

  <p>
    [Replace with body content. Aim for 3–6 paragraphs per section. Include
    real examples, specific advice, and where relevant, gentle Amazon affiliate
    links using rel="nofollow sponsored" target="_blank".]
  </p>

  <h2>[Section Heading 2]</h2>

  <p>
    [Continue article. Keep paragraphs tight. Use lists where it helps.]
  </p>

  <ul>
    <li><strong>Point one:</strong> short explanation</li>
    <li><strong>Point two:</strong> short explanation</li>
    <li><strong>Point three:</strong> short explanation</li>
  </ul>

  <h2>[Section Heading 3]</h2>

  <p>
    [Wrap with a practical takeaway, a gentle product recommendation if relevant,
    or a question that invites the reader to reflect.]
  </p>

<!-- AUTHOR-BIO:START -->
<!-- (placeholder — refresh.py will inject the author bio here) -->
<!-- AUTHOR-BIO:END -->
</article>

<!-- FOOTER:START -->
<!-- (placeholder — refresh.py will inject the real footer here) -->
<!-- FOOTER:END -->

</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES.JSON UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def add_to_categories(filename, category, dry_run=False):
    """Add the new post to categories.json under the chosen category."""
    if not CATEGORIES_FILE.exists():
        print(color(f"⚠️  No categories.json at {CATEGORIES_FILE}", C.YELLOW))
        return False

    data = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))

    if category not in data:
        data[category] = []

    if filename in data[category]:
        print(color(f"   already in categories.json under '{category}'", C.DIM))
        return True

    # Check if it exists in another category (avoid duplicates across categories)
    for other_cat, posts in data.items():
        if other_cat.startswith("_"):
            continue
        if filename in posts and other_cat != category:
            print(color(f"⚠️  Already in '{other_cat}' — won't add to '{category}' too", C.YELLOW))
            return False

    data[category].append(filename)
    data[category].sort()

    if dry_run:
        print(color(f"   [dry-run] would add to '{category}' in categories.json", C.DIM))
        return True

    CATEGORIES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(color(f"   ✓ added to '{category}' in categories.json", C.GREEN))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

def prompt(question, default=None, choices=None):
    """Ask the user a question. Returns their answer or default."""
    suffix = ""
    if choices:
        suffix = f" [{'/'.join(choices)}]"
    if default:
        suffix += f" (default: {default})"
    answer = input(color(f"  {question}{suffix}: ", C.CYAN)).strip()
    if not answer and default is not None:
        return default
    if choices and answer.lower() not in choices:
        print(color(f"  Please choose one of: {', '.join(choices)}", C.YELLOW))
        return prompt(question, default, choices)
    return answer


def interactive_setup():
    """Walk the user through creating a new post."""
    print()
    print(color("📝 New Post — Interactive Setup", C.BOLD + C.CYAN))
    print(color("─" * 50, C.DIM))
    print()

    title = prompt("Post title")
    while not title:
        title = prompt("Title is required. Post title")

    suggested_slug = slugify(title)
    slug = prompt("URL slug", default=suggested_slug)
    slug = slugify(slug)  # normalize whatever they typed

    print()
    print(color("  Categories:", C.DIM))
    print(color("    dogs    — appears on dogs.html", C.DIM))
    print(color("    cats    — appears on cats.html", C.DIM))
    print(color("    exotic  — appears on exotic.html", C.DIM))
    print(color("    general — appears on home/blog only (cross-category posts)", C.DIM))
    print()
    category = prompt("Category", choices=ALL_CATEGORIES)

    description = prompt("Short description (1–2 sentences for SEO/social)",
                         default=f"{title} — a practical guide from Balanced Ben Pets.")

    hero_image = prompt("Hero image path", default=f"assets/images/{slug}.jpg")

    return {
        "title": title,
        "slug": slug,
        "category": category,
        "description": description,
        "hero_image": hero_image,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scaffold a new blog post.")
    parser.add_argument("--title", help="Post title (skips interactive prompt)")
    parser.add_argument("--slug", help="URL slug (default: derived from title)")
    parser.add_argument("--category", choices=ALL_CATEGORIES, help="Category")
    parser.add_argument("--description", help="Short SEO/social description")
    parser.add_argument("--hero-image", help="Hero image path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    parser.add_argument("--force", action="store_true", help="Overwrite if file exists")
    args = parser.parse_args()

    # Interactive mode if no title given
    if not args.title:
        try:
            cfg = interactive_setup()
        except (KeyboardInterrupt, EOFError):
            print(color("\nCancelled.", C.YELLOW))
            sys.exit(0)
    else:
        if not args.category:
            print(color("❌ --category is required when using --title", C.RED))
            sys.exit(1)
        cfg = {
            "title": args.title,
            "slug": args.slug or slugify(args.title),
            "category": args.category,
            "description": args.description or f"{args.title} — a practical guide from Balanced Ben Pets.",
            "hero_image": args.hero_image or f"assets/images/{args.slug or slugify(args.title)}.jpg",
        }

    filename = f"post-{cfg['slug']}.html"
    output_path = PROJECT_ROOT / filename

    print()
    print(color("📋 Post details:", C.BOLD))
    print(f"   Title:       {cfg['title']}")
    print(f"   Slug:        {cfg['slug']}")
    print(f"   Filename:    {filename}")
    print(f"   Category:    {cfg['category']} ({category_label(cfg['category'])})")
    print(f"   Description: {cfg['description']}")
    print(f"   Hero image:  {cfg['hero_image']}")
    print()

    # File exists check
    if output_path.exists() and not args.force:
        print(color(f"❌ File already exists: {filename}", C.RED))
        print(color("   Use --force to overwrite (NOT recommended for existing posts).", C.DIM))
        sys.exit(1)

    if args.dry_run:
        print(color("DRY RUN — no file created", C.YELLOW))
        add_to_categories(filename, cfg['category'], dry_run=True)
        print()
        print(color("Run without --dry-run to create the post.", C.DIM))
        return

    # Build and write the post
    html = build_post_html(
        title=cfg['title'],
        category=cfg['category'],
        slug=cfg['slug'],
        description=cfg['description'],
        hero_image=cfg['hero_image'],
    )
    output_path.write_text(html, encoding="utf-8")
    print(color(f"✓ Created: {filename}", C.GREEN))

    # Add to categories.json
    add_to_categories(filename, cfg['category'])

    # Next-step guidance
    print()
    print(color("Next steps:", C.BOLD + C.CYAN))
    print(f"   1. Open {filename} and write your article content")
    print(f"   2. Add hero image to: {cfg['hero_image']}")
    print(f"   3. Run: {color(f'python3 scripts/refresh.py --only {filename}', C.CYAN)}")
    print(f"   4. Run: {color('python3 scripts/build_indexes.py', C.CYAN)}  (to update blog/category pages)")
    print()


if __name__ == "__main__":
    main()
