from pathlib import Path
import re
import sys

from i18n.translations import TRANSLATIONS

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
PATTERN = re.compile(r"[\u4e00-\u9fff]")


def main() -> int:
    had_issue = False

    for path in sorted(TEMPLATES_DIR.rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(text, 1):
            if PATTERN.search(line) and "if lang == 'zh'" not in line and "tojson" not in line and "t(" not in line:
                relative_path = path.relative_to(ROOT).as_posix()
                print(f"{relative_path}:{idx}: {line.strip()}")
                had_issue = True

    zh_keys = set(TRANSLATIONS.get("zh", {}).keys())
    en_keys = set(TRANSLATIONS.get("en", {}).keys())
    only_zh = sorted(zh_keys - en_keys)
    only_en = sorted(en_keys - zh_keys)

    if only_zh:
        print("i18n/translations.py: zh-only keys detected")
        for key in only_zh:
            print(f"  zh-only: {key}")
        had_issue = True

    if only_en:
        print("i18n/translations.py: en-only keys detected")
        for key in only_en:
            print(f"  en-only: {key}")
        had_issue = True

    return 1 if had_issue else 0


if __name__ == "__main__":
    raise SystemExit(main())
