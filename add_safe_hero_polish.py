from pathlib import Path
import re

SITE_ROOT = Path(".")

CSS_FILE = "visual-polish.css"

HERO_CSS = """

/* === Safe hero polish for AdSense review === */
.hero,
.post-hero,
.hero-banner,
.hero-section,
.hero-wrap {
  position: relative;
  overflow: hidden;
  border-radius: 22px;
  margin: 1.2rem 0 1.8rem;
  box-shadow: 0 10px 28px rgba(0,0,0,.10);
}

.hero img,
.post-hero img,
.hero-banner img,
.hero-section img,
.hero-wrap img {
  display: block;
  width: 100%;
  height: clamp(260px, 42vw, 520px);
  object-fit: cover;
}

.hero::after,
.post-hero::after,
.hero-banner::after,
.hero-section::after,
.hero-wrap::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0,0,0,0.10) 0%,
    rgba(0,0,0,0.22) 45%,
    rgba(0,0,0,0.42) 100%
  );
  pointer-events: none;
}

.hero-content,
.post-hero-content,
.hero-text,
.hero-caption {
  position: absolute;
  left: clamp(16px, 3vw, 34px);
  right: clamp(16px, 3vw, 34px);
  bottom: clamp(16px, 3vw, 30px);
  z-index: 2;
  color: #fff;
}

.hero-content h1,
.post-hero-content h1,
.hero-text h1,
.hero-caption h1,
.hero h1,
.post-hero h1 {
  font-size: clamp(2rem, 4.8vw, 3.6rem);
  line-height: 1.08;
  letter-spacing: -0.03em;
  margin: 0 0 .5rem;
  color: #fff;
  text-shadow: 0 3px 14px rgba(0,0,0,.35);
  max-width: 12ch;
}

.hero-content p,
.post-hero-content p,
.hero-text p,
.hero-caption p,
.hero .meta,
.post-hero .meta {
  margin: 0;
  font-size: clamp(.98rem, 1.6vw, 1.1rem);
  color: rgba(255,255,255,.95);
  text-shadow: 0 2px 10px rgba(0,0,0,.30);
  max-width: 60ch;
}

@media (max-width: 768px) {
  .hero img,
  .post-hero img,
  .hero-banner img,
  .hero-section img,
  .hero-wrap img {
    height: 260px;
  }

  .hero-content h1,
  .post-hero-content h1,
  .hero-text h1,
  .hero-caption h1,
  .hero h1,
  .post-hero h1 {
    max-width: 100%;
  }
}
"""

def append_hero_css():
    css_path = SITE_ROOT / CSS_FILE
    if not css_path.exists():
        print(f"Missing {CSS_FILE}. Put this script in the same folder as visual-polish.css")
        return

    content = css_path.read_text(encoding="utf-8", errors="ignore")

    if "Safe hero polish for AdSense review" in content:
        print("Hero CSS already added.")
        return

    css_path.write_text(content.rstrip() + "\n\n" + HERO_CSS.strip() + "\n", encoding="utf-8")
    print(f"Updated: {css_path}")

def add_hero_meta_class():
    html_files = list(SITE_ROOT.rglob("*.html"))

    patterns = [
        r'(<header[^>]*class="[^"]*\bhero\b[^"]*"[^>]*>)',
        r'(<section[^>]*class="[^"]*\bhero\b[^"]*"[^>]*>)',
        r'(<div[^>]*class="[^"]*\bhero\b[^"]*"[^>]*>)',
        r'(<header[^>]*class="[^"]*\bpost-hero\b[^"]*"[^>]*>)',
        r'(<section[^>]*class="[^"]*\bpost-hero\b[^"]*"[^>]*>)',
        r'(<div[^>]*class="[^"]*\bpost-hero\b[^"]*"[^>]*>)',
    ]

    updated = 0

    for file_path in html_files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        original = content

        # If hero exists and H1 is inside hero but there is no hero-content wrapper,
        # add a helper class to common meta paragraph if present.
        if ('class="hero"' in content or 'class="post-hero"' in content):
            content = re.sub(
                r'(<p class="meta")',
                r'<p class="meta hero-meta"',
                content,
                count=1
            )

        if content != original:
            file_path.write_text(content, encoding="utf-8")
            updated += 1
            print(f"Checked/updated: {file_path}")

    print(f"HTML files touched: {updated}")

def main():
    append_hero_css()
    add_hero_meta_class()
    print("\nDone. Test locally before uploading.")

if __name__ == "__main__":
    main()