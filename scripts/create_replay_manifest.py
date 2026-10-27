"""Prepare an unaccepted image replay manifest; review quality/visibility manually."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error('Output exists; choose a new path')
    records=json.loads(a.predictions.read_text())
    rows=[dict(segment=i,image=str(Path(r['image']).resolve()),quality_ok=False,asset_observed=False)
          for i,r in enumerate(records)]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(rows,indent=2))
    print('Review image order, segment association, quality_ok and asset_observed before replay.')


if __name__=='__main__':
    main()
