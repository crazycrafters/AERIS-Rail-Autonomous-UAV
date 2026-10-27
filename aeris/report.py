"""Export an escaped static mission report; no web service or review database."""
import argparse
import html
import json
from pathlib import Path


def render(mission):
    summary = {k:v for k,v in mission.items() if k not in ('events','observations')}
    rows = ''.join('<tr><td>'+html.escape(str(row.get('segment')))+
                   '</td><td>'+html.escape(str(row.get('quality_ok')))+
                   '</td><td>'+html.escape(str(row.get('review_required')))+
                   '</td><td><pre>'+html.escape(json.dumps(row,indent=2))+'</pre></td></tr>'
                   for row in mission.get('observations',[]))
    return ('<!doctype html><html><head><meta charset="utf-8"><title>AERIS mission report</title>'
            '<style>body{font-family:system-ui;margin:2rem}td,th{border:1px solid #ccc;padding:.5rem}'
            'table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
            '</head><body><h1>AERIS inspection simulation report</h1>'
            '<p>Review candidates are not confirmed defects. This export does not record reviewer decisions.</p><pre>'
            +html.escape(json.dumps(summary,indent=2))+'</pre><table><tr><th>Segment</th><th>Quality</th>'
            '<th>Review candidate</th><th>Evidence</th></tr>'+rows+'</table></body></html>')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mission',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error('Output exists; choose a new filename')
    mission=json.loads(a.mission.read_text())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(render(mission),encoding='utf-8')
    print(a.output.resolve())


if __name__=='__main__':
    main()
