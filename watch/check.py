"""Daily patch watch for the Wide FOV Slider Deadlock mod.

Reads SteamDB's GameTracking-Deadlock copy of the game files and checks everything the mod depends on.
Writes report.json / report.md; the workflow opens a GitHub issue (which emails the repo owner) when a check fails.
"""
import json, os, re, sys, urllib.request

RAW = 'https://raw.githubusercontent.com/SteamTracking/GameTracking-Deadlock/master/'
API = 'https://api.github.com/repos/SteamTracking/GameTracking-Deadlock/commits?per_page=1'
P = 'game/citadel/pak01_dir/panorama/'
HERE = os.path.dirname(os.path.abspath(__file__))


def get(path):
    with urllib.request.urlopen(RAW + path, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')


def norm(xml):
    # drop the decompiler's header comment and whitespace differences
    xml = re.sub(r'<!--.*?-->', '', xml, flags=re.S)
    xml = re.sub(r'\.vcss_c"', '.vcss"', xml)
    return re.sub(r'\s+', ' ', xml).strip()


checks = []


def check(key, severity, ok, title, detail):
    checks.append({'key': key, 'severity': severity, 'ok': bool(ok), 'title': title, 'detail': detail})


try:
    req = urllib.request.Request(API, headers={'User-Agent': 'wide-fov-watch'})
    with urllib.request.urlopen(req, timeout=60) as r:
        c = json.load(r)[0]
    build = {'sha': c['sha'], 'date': c['commit']['author']['date'], 'message': c['commit']['message'].split('\n')[0][:120]}
except Exception as e:
    build = {'sha': '', 'date': '', 'message': 'could not read latest tracking commit: %s' % e}

# 1) the two layouts the mod replaces: if Valve changes them, the mod's old copy can crash the game
for name in ('base_hud', 'base_dashboard'):
    live = norm(get(P + 'layout/%s.xml' % name))
    expected = norm(open(os.path.join(HERE, 'expected', name + '.xml'), encoding='utf-8').read())
    check('layout_' + name, 'critical', live == expected,
          'Valve changed %s.xml' % name,
          'The mod ships its own copy of panorama/layout/%s. Rebuild it from the new game files before players crash '
          '(build_wide_fov_v21.py reads the current file from pak01).' % name)

# 2) where the slider goes in Settings
ps = get(P + 'layout/popups/popup_settings.xml')
check('camera_fov', 'warning', re.search(r'id="CameraFOV"', ps),
      'Camera FOV slider is gone from Settings',
      'The Wide FOV row now falls back to the top of Camera Settings and players see the Escape-menu backup box. '
      'Update the anchor in widefov_v21.js (findSpot).')
check('camera_group', 'warning', re.search(r'id="citadel_settings_camera"', ps),
      'Camera Settings group is gone from Settings',
      'The Wide FOV row falls back to the first settings list it finds. Update findSpot in widefov_v21.js.')
check('settings_row', 'critical', 'PopupSettingsSettingsRow' in ps,
      'Settings rows changed type (PopupSettingsSettingsRow missing)',
      'The mod builds its row as a PopupSettingsSettingsRow; the Settings slider will not appear.')

# 3) the Escape-menu backup box
hud = get(P + 'layout/hud.xml')
esc = get(P + 'layout/hud_escape_menu.xml')
css = get(P + 'styles/hud_escape_menu.css')
check('escape_menu', 'warning', 'id="EscapeMenu"' in hud and 'id="SubOptions"' in esc and 'ShowEscapeMenu' in css,
      'Escape menu structure changed',
      'The backup box looks for #EscapeMenu with class ShowEscapeMenu and #SubOptions; it may never show or never hide.')

# 4) the setting itself
cv = get('DumpSource2/convars.txt')
line = next((l.strip() for l in cv.splitlines() if re.match(r'\s*r_aspectratio\s', l)), '')
check('r_aspectratio_exists', 'critical', line,
      'r_aspectratio no longer exists',
      'The slider has nothing to control. The mod needs a new approach.')
check('r_aspectratio_flags', 'warning', (not line) or line == 'r_aspectratio 0 (developmentonly defensive)',
      'r_aspectratio flags changed',
      'Now: `%s` (was `r_aspectratio 0 (developmentonly defensive)`). If it became a cheat convar, the slider stops working.' % line)

failed = [c for c in checks if not c['ok']]
report = {'build': build, 'failed': failed, 'checks': checks}
json.dump(report, open('report.json', 'w'), indent=2)

lines = ['Latest tracked Deadlock update: `%s` (%s, %s)' % (build['message'], build['date'][:10], build['sha'][:10]), '']
for c in checks:
    lines.append('- %s **%s** %s' % ('OK' if c['ok'] else ('CRITICAL' if c['severity'] == 'critical' else 'WARNING'), c['key'], '' if c['ok'] else '- ' + c['title']))
if failed:
    lines += ['', '### What broke', '']
    for c in failed:
        lines += ['**%s** (%s): %s' % (c['title'], c['severity'], c['detail']), '']
open('report.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
if os.environ.get('SIMULATE_FAILURE') == 'true' and not failed:
    report['failed'] = [{'key': 'test', 'severity': 'warning', 'ok': False, 'title': 'Test alert (simulated)', 'detail': 'Manual test run; nothing is broken.'}]
    json.dump(report, open('report.json', 'w'), indent=2)
sys.exit(0)
