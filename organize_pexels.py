#!/usr/bin/env python3
"""
organize_pexels.py — Rename Pexels downloads, move to /images, print URLs.

Usage:
    python3 organize_pexels.py <post-slug> [role1 role2 role3 ...]

Examples:
    # Auto-assign default roles (hero, body-1, body-2, ..., cta)
    python3 organize_pexels.py puppy-training

    # Specify exact roles in order (matches files by download time, oldest first)
    python3 organize_pexels.py puppy-training hero body-sit body-heel body-reward cta

Notes:
    - Scans ~/Downloads for pexels-*.{jpg,jpeg,png,webp}
    - Files are matched to roles in modified-time order (oldest first)
    - Renames to <slug>-<role>.<ext>, moves to ./images/, prints <img> URLs
"""
import sys
import shutil
from pathlib import Path

DOWNLOADS = Path.home() / "Downloads"
IMAGES_DIR = Path(__file__).parent / "images"
DEFAULT_ROLES = ["hero", "body-1", "body-2", "body-3", "body-4",
                 "body-5", "body-6", "body-7", "cta"]
EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    slug = sys.argv[1].strip().lower().replace(" ", "-")
    roles = sys.argv[2:] if len(sys.argv) > 2 else DEFAULT_ROLES

    # Find pexels files, sorted by modified time (oldest first)
    pexels_files = sorted(
        [f for f in DOWNLOADS.iterdir()
         if f.is_file()
         and f.name.lower().startswith("pexels")
         and f.suffix.lower() in EXTS],
        key=lambda f: f.stat().st_mtime
    )

    if not pexels_files:
        print(f"No pexels-* images found in {DOWNLOADS}")
        sys.exit(0)

    if len(pexels_files) > len(roles):
        print(f"Warning: {len(pexels_files)} files but only {len(roles)} roles. "
              f"Extras will be numbered body-N.")
        # Pad roles with body-N for any overflow
        n = len(roles)
        while len(roles) < len(pexels_files):
            n += 1
            roles.append(f"body-{n}")

    IMAGES_DIR.mkdir(exist_ok=True)
    urls = []
    print(f"\nOrganizing {len(pexels_files)} image(s) for post: {slug}\n")

    for src, role in zip(pexels_files, roles):
        ext = src.suffix.lower()
        # Normalize .jpg -> .jpeg for consistency with your example
        if ext == ".jpg":
            ext = ".jpeg"
        new_name = f"{slug}-{role}{ext}"
        dst = IMAGES_DIR / new_name

        # Avoid overwriting
        counter = 2
        while dst.exists():
            new_name = f"{slug}-{role}-{counter}{ext}"
            dst = IMAGES_DIR / new_name
            counter += 1

        shutil.move(str(src), str(dst))
        url = f"/images/{new_name}"
        urls.append((new_name, url))
        print(f"  {src.name}  ->  {new_name}")

    print("\n--- URLs ready to paste ---")
    for name, url in urls:
        print(url)

    print("\n--- <img> tags ---")
    for name, url in urls:
        alt = name.rsplit(".", 1)[0].replace("-", " ")
        print(f'<img src="{url}" alt="{alt}" loading="lazy" />')


if __name__ == "__main__":
    main()
