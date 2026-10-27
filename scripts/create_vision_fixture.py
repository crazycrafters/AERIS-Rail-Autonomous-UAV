"""Generate tiny annotated geometry images for pipeline smoke tests only."""
import argparse
import csv
from pathlib import Path
import random
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = a.output.resolve()
    if root.exists():
        p.error('Output exists; choose a new directory')
    root.mkdir(parents=True)
    rows=[]
    rng = random.Random(27)
    for split, count in [('train', 6), ('val', 2), ('test', 2)]:
        (root / 'images' / split).mkdir(parents=True)
        (root / 'labels' / split).mkdir(parents=True)
        for i in range(count):
            path = Path('images') / split / f'geometry-{i}.png'
            image = Image.new('RGB', (64,64), tuple(rng.randrange(30) for _ in range(3)))
            draw = ImageDraw.Draw(image)
            draw.rectangle((16,16,47,47), fill=('white' if i%2 else 'orange'))
            image.save(root/path)
            (root/'labels'/split/f'geometry-{i}.txt').write_text(f'{i%2} 0.5 0.5 0.5 0.5\n')
            rows.append(dict(image=path.as_posix(),site=f'synthetic-{split}',session=f'{split}-session',
                             asset_group=f'{split}-asset-{i}',split=split))
    with (root/'manifest.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['image','site','session','asset_group','split'])
        writer.writeheader();writer.writerows(rows)
    print(root)


if __name__=='__main__':
    main()
