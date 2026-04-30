from pathlib import Path
import re

SITE_ROOT = Path(".")
NEW_LANGS = "es,it,pt,hi,zh-CN,fr"

def update_translate_languages(file_path: Path):
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    original = content

    # Replace includedLanguages no matter what languages are there now
    content = re.sub(
        r"includedLanguages\s*:\s*['\"][^'\"]*['\"]",
        f"includedLanguages: '{NEW_LANGS}'",
        content
    )

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        print(f"Updated languages: {file_path}")
    else:
        print(f"Skipped (no includedLanguages found): {file_path}")

def main():
    html_files = list(SITE_ROOT.rglob("*.html"))

    for file in html_files:
        update_translate_languages(file)

    print("\nDone! Translation languages updated where found.")

if __name__ == "__main__":
    main()