# Emberwright website

Source of [emberwright-mods.com](https://emberwright-mods.com): the home of Emberwright's mods for Enshrouded, starting with Architect Lines (download, install guide, keys, changelog).

## How it works

- `python build.py` builds the site into `_site/` (Python 3.9 or later, nothing to install). `python build.py --check` also fails on any placeholder left.
- `site.json` says which home page is live (`soon` until the beta, then `full`), the languages and the domain.
- `src/layout.html` is the frame of every page; `src/pages/*.html` are the pages; `src/i18n/<lang>.json` holds every text. English sits at the root, German under `/de/`, French under `/fr/`. Every language must have the same keys, or the build stops.
- `src/assets/` holds the styles, scripts, images and fonts. Fonts are served by the site itself (SIL OFL, licenses beside them): no request goes to a third party.
- `src/data/` (to come) holds `latest.json` and the other files written by the release tooling of Architect Lines (`publish-release.ps1`).
- Each push to `main` publishes the site on GitHub Pages (`.github/workflows/pages.yml`).

## Rules

- No cookies, no analytics, no third-party requests (see the privacy page). Changing this means updating the privacy page in every language first.
- The logos come from the Architect Lines repository (`assets/logo/`, see its `assets/README.md`); never redraw them here.
- Discord: https://discord.gg/Pbev3kJmdu
