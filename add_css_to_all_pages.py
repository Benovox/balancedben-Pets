from pathlib import Path

SITE_ROOT = Path(".")
CSS_LINE = '<link rel="stylesheet" href="visual-polish.css">\n'

def process_html(file_path):
    content = file_path.read_text(encoding="utf-8", errors="ignore")

    # Skip if already added
    if "visual-polish.css" in content:
        return

    # Add before </head>
    if "</head>" in content:
        content = content.replace("</head>", CSS_LINE + "</head>")
        file_path.write_text(content, encoding="utf-8")
        print(f"Updated: {file_path}")
    else:
        print(f"Skipped (no head tag): {file_path}")

def main():
    html_files = list(SITE_ROOT.rglob("*.html"))

    for file in html_files:
        process_html(file)

    print("\nDone! All pages updated.")

if __name__ == "__main__":
    main()