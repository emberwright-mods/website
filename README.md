# Emberwright website

Source of [emberwright-mods.com](https://emberwright-mods.com): the home of Emberwright's mods for Enshrouded, starting with Architect Lines (download, install guide, keys, changelog).

## How it works

- `python build.py` builds the site into `_site/` (Python 3.9 or later, nothing to install). `python build.py --check` also fails on any placeholder left.
- `site.json` says which home page is live (`soon` until the beta, then `full`), the languages and the domain.
- `src/layout.html` is the frame of every page; `src/pages/*.html` are the pages; `src/i18n/<lang>.json` holds every text. English sits at the root, German under `/de/`, French under `/fr/`. Every language must have the same keys, or the build stops.
- `src/assets/` holds the styles, scripts, images and fonts. Fonts are served by the site itself (SIL OFL, licenses beside them): no request goes to a third party.
- `src/data/alines/` holds `latest.json`, `keys.json` and `changelog.json`, written by `publish-release.ps1` of Architect Lines after each release (contract: its `BETA.md`, section 10). They fill the download button, the file checks, the keys table and the changelog of the full page. While they are missing, the page says the download comes with the beta. `build.py --check` refuses an incomplete file, an unknown `schema`, or a scan other than clean or warning.
- `examples/alines/` holds example data, never published: `python build.py --home full --example` previews the full page as it will look after a release. `--home full` alone previews it without data.
- Each push to `main` publishes the site on GitHub Pages (`.github/workflows/pages.yml`).

## Rules

- No cookies, no analytics, no third-party requests (see the privacy page). Changing this means updating the privacy page in every language first.
- The logos come from the Architect Lines repository (`assets/logo/`, see its `assets/README.md`); never redraw them here.
- Discord: https://discord.gg/Pbev3kJmdu
- YouTube: https://www.youtube.com/@emberwright-mods
