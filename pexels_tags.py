#!/usr/bin/env python3
"""
pexels_tags.py — Turn Pexels live URLs into clean <img> tags for your post.

Usage:
    # Paste URLs on stdin, one per line, Ctrl-D to finish:
    python3 pexels_tags.py <post-slug> [role1 role2 ...]

    # Or pipe from a file:
    python3 pexels_tags.py puppy-training < urls.txt

    # Or pass a URLs file directly:
    python3 pexels_tags.py puppy-training --file urls.txt hero body-sit body-heel cta

Examples:
    $ python3 pexels_tags.py puppy-training hero body-1 body-2 cta
    https://images.pexels.com/photos/5763575/pexels-photo-5763575.jpeg?auto=compress&cs=tinysrgb&w=1260
    https://images.pexels.com/photos/1234567/pexels-photo-1234567.jpeg?auto=compress&cs=tinysrgb&w=1260
    [Ctrl-D]

    <img src="https://images.pexels.com/..." alt="Puppy training hero" loading="lazy" />
    <img src="https://images.pexels.com/..." alt="Puppy training body 1" loading="lazy" />
    ...

Notes:
    - URLs are matched to roles in the order you paste them
    - Default roles if omitted: hero, body-1..body-7, cta
    - alt text = "<slug as words> <role as words>", capitalized
"""
import sys
from pathlib import Path

DEFAULT_ROLES = ["hero", "body-1", "body-2", "body-3", "body-4",
                 "body-5", "body-6", "body-7", "cta"]


def make_alt(slug: str, role: str) -> str:
    text = f"{slug.replace('-', ' ')} {role.replace('-', ' ')}"
    return text.strip().capitalize()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    slug = args[0].strip().lower().replace(" ", "-")
    rest = args[1:]

    # Optional --file <path>
    urls_from_file = []
    if "--file" in rest:
        i = rest.index("--file")
        fpath = Path(rest[i + 1])
        urls_from_file = [ln.strip() for ln in fpath.read_text().splitlines() if ln.strip()]
        rest = rest[:i] + rest[i + 2:]

    roles = rest if rest else DEFAULT_ROLES

    # Read URLs from stdin if no file given
    if urls_from_file:
        urls = urls_from_file
    else:
        print(f"Paste Pexels URLs for '{slug}' (one per line), then Ctrl-D:", file=sys.stderr)
        urls = [ln.strip() for ln in sys.stdin.readlines() if ln.strip()]

    if not urls:
        print("No URLs provided.", file=sys.stderr)
        sys.exit(1)

    # Pad roles if needed
    n = len(roles)
    while len(roles) < len(urls):
        n += 1
        roles.append(f"body-{n}")

    print()
    for url, role in zip(urls, roles):
        alt = make_alt(slug, role)
        print(f'<img src="{url}" alt="{alt}" loading="lazy" />')


if __name__ == "__main__":
    main()
