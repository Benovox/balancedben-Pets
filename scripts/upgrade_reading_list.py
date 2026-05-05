#!/usr/bin/env python3
"""
upgrade_reading_list.py
Converts old <h3>Related Reading</h3><ul>...<li> pattern
to new <h2>More Reading</h2><div class="reading-list"> card style.

Usage:
  python3 scripts/upgrade_reading_list.py --dry-run
  python3 scripts/upgrade_reading_list.py
  python3 scripts/upgrade_reading_list.py --only post-puppy-training-timeline.html
"""

import re
import os
import glob
import shutil
import argparse
from datetime import datetime

def backup(files):
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_dir = f"_backup/{stamp}_reading-list"
    os.makedirs(backup_dir, exist_ok=True)
    for f in files:
        shutil.copy2(f, backup_dir)
    print(f"💾 Backed up {len(files)} files to: {backup_dir}")

def parse_li(li_html):
    """Extract href, title, description from a <li><a href="...">Title</a> — desc</li>"""
    # With dash/mdash separator
    match = re.search(r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>\s*(?:&mdash;|[—–-]+)\s*(.+)', li_html, re.DOTALL)
    if match:
        href = match.group(1).strip()
        title = match.group(2).strip()
        desc = re.sub(r'\s+', ' ', match.group(3).strip())
        return href, title, desc
    # Without separator — description follows link directly as remaining text
    match2 = re.search(r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>(.*)', li_html, re.DOTALL)
    if match2:
        href = match2.group(1).strip()
        title = match2.group(2).strip()
        desc = re.sub(r'\s+', ' ', match2.group(3).strip()).strip(' .,')
        return href, title, desc if desc else ""
    return None, None, None

def build_card(href, title, desc):
    if desc:
        return f'    <a href="{href}">\n      <strong>{title}</strong>\n      {desc}\n    </a>'
    else:
        return f'    <a href="{href}">\n      <strong>{title}</strong>\n    </a>'

def upgrade_content(content, filename):
    """Find and replace old Related Reading pattern with new card style."""

    # Pattern: <h2|h3> starting with Related/More Reading (any suffix) optionally followed by <p> then <ul>
    pattern = re.compile(
        r'<h[23][^>]*>\s*(?:Related|More) Reading[^<]*</h[23]>\s*(?:<p>[^<]*</p>\s*)?<ul>(.*?)</ul>',
        re.DOTALL | re.IGNORECASE
    )

    matches = list(pattern.finditer(content))
    if not matches:
        return content, False

    new_content = content
    offset = 0

    for match in matches:
        ul_inner = match.group(1)
        li_items = re.findall(r'<li>(.*?)</li>', ul_inner, re.DOTALL)

        cards = []
        for li in li_items:
            href, title, desc = parse_li(li.strip())
            if href and title:
                cards.append(build_card(href, title, desc))

        if not cards:
            continue

        cards_html = '\n'.join(cards)
        new_block = (
            f'<h2>More Reading</h2>\n'
            f'  <p>\n'
            f'    These guides pair well with this topic:\n'
            f'  </p>\n\n'
            f'  <div class="reading-list">\n'
            f'{cards_html}\n'
            f'  </div>'
        )

        start = match.start() + offset
        end = match.end() + offset
        new_content = new_content[:start] + new_block + new_content[end:]
        offset += len(new_block) - (end - start - offset + offset)

    changed = new_content != content
    return new_content, changed

def main():
    parser = argparse.ArgumentParser(description="Upgrade Related Reading sections to card style.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    parser.add_argument("--only", help="Process only one file")
    args = parser.parse_args()

    print("🐾 Balanced Ben Pets — upgrade_reading_list.py")
    print("─" * 50)
    if args.dry_run:
        print("DRY RUN — NOTHING WILL BE MODIFIED")
    else:
        print("UPGRADE RUN — APPLYING CHANGES")
    print("─" * 50)

    if args.only:
        files = [args.only] if os.path.exists(args.only) else []
    else:
        files = sorted(glob.glob("post-*.html"))

    print(f"\n📋 Found {len(files)} file(s)\n")

    to_modify = []
    results = []

    for f in files:
        content = open(f, encoding="utf-8").read()
        new_content, changed = upgrade_content(content, f)

        if changed:
            to_modify.append(f)
            results.append((f, "✓ upgraded"))
        else:
            # Check if already has reading-list style
            if 'class="reading-list"' in content:
                results.append((f, "· already upgraded, skipped"))
            elif "Related Reading" not in content and "More Reading" not in content:
                results.append((f, "· no related reading section found"))
            else:
                results.append((f, "⚠ pattern not matched — manual review needed"))

    for f, status in results:
        print(f"   {status}: {f}")

    print(f"\n{'=' * 50}")
    upgraded = len(to_modify)
    skipped = len([r for r in results if "skipped" in r[1]])
    no_section = len([r for r in results if "no related" in r[1]])
    manual = len([r for r in results if "manual" in r[1]])

    print(f"SUMMARY")
    print(f"   {upgraded} ready to upgrade")
    print(f"   {skipped} already done (skipped)")
    print(f"   {no_section} no related reading section")
    print(f"   {manual} need manual review")
    print(f"{'=' * 50}")

    if args.dry_run:
        print("\nRun without --dry-run to apply.")
        return

    if not to_modify:
        print("\nNothing to do.")
        return

    backup(to_modify)

    for f in to_modify:
        content = open(f, encoding="utf-8").read()
        new_content, _ = upgrade_content(content, f)
        open(f, "w", encoding="utf-8").write(new_content)
        print(f"   ✓ wrote: {f}")

    print(f"\n✅ Done. {upgraded} files upgraded.")
    print("Next: open a few posts in the browser to verify.")

if __name__ == "__main__":
    main()
