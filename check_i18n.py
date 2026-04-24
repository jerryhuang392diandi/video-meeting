from pathlib import Path
import re
import sys

from translations import TRANSLATIONS

BASE = Path(__file__).resolve().parent / 'templates'
pat = re.compile(r'[\u4e00-\u9fff]')
had_issue = False

for path in sorted(BASE.glob('*.html')):
    text = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    for idx, line in enumerate(text, 1):
        if pat.search(line) and "if lang == 'zh'" not in line and 'tojson' not in line and 't(' not in line:
            print(f'{path.name}:{idx}: {line.strip()}')
            had_issue = True

zh_keys = set(TRANSLATIONS.get('zh', {}).keys())
en_keys = set(TRANSLATIONS.get('en', {}).keys())
only_zh = sorted(zh_keys - en_keys)
only_en = sorted(en_keys - zh_keys)

if only_zh:
    print('translations.py: zh-only keys detected')
    for key in only_zh:
        print(f'  zh-only: {key}')
    had_issue = True

if only_en:
    print('translations.py: en-only keys detected')
    for key in only_en:
        print(f'  en-only: {key}')
    had_issue = True

if had_issue:
    sys.exit(1)
