"""Build unretouched, lossless comparison assets from the supplied PNG captures."""
from pathlib import Path
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/comparisons'
OUT.mkdir(parents=True, exist_ok=True)
names = {
    'cover-off': 'Cover Off', 'cover-on': 'Cover DLSS 5 On',
    'off': 'Off', 'default': 'DLSS 5 Default',
    'preset-1': 'DLSS 5 NR Preset 1', 'preset-2': 'DLSS 5 NR Preset 2',
    'preset-3': 'DLSS 5 NR Preset 3',
    'cinematic': 'DLSS 5 NR Style Cinematic', 'natural': 'DLSS 5 NR Style Natural',
    **{f't{i}-{state}': f'T{i} {"Off" if state == "off" else "DLSS 5 On"}'
       for i in range(1, 4) for state in ('off', 'on')},
}
for slug, name in names.items():
    with Image.open(ROOT / 'Screenshot Examples' / f'{name}.png') as source:
        source.convert('RGB').save(OUT / f'{slug}.webp', lossless=True, method=6)

pairs = [('cover', 'Outdoor scene', 'cover-off', 'cover-on'),
         ('interior', 'Interior / Default', 'off', 'default'),
         *[(f't{i}', f'Team {i}', f't{i}-off', f't{i}-on') for i in range(1, 4)]]
for slug, title, before, after in pairs:
    panel = Image.new('RGB', (1600, 490), '#101827')
    draw = ImageDraw.Draw(panel)
    for x, key, label in [(0, before, 'NR OFF'), (800, after, 'NR ON')]:
        with Image.open(OUT / f'{key}.webp') as im:
            panel.paste(im.resize((800, 450), Image.Resampling.LANCZOS), (x, 40))
        draw.text((x + 16, 12), label, fill='#e5c478')
    panel.save(OUT / f'{slug}-preview.jpg', quality=92)

manifest = {'captures': names, 'pairs': pairs}
(OUT / 'captures.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(f'Built {len(names)} lossless captures and {len(pairs)} README previews.')
