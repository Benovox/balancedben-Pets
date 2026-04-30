#!/usr/bin/env python3

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageOps

# ========= CONFIG =========
SITE_ROOT = Path(".").resolve()
BACKUP_DIR = SITE_ROOT / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
POLISH_CSS_NAME = "visual-polish.css"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
HTML_EXTS = {".html", ".htm"}

MAX_WIDTH = 1600
JPEG_QUALITY = 82
WEBP_QUALITY = 80

SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
}

# ========= CSS =========
POLISH_CSS = """
body {
  line-height: 1.7;
  font-family: Arial, sans-serif;
}

main {
  max-width: 900px;
  margin: auto;
  padding: 16px;
}

h1, h2, h3 {
  line-height: 1.3;
}

img {
  max-width: 100%;
  border-radius: 12px;
}

.card {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

button {
  border-radius: 999px;
  padding: 10px 16px;
  cursor: pointer;
}

iframe {
  border-radius: 12px;
  width: 100%;
}
"""

# ========= FUNCTIONS =========

def backup_site():
    print("Creating backup...")
    shutil.copytree(SITE_ROOT, BACKUP_DIR, dirs_exist_ok=True)
    print("Backup created:", BACKUP_DIR)

def find_files(extensions):
    files = []
    for root, dirs, filenames in os.walk(SITE_ROOT):
        if any(skip in root for skip in SKIP_DIR_NAMES):
            continue
        for f in filenames:
            if Path(f).suffix.lower() in extensions:
                files.append(Path(root) / f)
    return files

def optimize_image(path):
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)

            if im.width > MAX_WIDTH:
                ratio = MAX_WIDTH / im.width
                im = im.resize((MAX_WIDTH, int(im.height * ratio)))

            if path.suffix.lower() in [".jpg", ".jpeg"]:
                im = im.convert("RGB")
                im.save(path, "JPEG", quality=JPEG_QUALITY)

            elif path.suffix.lower() == ".png":
                im.save(path, "PNG", optimize=True)

            elif path.suffix.lower() == ".webp":
                im.save(path, "WEBP", quality=WEBP_QUALITY)

            print("Optimized:", path)

    except Exception as e:
        print("Skipped:", path, e)

def write_css():
    css_path = SITE_ROOT / POLISH_CSS_NAME
    with open(css_path, "w") as f:
        f.write(POLISH_CSS)
    print("CSS created:", css_path)

def inject_css(html_path):
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if POLISH_CSS_NAME in content:
        return

    link_tag = f'<link rel="stylesheet" href="{POLISH_CSS_NAME}">\n'

    if "</head>" in content:
        content = content.replace("</head>", link_tag + "</head>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Updated:", html_path)

def main():
    backup_site()

    print("Optimizing images...")
    images = find_files(IMAGE_EXTS)
    for img in images:
        optimize_image(img)

    write_css()

    print("Updating HTML files...")
    html_files = find_files(HTML_EXTS)
    for html in html_files:
        inject_css(html)

    print("Done! Check your site before uploading.")

if __name__ == "__main__":
    main()