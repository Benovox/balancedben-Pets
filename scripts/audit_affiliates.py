#!/usr/bin/env python3
"""
audit_affiliates.py — Affiliate link safety auditor for balancedben.com

Usage:
  python3 scripts/audit_affiliates.py          # dry-run audit
  python3 scripts/audit_affiliates.py --fix    # auto-fix rel/target + append tag
"""

import os, re, sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent        # /Pet web site/
TAG         = "balancedpets-20"
MAX_LINKS   = 2
DISCLOSURE_KEYWORDS = ["affiliate", "commission", "sponsored"]

REQUIRED_REL    = ["nofollow", "sponsored", "noopener"]
REQUIRED_TARGET = '_blank'

# Matches amazon.com product URLs and amzn.to short links
AMAZON_RE = re.compile(
    r'href=["\']'
    r'(https?://(?:www\.)?amazon\.(?:com|co\.uk|ca|com\.au|de|fr|it|es|co\.jp)/\S+?'
    r'|https?://amzn\.to/\S+?)'
    r'["\']',
    re.I
)

# Matches a full <a ...> tag
ATAG_RE = re.compile(r'<a\s[^>]*href=["\']([^"\']*amazon[^"\']*|[^"\']*amzn\.to[^"\']*)["\'][^>]*>.*?</a>', re.I | re.S)

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_attr(tag_str, attr):
    """Pull an attribute value out of a raw tag string."""
    m = re.search(rf'{attr}=["\']([^"\']*)["\']', tag_str, re.I)
    return m.group(1) if m else ""

def has_disclosure(html):
    # Look for any disclosure keyword in a <div> or <p> near the top (first 3000 chars)
    snippet = html[:12000].lower()
    return any(k in snippet for k in DISCLOSURE_KEYWORDS)

def ensure_tag(url):
    """Append ?tag=balancedpets-20 (or &tag=...) if not already present."""
    if TAG in url:
        return url, False
    sep = "&" if "?" in url else "?"
    return url + f"{sep}tag={TAG}", True

def fix_atag(match):
    """
    Given a matched <a> tag with an Amazon href, return a corrected version
    with proper rel, target, and associate tag appended.
    """
    original = match.group(0)
    href = match.group(1)

    new_href, tag_added = ensure_tag(href)

    # Build corrected tag
    fixed = original

    # Update href
    fixed = fixed.replace(href, new_href, 1)

    # Fix/set target
    if 'target=' in fixed:
        fixed = re.sub(r'target=["\'][^"\']*["\']', f'target="{REQUIRED_TARGET}"', fixed)
    else:
        fixed = fixed.replace('<a ', f'<a target="{REQUIRED_TARGET}" ', 1)

    # Fix/set rel — replace existing rel or inject
    full_rel = ' '.join(REQUIRED_REL)
    if 'rel=' in fixed:
        fixed = re.sub(r'rel=["\'][^"\']*["\']', f'rel="{full_rel}"', fixed)
    else:
        fixed = fixed.replace('<a ', f'<a rel="{full_rel}" ', 1)

    return fixed

# ── Audit one file ────────────────────────────────────────────────────────────
def audit_file(path, fix=False):
    html = path.read_text(encoding="utf-8")
    matches = list(ATAG_RE.finditer(html))

    if not matches:
        return None   # no Amazon links → skip

    issues  = []
    changes = []

    # 1. Link count
    if len(matches) > MAX_LINKS:
        issues.append(f"⚠️  {len(matches)} affiliate links (max is {MAX_LINKS})")

    # 2. Disclosure
    if not has_disclosure(html):
        issues.append("❌ Disclosure box not found in first 3000 chars")

    # 3. Per-link checks
    for m in matches:
        tag_str = m.group(0)
        href    = m.group(1)
        link_issues = []

        rel    = get_attr(tag_str, "rel").split()
        target = get_attr(tag_str, "target")

        missing_rel = [r for r in REQUIRED_REL if r not in rel]
        if missing_rel:
            link_issues.append(f"rel missing: {missing_rel}")
        if target != REQUIRED_TARGET:
            link_issues.append(f"target='{target}' → needs '_blank'")
        if TAG not in href:
            link_issues.append(f"missing associate tag '{TAG}'")

        if link_issues:
            label = re.search(r'>(.+?)</a>', tag_str, re.S)
            label = label.group(1).strip()[:40] if label else href[:40]
            issues.append(f"   🔗 '{label}': {' | '.join(link_issues)}")

    # 4. Fix mode — rewrite file with corrected tags
    if fix:
        new_html = ATAG_RE.sub(fix_atag, html)
        if new_html != html:
            path.write_text(new_html, encoding="utf-8")
            changes.append("✅ rel/target/tag corrected and saved")
        else:
            changes.append("✔  No changes needed")

    return {"file": path.name, "count": len(matches), "issues": issues, "changes": changes}

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    fix_mode = "--fix" in sys.argv
    posts    = sorted(ROOT.glob("post-*.html"))

    print(f"\n{'🔧 FIX MODE' if fix_mode else '🔍 AUDIT MODE'} — balancedben.com affiliate audit")
    print(f"Tag: {TAG} | Max links/post: {MAX_LINKS} | Posts scanned: {len(posts)}\n")

    total_links      = 0
    posts_with_links = 0
    total_issues     = 0

    for path in posts:
        result = audit_file(path, fix=fix_mode)
        if result is None:
            continue

        posts_with_links += 1
        total_links      += result["count"]
        total_issues     += len(result["issues"])

        status = "✅" if not result["issues"] else "⚠️ "
        print(f"{status} {result['file']}  [{result['count']} link(s)]")
        for line in result["issues"]:
            print(f"   {line}")
        for line in result["changes"]:
            print(f"   {line}")
        print()

    print("─" * 54)
    print(f"  Posts with affiliate links : {posts_with_links}")
    print(f"  Total affiliate links      : {total_links}")
    print(f"  Issues found               : {total_issues}")
    if total_issues and not fix_mode:
        print("\n  → Run with --fix to auto-correct rel / target / tag.\n")
    else:
        print()

if __name__ == "__main__":
    main()
