"""Remember managed installations so app removal can restore them."""
import json
import os
from pathlib import Path
import manage


def location():
    return Path(os.environ['LOCALAPPDATA']) / 'EndfieldEnhancer' / 'desktop.json'


def remember(game):
    path = location()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text()) if path.exists() else {'games': []}
    resolved = str(game.resolve())
    if resolved not in data['games']:
        data['games'].append(resolved)
    data['selected'] = resolved
    manage.atomic_write(path, json.dumps(data).encode())


def selected():
    try:
        return json.loads(location().read_text()).get('selected', '')
    except (OSError, ValueError):
        return ''


def restore_recorded():
    path = location()
    if not path.exists():
        return {'restored': []}
    data = json.loads(path.read_text())
    restored = []
    for entry in data.get('games', []):
        game = Path(entry)
        import native_neural
        if (game / native_neural.STATE).exists():
            native_neural.restore(game)
            restored.append(entry + ' (native NR)')
        import neural
        if (game / neural.STATE).exists():
            neural.restore(game)
            restored.append(entry + ' (DLSS)')
        if manage.state_path(game).exists():
            with manage.locked(game):
                manage.restore(game)
            restored.append(entry)
    return {'restored': restored}
