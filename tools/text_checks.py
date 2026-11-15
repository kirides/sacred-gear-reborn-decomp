# Text checks for the mod's self test: ids whose text ReBorn's SRglbl.res changes or adds, from two runs of tools/textdump
# (one on the plain game, one with the mod's overlay).
#   python tools/text_checks.py <vanilla texts.json> <reborn texts.json> --language DE --out mods/reborn/text_checks.json
import argparse, json
ap = argparse.ArgumentParser()
ap.add_argument('vanilla')
ap.add_argument('reborn')
ap.add_argument('--language', required=True, help="Settings.cfg LANGUAGE of both runs")
ap.add_argument('--out', default='mods/reborn/text_checks.json')
ap.add_argument('--count', type=int, default=6)
a = ap.parse_args()
v = json.load(open(a.vanilla, encoding='utf-8'))
r = json.load(open(a.reborn, encoding='utf-8'))
plain = lambda t: t.strip() and not t.startswith(chr(92))
new = sorted((int(k) for k in r if k not in v and plain(r[k])))
changed = sorted((int(k) for k in r if k in v and r[k] != v[k] and plain(r[k]) and plain(v[k])))
pick = (new[:a.count // 2] + changed[:a.count // 2])
checks = [{'id': i, 'text': r[str(i)], 'was': v.get(str(i))} for i in pick]
json.dump({'language': a.language, 'checks': checks}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(new)} new, {len(changed)} changed ids; {len(checks)} checks written to {a.out}')
