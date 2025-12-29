from pathlib import Path

for f in Path('json').glob('*.json'):
    parts = f.stem.split('_')
    if len(parts) >= 4:
        new_name = f'{parts[0]}_{parts[1]}_{"_".join(parts[3:])}.json'
        f.rename(f.parent / new_name)
        print(f'{f.name} -> {new_name}')