"""Build printable HTML hardware manuals with inline SVG illustrations.

Install requirements-docs.txt, then run from any working directory. --check
verifies checked-in HTML matches its Markdown/SVG sources without writing.
"""
import argparse
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'docs/hardware'
SOURCES = ['student_build_manual.md', 'custom_airframe_and_controller.md']
STYLE = '''body{font-family:system-ui,sans-serif;max-width:1080px;margin:auto;padding:1.5rem;line-height:1.6;color:#182338}
h1,h2,h3{line-height:1.25}h2{margin-top:2rem;border-top:1px solid #ddd;padding-top:1rem}
a{color:#184f8e}table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{border:1px solid #c8ced7;padding:.5rem;text-align:left;vertical-align:top}
pre{background:#f2f4f7;padding:1rem;white-space:pre-wrap;overflow-wrap:anywhere}code{font-size:.9em}
figure{margin:1.5rem 0}figure svg{width:100%;height:auto}figcaption{font-size:.9em;color:#46546a}nav{background:#edf3fc;padding:1rem}
@media print{body{max-width:none;padding:0;font-size:10pt}nav{display:none}a{color:inherit}figure,tr{break-inside:avoid}h2,h3{break-after:avoid}pre{border:1px solid #ddd}}'''


def render(source):
    import markdown
    text = source.read_text()
    def illustration(match):
        label, target = match.groups()
        image = (source.parent / target).resolve()
        image.relative_to(DIRECTORY.resolve())
        return '\n<figure>'+image.read_text()+'<figcaption>'+escape(label)+'</figcaption></figure>\n'
    text = re.sub(r'!\[([^]]*)\]\((assets/[^)]+\.svg)\)', illustration, text)
    def link(match):
        label, target = match.groups()
        if '://' in target or target.startswith('#'):
            return match.group(0)
        resolved = (source.parent / target).resolve()
        if resolved.parent == DIRECTORY and resolved.name in SOURCES:
            target = resolved.with_suffix('.html').name
        else:
            relative = resolved.relative_to(ROOT).as_posix()
            target = 'https://github.com/crazycrafters/AERIS-Rail-Autonomous-UAV/blob/main/' + relative
        return f'[{label}]({target})'
    text = re.sub(r'(?<!!)\[([^]]+)\]\(([^)]+)\)', link, text)
    body = markdown.markdown('[TOC]\n\n'+text, extensions=['tables','fenced_code','toc'])
    title = source.read_text().splitlines()[0].lstrip('# ')
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>'+escape(title)+'</title><style>'+STYLE+'</style></head><body>'
            '<nav>Printable AERIS build manual. Use your browser’s Print → Save as PDF. '
            '<a href="student_build_manual.html">Student build</a> · '
            '<a href="custom_airframe_and_controller.html">Custom hardware development</a></nav>'
            +body+'</body></html>\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true')
    a=p.parse_args()
    for name in SOURCES:
        source=DIRECTORY/name
        target=source.with_suffix('.html')
        contents=render(source)
        if a.check:
            if not target.exists() or target.read_text()!=contents:
                p.exit(1,f'Out-of-date generated manual: {target}\n')
        else:
            target.write_text(contents)
        print(target.relative_to(ROOT))


if __name__=='__main__':
    main()
