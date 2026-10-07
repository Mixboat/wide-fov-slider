"""Patch watch for the Wide FOV Slider, Hide Investments, Old Damage Portraits and Shop Notes Deadlock mods.

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


MODS = {
    'wfov': {'name': 'Wide FOV Slider', 'page': 'https://gamebanana.com/mods/724244'},
    'hinv': {'name': 'Hide Investments', 'page': 'https://gamebanana.com/mods/724744'},
    'odp': {'name': 'Old Damage Portraits', 'page': 'https://gamebanana.com/mods/724869'},
    'sn': {'name': 'Shop Notes', 'page': 'https://gamebanana.com/requests/97453'},
}


def check(key, severity, ok, title, detail, mod='wfov'):
    checks.append({'key': key, 'severity': severity, 'ok': bool(ok), 'title': title, 'detail': detail,
                   'mod': MODS[mod]['name'], 'page': MODS[mod]['page']})


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

# 5) Hide Investments: the two tiny layouts it ships with one script line added, and the badges it hides
for name in ('team_status', 'hud_data_feed'):
    live = norm(get(P + 'layout/%s.xml' % name))
    expected = norm(open(os.path.join(HERE, 'expected', name + '.xml'), encoding='utf-8').read())
    check('hinv_layout_' + name, 'critical', live == expected,
          'Valve changed %s.xml' % name,
          'Hide Investments ships its own copy of panorama/layout/%s with one script line added; the old copy now '
          'overrides the new one. Rebuild with build_hide_investments.py (it reads the current file from pak01) and '
          're-upload, then refresh watch/expected/%s.xml.' % (name, name), mod='hinv')
st = get(P + 'layout/citadel_hud_active_player_stats.xml')
check('hinv_badge_ids', 'warning', all(('id="%s"' % i) in st for i in ('HudStatBlock', 'CoreStats', 'CoreStatFXLayer')),
      'Investment badge ids changed',
      'One of #HudStatBlock / #CoreStats / #CoreStatFXLayer is gone from citadel_hud_active_player_stats.xml. '
      'The class backup (core_stat / stat_fx parents) should still hide them; check in game and update IDS in hide_investments.js.', mod='hinv')
check('hinv_badge_classes', 'critical', 'class="core_stat"' in st and 'stat_fx' in st,
      'Investment badge classes changed',
      'The backup classes core_stat / stat_fx are gone. If the badge ids changed too, the badges show again. '
      'Update hide_investments.js.', mod='hinv')
check('hinv_stats_panel', 'warning', 'id="hudActivePlayerStats"' in hud,
      'Active player stats panel renamed',
      '#hudActivePlayerStats is gone from hud.xml; the class backup falls back to a slower search by panel type.', mod='hinv')

# 6) Old Damage Portraits: it ships its own copies of two stylesheets (Valve's current css + the old rules)
for name in ('hud_damage_impact', 'hero_badge'):
    live = get(P + 'styles/%s.css' % name)
    expected = open(os.path.join(HERE, 'expected', name + '.css'), encoding='utf-8').read()
    check('odp_css_' + name, 'warning', norm(live) == norm(expected),
          'Valve changed %s.css' % name,
          'Old Damage Portraits overrides this stylesheet, so players miss whatever Valve changed (looks only, cannot crash). '
          'Rebuild with build_old_damage_portraits.py (it re-reads the current css from pak01) and re-upload; then refresh expected/%s.css.' % name, mod='odp')
di_css = get(P + 'styles/hud_damage_impact.css'); hb_css = get(P + 'styles/hero_badge.css')
check('odp_css_hooks', 'critical',
      all(x in di_css for x in ('.healthBarContainer', 'active_damage_wiggle', 'healthbar_backer_horiz_mask', 'healthbar_backer_horiz_border', 'healthBar_backer', '.playerName', 'KillAssistContainer'))
      and all(x in hb_css for x in ('HeroImageBackground', 'CitadelHeroBadge #HeroImage')),
      'A stylesheet lost a rule the mod rewrites',
      'build_old_damage_portraits.py will refuse to build until its old-look rules are updated for the new css.', mod='odp')
di_xml = get(P + 'layout/hud_damage_impact.xml')
check('odp_layout', 'warning', norm(di_xml) == norm(open(os.path.join(HERE, 'expected', 'hud_damage_impact.xml'), encoding='utf-8').read()),
      'Damage-portrait layout changed',
      'The mod only ships css, so this cannot crash, but panel names may have changed: check the old look in game and update the rules.', mod='odp')

# 7) Shop Notes: two tiny HUD layouts with one script line added, and the shop panels it adds the Notes tab to
for name in ('hud_modifiers', 'hud_ability_panels_container'):
    live = norm(get(P + 'layout/%s.xml' % name))
    expected = norm(open(os.path.join(HERE, 'expected', name + '.xml'), encoding='utf-8').read())
    check('sn_layout_' + name, 'critical', live == expected,
          'Valve changed %s.xml' % name,
          'Shop Notes ships its own copy of panorama/layout/%s with one script line added; the old copy now overrides the new one. '
          'Rebuild with build_shop_notes.py (it reads the current file from pak01) and re-upload, then refresh watch/expected/%s.xml.' % (name, name), mod='sn')
shop = get(P + 'layout/citadel_hud_hero_shop.xml')
check('sn_shop_ids', 'critical', all(('id="%s"' % i) in shop for i in ('ShopNavigation', 'ShopModListsContainer')) and 'CitadelHudHeroShop' in shop,
      'Shop panel ids changed',
      'One of CitadelHudHeroShop / #ShopNavigation / #ShopModListsContainer is gone from citadel_hud_hero_shop.xml, so the Notes tab is not added. Update shop_notes.js.', mod='sn')
shop_css = get(P + 'styles/citadel_hud_hero_shop.css')
check('sn_shop_tabs', 'warning', all(c in shop_css for c in ('showingFavorites', 'showingRecommendations', 'showingAllItems', 'showingWeapon', 'showingTech', 'showingArmor')),
      'Shop tab classes changed',
      'A showing* class is gone from citadel_hud_hero_shop.css: Notes may not close when a shop tab is clicked. Update SHOW in shop_notes.js.', mod='sn')

failed = [c for c in checks if not c['ok']]
report = {'build': build, 'failed': failed, 'checks': checks}
json.dump(report, open('report.json', 'w'), indent=2)

lines = ['Latest tracked Deadlock update: `%s` (%s, %s)' % (build['message'], build['date'][:10], build['sha'][:10]), '']
for c in checks:
    lines.append('- %s **%s** (%s) %s' % ('OK' if c['ok'] else ('CRITICAL' if c['severity'] == 'critical' else 'WARNING'), c['key'], c['mod'], '' if c['ok'] else '- ' + c['title']))
if failed:
    lines += ['', '### What broke', '']
    for c in failed:
        lines += ['**%s: %s** (%s): %s' % (c['mod'], c['title'], c['severity'], c['detail']), '']
open('report.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
if os.environ.get('SIMULATE_FAILURE') == 'true' and not failed:
    report['failed'] = [{'key': 'test', 'severity': 'warning', 'ok': False, 'title': 'Test alert (simulated)', 'detail': 'Manual test run; nothing is broken.', 'mod': 'Wide FOV Slider + Hide Investments', 'page': 'https://gamebanana.com/members/5889014'}]
    json.dump(report, open('report.json', 'w'), indent=2)
sys.exit(0)
