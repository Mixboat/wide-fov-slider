# Mixboat's Deadlock mod pages

This repo hosts the small web pages and the patch watch behind my Deadlock mods. It started as the storage page for the
Wide FOV Slider, so the repo keeps that name: the mods load these pages from `mixboat.github.io/wide-fov-slider/...`, and
renaming it would break them.

## What's in here

| Path | What it is | Used by |
|---|---|---|
| [`shop-notes/`](shop-notes/) | **Shop Notes storage page.** Keeps your notes, templates, snapshots and pasted screenshots in the page's own browser storage (localStorage) on your PC. It also shows the box you paste screenshots into, in the notes' light or dark look. | [Shop Notes](https://gamebanana.com/mods/725094) and the notes in Seamless QoL |
| [`index.html`](index.html) | **Wide FOV Slider storage page.** Remembers your slider value. | The original [Wide FOV Slider](https://gamebanana.com/mods/724244) release |
| [`watch/`](watch/) + [`.github/workflows/`](.github/workflows/) | **Patch watch.** Every 6 hours, checks the latest Deadlock game files ([SteamTracking/GameTracking-Deadlock](https://github.com/SteamTracking/GameTracking-Deadlock)) for changes that would break a mod, and opens an issue when something changed. | Wide FOV Slider, Hide Investments, Old Damage Portraits, Shop Notes |
| `shop-notes-test/`, `clip-test/` | Test pages from development. Not used by any released mod. | - |

## Privacy

- The pages run in a hidden in-game browser panel and only store data **in that panel's local storage on your own PC**.
- Nothing is sent anywhere, and the pages load nothing from other sites.
- Shop Notes keeps each Steam account's notes apart. Backups and template share codes contain only your note text, never your account id.

## How the mods talk to the page

Deadlock's UI scripts have no file or storage access of their own, so the mods load the page in a hidden panel. They send
requests in the page address (`#...`), and the page answers through its title. The Shop Notes page is versioned (now v6), and
every version answers older requests exactly as before, so older mod versions keep working.

## Credits

Thanks to **Predi** for the hidden storage-page technique these mods build on.
