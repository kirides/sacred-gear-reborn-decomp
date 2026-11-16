#!/usr/bin/env python3
"""Builds mods/reborn/changes.json (what the mod's "Changes" screen shows) from the ReBorn changelist documents.

  python tools/changelog_from_docx.py --total "ReBorn HD - changelist TOTAL (settings).docx" \
      --versions "ReBorn HD - changelist by versions.docx" --out mods/reborn/changes.json

--total     the TOTAL changelist: its section "ALL CHANGES (UP TO VERSION x.y)" becomes the first sections (one per numbered heading).
--versions  the changelist by versions: the entries of the versions after the TOTAL document's version are appended, one section per
            version and heading ("4.5: HEROES"); its last version heading is the ReBorn version ("version").
Both are the Sacred ReBorn Overlookers group's documents; the text is kept as written (the tool only splits it into sections and
strips the layout). Regenerate after a new ReBorn release with its documents.
"""
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def paragraphs(path):
    """[(style, bulleted, text)] of the document, empty paragraphs dropped."""
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    out = []
    for p in root.iter(W + 'p'):
        style = p.find(W + 'pPr/' + W + 'pStyle')
        num = p.find(W + 'pPr/' + W + 'numPr')
        parts = []
        for e in p.iter():
            if e.tag == W + 't':
                parts.append(e.text or '')
            elif e.tag in (W + 'br', W + 'cr'):
                parts.append(chr(10))
            elif e.tag == W + 'tab':
                parts.append(' ')
        text = ''.join(parts).replace(chr(0x200B), '').strip()
        if text:
            out.append((style.get(W + 'val') if style is not None else '', num is not None, text))
    return out


def clean(text):
    # the documents glue list items with " - " after a heading word; keep the text, only normalise blanks
    return re.sub(r' *' + chr(10) + ' *', chr(10), re.sub(r'[ \t]+', ' ', text)).strip()


def version_key(label):
    m = re.search(r'(\d+(?:\.\d+)*)', label)
    return tuple(int(x) for x in m.group(1).split('.')) if m else ()


def total_sections(path):
    paras = paragraphs(path)
    sections, current, version = [], None, ''
    inside = False
    for style, bullet, text in paras:
        if style == '1':
            inside = text.upper().startswith('ALL CHANGES')
            m = re.search(r'VERSION\s+([\d.]+)', text, re.I)
            if inside and m:
                version = m.group(1)
                current = {'title': 'Overview', 'items': []}
                sections.append(current)
            continue
        if not inside:
            continue
        if style == '2':
            title = re.sub(r'^\d+\.\s*', '', text).strip()
            current = {'title': title.capitalize() if title.isupper() else title, 'items': []}
            sections.append(current)
        elif current is not None:
            current['items'].append(('* ' if bullet else '') + clean(text))
    return [s for s in sections if s['items']], version


def version_sections(path, after):
    paras = paragraphs(path)
    sections, current, version, last = [], None, '', ''
    for style, bullet, text in paras:
        m = re.match(r'ReBorn mod ve[sr]+ion\s+(.+)$', text, re.I)
        if style == '1' and m:
            version = m.group(1).strip()
            last = version
            current = None
            continue
        if not version or version_key(version) <= after or text.upper() == 'CHANGES':
            continue
        if style.startswith('a') and bullet:        # in these documents the bulleted lines are the headings
            current = {'title': '%s: %s' % (version_key(version) and '.'.join(map(str, version_key(version))), text.capitalize()), 'items': []}
            sections.append(current)
        elif current is not None:
            current['items'].append(clean(text))
        else:
            current = {'title': '%s: Notes' % '.'.join(map(str, version_key(version))), 'items': [clean(text)]}
            sections.append(current)
    return [s for s in sections if s['items']], '.'.join(map(str, version_key(last))) if last else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--total', required=True)
    ap.add_argument('--versions', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    sections, total_version = total_sections(a.total)
    later, latest = version_sections(a.versions, version_key(total_version))
    data = {'version': latest or total_version, 'total_version': total_version, 'sections': sections + later}
    with open(a.out, 'w', encoding='utf8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print('ReBorn %s: %d sections (%d from the total changelist up to %s), %d items' % (
        data['version'], len(data['sections']), len(sections), total_version, sum(len(s['items']) for s in data['sections'])))


if __name__ == '__main__':
    sys.exit(main())
