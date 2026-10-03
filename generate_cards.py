"""
Builds dark_mode.svg and light_mode.svg from the CONFIG below.
Run this once (and again whenever you edit your info). today.py then fills in
the live GitHub numbers inside the elements this script creates.

    python generate_cards.py
"""
from xml.sax.saxutils import escape

CONFIG = {
    'username': 'flintstqne',   # shown in the header line
    'about': [                             # (label, value) block under the header
        ('Role', 'B.S. Cybersecurity Student'),
        ('Focus', 'Security Engineering • Systems • AI'),
        ('Location', 'Pittsburgh, PA Area'),
    ],
    'skills': [                            # (label, value) block after two blank lines
        ('Languages', 'Python • Java • Bash • SQL'),
        ('Systems', 'Linux • Docker • VMware • Git'),
        ('Networking', 'TCP/IP • DNS • HTTP/S • Wireshark'),
        ('Security', 'Malware Analysis • SIEM • YARA'),
        ('Infrastructure', 'Ansible • Prometheus • Grafana'),
        ('Currently Building', 'Security + Infrastructure Homelab'),
    ],
}

FALLBACK_ART = [
    '    ______________    ',
    '   /              \\   ',
    '  |  $ whoami      |  ',
    '  |  > you         |  ',
    '  |  $ _           |  ',
    '   \\______________/   ',
    '      /________\\      ',
]
ART_FONT = 9        # px, font size for the portrait
ART_CHAR_W = 5.4    # px per character. textLength pins each row to this grid.
ART_LINE = 11       # px between portrait rows


def load_art(theme):
    """Use ascii_dark.txt / ascii_light.txt from photo_to_ascii.py when present."""
    path = 'ascii_' + theme.split('_')[0] + '.txt'
    try:
        with open(path) as f:
            lines = f.read().rstrip('\n').split('\n')
        return lines, True
    except FileNotFoundError:
        return FALLBACK_ART, False


THEMES = {
    'dark_mode.svg': dict(bg='#161b22', key='#ffa657', value='#a5d6ff', dots='#616e7f', text='#c9d1d9', add='#3fb950', dele='#f85149'),
    'light_mode.svg': dict(bg='#f6f8fa', key='#953800', value='#0a3069', dots='#c2cfde', text='#24292f', add='#1a7f37', dele='#cf222e'),
}

X0, X1, LINE = 15, 390, 20
WIDTH_CHARS = 56   # width of the header and section rules in monospace characters
VALUE_COL = 24     # every value starts at this character column, so values line up


def row(label, value, y, value_id=None):
    """One 'Label: ........ value' line. Dots fill the space up to VALUE_COL."""
    pad = max(1, VALUE_COL - len(label) - 1 - 2)
    dots = ' ' + '.' * pad + ' '
    vid = f' id="{value_id}"' if value_id else ''
    return (f'<tspan x="{X1}" y="{y}" class="key">{escape(label)}</tspan>:'
            f'<tspan class="cc">{dots}</tspan>'
            f'<tspan class="value"{vid}>{escape(value)}</tspan>')


def section(title, y):
    dashes = '-' * max(0, WIDTH_CHARS - len(title) - 2)
    return f'<tspan x="{X1}" y="{y}">- {escape(title)}</tspan> {dashes}-'


def loc_row(y):
    """Lines of Code: net total, then green additions and red deletions."""
    pad = max(1, VALUE_COL - len('Lines of Code') - 1 - 2)
    return (f'<tspan x="{X1}" y="{y}" class="key">Lines of Code</tspan>:'
            f'<tspan class="cc"> {"." * pad} </tspan>'
            f'<tspan class="value" id="loc_data">0</tspan> ( '
            f'<tspan class="addColor" id="loc_add">0</tspan><tspan class="addColor">++</tspan>, '
            f'<tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan> )')


def _build(theme, y0, min_height):
    """Return (svg, height). y0 shifts the info column down, min_height grows the card."""
    c = THEMES[theme]
    lines = []
    y = y0
    header = CONFIG['username']
    lines.append(f'<tspan x="{X1}" y="{y}">{escape(header)}</tspan> {"-" * max(0, WIDTH_CHARS - len(header) - 1)}-')
    y += LINE * 2
    for label, val in CONFIG['about']:
        lines.append(row(label, val, y)); y += LINE
    y += LINE * 2
    for label, val in CONFIG['skills']:
        lines.append(row(label, val, y)); y += LINE
    y += LINE
    lines.append(section('GitHub Stats', y)); y += LINE
    lines.append(row('Repos', '0', y, 'repo_data')); y += LINE
    lines.append(row('Commits', '0', y, 'commit_data')); y += LINE
    lines.append(loc_row(y)); y += LINE
    height = max(y + 25, min_height)

    # Left side ASCII art, vertically centered on the card.
    art_lines, is_photo = load_art(theme)
    step = ART_LINE if is_photo else LINE
    art_top = max(25, (height - len(art_lines) * step) // 2 + step)
    if is_photo:
        span = ART_CHAR_W * max(len(a) for a in art_lines)
        art = ''.join(
            f'<tspan x="{X0}" y="{art_top + i * step}" font-size="{ART_FONT}px" '
            f'textLength="{span:.1f}" lengthAdjust="spacing">{escape(a)}</tspan>'
            for i, a in enumerate(art_lines))
    else:
        art = ''.join(f'<tspan x="{X0}" y="{art_top + i * step}">{escape(a)}</tspan>'
                      for i, a in enumerate(art_lines))

    return f'''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="{height}px" font-size="16px">
<style>
@font-face {{ src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; font-display: swap; -webkit-size-adjust: 95%; size-adjust: 95%; }}
.key {{fill: {c['key']};}}
.value {{fill: {c['value']};}}
.addColor {{fill: {c['add']};}}
.delColor {{fill: {c['dele']};}}
.cc {{fill: {c['dots']};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="985px" height="{height}px" fill="{c['bg']}" rx="15"/>
<text x="{X0}" y="30" fill="{c['text']}" class="ascii" xml:space="preserve">{art}</text>
<text x="{X1}" y="30" fill="{c['text']}" xml:space="preserve">{''.join(lines)}</text>
</svg>
''', height


def build(theme):
    """Build the card, centering the info column when the portrait is taller."""
    svg, height = _build(theme, 30, 0)
    art_lines, is_photo = load_art(theme)
    art_height = len(art_lines) * (ART_LINE if is_photo else LINE) + 50
    if art_height > height:
        offset = (art_height - height) // 2
        svg, _ = _build(theme, 30 + offset, art_height)
    return svg


if __name__ == '__main__':
    for name in THEMES:
        with open(name, 'w', encoding='utf-8') as f:
            f.write(build(name))
        print('wrote', name)
