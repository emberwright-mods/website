"""Builds the Emberwright website into _site/, ready for GitHub Pages.

Usage:  python build.py            (builds _site/)
        python build.py --check    (builds, then fails on any problem)

What it does:
  - site.json says which home page is live ("soon" or "full"), the languages
    and the domain;
  - each page of src/pages/ is rendered once per language, inside
    src/layout.html, with the strings of src/i18n/<lang>.json;
    English sits at the root, the other languages under /<lang>/;
  - src/assets/ and src/data/ are copied as they are, plus CNAME and .nojekyll.

Placeholders, in the layout and the pages:
  {{t.key}}        a string of src/i18n/<lang>.json (may hold HTML)
  {{root}}         relative path from the page to the site root ("", "../", ...)
  {{home}}         relative path to this language's home page
  {{page.<name>}}  relative path to page <name> in this language
  {{lang}}         the page's language code
  {{alternates}}   <link rel="alternate" hreflang> tags of this page
  {{switcher}}     the language buttons of this page
  {{content}}      (layout only) the page

Every language must have exactly the same keys, and no placeholder may be
left: the build stops otherwise, so a page never ships half translated.
"""

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "_site"
PLACEHOLDER = re.compile(r"\{\{([a-zA-Z0-9_.\-]+)\}\}")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def page_dir(lang, default_lang, name):
    """Folder of page `name` in `lang`, relative to the site root."""
    parts = [] if lang == default_lang else [lang]
    if name != "index":
        parts.append(name)
    return "/".join(parts)


def rel(from_dir, to_dir):
    """Relative link from folder `from_dir` to folder `to_dir` (both from the root)."""
    up = "../" * (len(from_dir.split("/")) if from_dir else 0)
    return up + (to_dir + "/" if to_dir else "")


def render(text, values, where):
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise SystemExit(f"{where}: unknown placeholder {{{{{key}}}}}")
        return values[key]
    # Two passes: strings may hold {{root}} or {{page.x}} themselves.
    return PLACEHOLDER.sub(replace, PLACEHOLDER.sub(replace, text))


def main():
    site = load_json(ROOT / "site.json")
    langs = site["languages"]
    default_lang = langs[0]
    names = {lang: load_json(SRC / "i18n" / f"{lang}.json") for lang in langs}

    reference = set(names[default_lang])
    for lang in langs[1:]:
        keys = set(names[lang])
        if keys != reference:
            missing = sorted(reference - keys)
            extra = sorted(keys - reference)
            raise SystemExit(f"i18n/{lang}.json differs from {default_lang}.json: missing {missing}, extra {extra}")

    pages = {"index": site["home"]}
    for path in sorted((SRC / "pages").glob("*.html")):
        if path.stem not in ("soon", "full"):
            pages[path.stem] = path.stem

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    layout = (SRC / "layout.html").read_text(encoding="utf-8")

    for lang in langs:
        strings = names[lang]
        for name, source in pages.items():
            here = page_dir(lang, default_lang, name)
            values = {"t." + k: v for k, v in strings.items()}
            values["root"] = rel(here, "")
            values["lang"] = lang
            values["home"] = rel(here, page_dir(lang, default_lang, "index"))
            for other in pages:
                values["page." + other] = rel(here, page_dir(lang, default_lang, other))
            alternates = []
            switcher = []
            for other_lang in langs:
                target = page_dir(other_lang, default_lang, name)
                url = f"https://{site['domain']}/" + (target + "/" if target else "")
                alternates.append(f'<link rel="alternate" hreflang="{other_lang}" href="{url}">')
                current = ' aria-current="true"' if other_lang == lang else ""
                switcher.append(f'<a href="{rel(here, target)}" hreflang="{other_lang}" lang="{other_lang}"{current}>{other_lang.upper()}</a>')
            default_target = page_dir(default_lang, default_lang, name)
            alternates.append(f'<link rel="alternate" hreflang="x-default" href="https://{site["domain"]}/' + (default_target + "/" if default_target else "") + '">')
            values["alternates"] = "\n".join(alternates)
            values["switcher"] = "".join(switcher)
            values["canonical"] = f"https://{site['domain']}/" + (here + "/" if here else "")
            body = (SRC / "pages" / f"{source}.html").read_text(encoding="utf-8")
            values["content"] = render(body, values, f"pages/{source}.html ({lang})")
            # The page's own title and description come from the page's keys.
            values["page_title"] = strings.get(f"{source}.title", strings["site.title"])
            values["page_description"] = strings.get(f"{source}.description", strings["site.description"])
            html = render(layout, values, f"layout.html ({lang}, {name})")
            target = OUT / here / "index.html" if here else OUT / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(html)

    shutil.copytree(SRC / "assets", OUT / "assets")
    if (SRC / "data").exists():
        shutil.copytree(SRC / "data", OUT / "data")
    (OUT / "CNAME").write_text(site["domain"] + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    built = sorted(str(p.relative_to(OUT)).replace("\\", "/") for p in OUT.rglob("index.html"))
    print(f"Built {len(built)} pages ({site['home']} home, {', '.join(langs)}):")
    for path in built:
        print("  " + path)

    if "--check" in sys.argv:
        for path in OUT.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            if "{{" in text or "}}" in text:
                raise SystemExit(f"{path}: a placeholder is left")
        print("Check OK")


if __name__ == "__main__":
    main()
