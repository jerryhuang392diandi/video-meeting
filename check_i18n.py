from pathlib import Path
import re
BASE = Path(__file__).resolve().parent / 'templates'
pat = re.compile(r'[\u4e00-\u9fff]')
for path in sorted(BASE.glob('*.html')):
    text = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    for idx, line in enumerate(text, 1):
        if pat.search(line) and "if lang == 'zh'" not in line and 'tojson' not in line and 't(' not in line:
            print(f'{path.name}:{idx}: {line.strip()}')
