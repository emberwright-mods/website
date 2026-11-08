"""Builds the Emberwright website into _site/, ready for GitHub Pages.

Usage:  python build.py                    builds _site/ as site.json says
        python build.py --check            also fails on any problem
        python build.py --home full        builds the full home page instead of site.json's
        python build.py --example          reads examples/alines/ instead of src/data/alines/
                                           (to preview the full page before a release)

What it does:
  - site.json says which home page is live ("soon" or "full"), the languages
    and the domain;
  - each page of src/pages/ is rendered once per language, inside
    src/layout.html, with the strings of src/i18n/<lang>.json; English sits at
    the root, the other languages under /<lang>/; a page's optional
    <name>.nav.html goes into the top bar;
  - src/data/alines/ (latest.json, keys.json, changelog.json, written by
    publish-release.ps1 of Architect Lines, contract in its BETA.md, section 10)
    fills the download button, the checks, the keys and the changelog; while
    they are missing, the page says the download comes with the beta;
  - src/assets/ is copied as it is, plus CNAME and .nojekyll.

Placeholders, in the layout and the pages:
  {{t.key}}            a string of src/i18n/<lang>.json (may hold HTML)
  {{root}}             relative path from the page to the site root
  {{home}}             relative path to this language's home page
  {{page.<name>}}      relative path to page <name> in this language
  {{lang}}             the page's language code
  {{assets.version}}   short hash of the styles and scripts, appended to their links
                       (?v=...) so browsers fetch them again after each change
  {{alternates}}       <link rel="alternate" hreflang> tags of this page
  {{switcher}}         the language links of this page
  {{nav}}              the page's own top bar links (<name>.nav.html), or nothing
  {{key.<id>}}         the default key of action <id> as <kbd>, or nothing
  {{alines.<part>}}    a part built from src/data/alines/ (see alines_parts)
  {{content}}          (layout only) the page

Every language must have exactly the same keys, and no placeholder may be
left: the build stops otherwise, so a page never ships half translated.
"""

import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "_site"
PLACEHOLDER = re.compile(r"\{\{([a-zA-Z0-9_.\-]+)\}\}")
RELEASES = "https://github.com/emberwright-mods/alines-releases/"
SCHEMA = 1
# The keys of the table "Keys at a glance": the Quick level, in this order.
QUICK_TABLE = ["keyMark", "keyVolume", "keyStack", "keyToolLine", "keyToolWall", "keyToolFloor",
               "keyToolVolume", "keyMode", "keyUndo", "keyRedo", "keyLevel", "keyPanel"]
KEY_NAMES = {"Backquote": "`", "LeftAlt": "Alt", "RightAlt": "Alt Gr", "LeftShift": "Shift",
             "RightShift": "Shift", "LeftControl": "Ctrl", "Control": "Ctrl", "Up": "↑",
             "Down": "↓", "Left": "←", "Right": "→", "MiddleMouse": "\U0001F5B1 middle"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fail(message):
    raise SystemExit(message)


# ---------- Architect Lines data (contract: BETA.md, section 10) ----------

def need(obj, path, kind, where):
    value = obj
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            fail(f"{where}: missing {path}")
        value = value[part]
    if kind is not None and not isinstance(value, kind):
        fail(f"{where}: {path} should be {kind.__name__ if isinstance(kind, type) else kind}")
    return value


def load_alines(folder):
    data = {"latest": None, "keys": None, "changelog": None}
    if not folder.exists():
        return data
    for name in data:
        path = folder / f"{name}.json"
        if not path.exists():
            continue
        obj = load_json(path)
        where = str(path.relative_to(ROOT))
        if obj.get("schema") != SCHEMA:
            fail(f"{where}: schema {obj.get('schema')!r}, this site reads schema {SCHEMA}")
        if name == "latest":
            need(obj, "channel", str, where)
            if obj["channel"] not in ("beta", "stable"):
                fail(f"{where}: channel must be beta or stable")
            for path_ in ("tag", "published", "releaseUrl", "alines.version", "shroudforge.version",
                          "installer.name", "installer.url", "scans.defender", "scans.virustotal.result",
                          "scans.virustotal.url"):
                need(obj, path_, str, where)
            need(obj, "installer.size", int, where)
            sha = need(obj, "installer.sha256", str, where)
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                fail(f"{where}: installer.sha256 must be 64 lowercase hex characters")
            for path_ in ("releaseUrl", "installer.url"):
                url = need(obj, path_, str, where)
                if not url.startswith(RELEASES) or "/latest/" in url:
                    fail(f"{where}: {path_} must point at this release in {RELEASES}")
            if obj["installer"].get("publisher") is not None and not isinstance(obj["installer"]["publisher"], str):
                fail(f"{where}: installer.publisher must be a string or null")
            for scan in (obj["scans"]["defender"], obj["scans"]["virustotal"]["result"]):
                if scan not in ("clean", "warning"):
                    fail(f"{where}: a scan says {scan!r}; only a clean or warning package is published")
        elif name == "keys":
            need(obj, "version", str, where)
            for i, key in enumerate(need(obj, "keys", list, where)):
                for field in ("action", "id", "key", "level"):
                    need(key, field, str, f"{where}, keys[{i}]")
        else:
            for i, entry in enumerate(need(obj, "entries", list, where)):
                for field in ("version", "text"):
                    need(entry, field, str, f"{where}, entries[{i}]")
        data[name] = obj
    return data


def kbd(key):
    parts = key.split("+") if key != "+" else ["+"]
    return "+".join(f"<kbd>{html.escape(KEY_NAMES.get(p, p))}</kbd>" for p in parts)


def size_text(size, strings):
    mb = f"{size / (1024 * 1024):.1f}".replace(".", strings["num.decimal"])
    return f"{mb} {strings['num.mb']}"


def alines_parts(strings, data, warnings):
    """The {{alines.*}} and {{key.*}} values of one language."""
    t = strings
    latest, keys, changelog = data["latest"], data["keys"], data["changelog"]
    parts = {}

    by_id = {k["id"]: k for k in keys["keys"]} if keys else {}
    for key_id, key in by_id.items():
        parts["key." + key_id] = kbd(key["key"])
    # A key the page names but keys.json lacks shows nothing (before the first release).
    for key_id in QUICK_TABLE + ["keyToolStack", "keyToolMaterial", "keyWallThickness", "keyFreePoint", "keyLine", "keyWall"]:
        parts.setdefault("key." + key_id, "")

    if latest:
        inst = latest["installer"]
        channel = t["dl.beta"] if latest["channel"] == "beta" else ""
        version = latest["alines"]["version"]
        detail = f"{channel} {version} · {html.escape(inst['name'])} · {size_text(inst['size'], t)}".strip()
        parts["alines.cta"] = (f'<a class="btn btn-gold" href="{html.escape(inst["url"])}"><span>{t["dl.button"]}</span>'
                               f'<small>{detail}</small></a>')
        parts["alines.file"] = f'<a class="mono" href="{html.escape(inst["url"])}">{html.escape(inst["name"])}</a>, {channel} {version}'.replace("  ", " ")
        publisher = html.escape(inst["publisher"]) if inst.get("publisher") else t["verify.unsigned"]
        vt = latest["scans"]["virustotal"]
        vt_text = (f'{vt.get("detections", 0)} / {vt.get("engines", "?")}' if "engines" in vt else t["verify." + vt["result"]])
        parts["alines.verify"] = (
            f'<div class="verify"><h3>{t["verify.h"]}</h3><dl>'
            f'<dt>{t["verify.publisher"]}</dt><dd>{publisher}</dd>'
            f'<dt>SHA-256</dt><dd class="hash"><code id="sha">{inst["sha256"]}</code>'
            f'<button type="button" class="copy" id="copy-sha" data-copied="{t["verify.copied"]}" data-selected="{t["verify.selected"]}">{t["verify.copy"]}</button></dd>'
            f'<dt>VirusTotal</dt><dd><span class="scan-{vt["result"]}">{vt_text}</span> · <a href="{html.escape(vt["url"])}">{t["verify.report"]}</a></dd>'
            f'<dt>Defender</dt><dd><span class="scan-{latest["scans"]["defender"]}">{t["verify." + latest["scans"]["defender"]]}</span></dd>'
            f'<dt>{t["verify.release"]}</dt><dd><a href="{html.escape(latest["releaseUrl"])}">{html.escape(latest["tag"])}</a></dd>'
            f'</dl></div>')
        parts["alines.edition"] = html.escape(f'{latest["shroudforge"].get("edition", "AL Edition")} {latest["shroudforge"]["version"]}')
        parts["alines.version"] = html.escape(version)
    else:
        parts["alines.cta"] = f'<span class="btn btn-gold is-off" aria-disabled="true"><span>{t["dl.soon"]}</span><small>{t["dl.soon_sub"]}</small></span>'
        parts["alines.file"] = f'<span class="mono">install_alines.exe</span>, {t["dl.soon_short"]}'
        parts["alines.verify"] = f'<div class="verify"><h3>{t["verify.h"]}</h3><p>{t["verify.soon"]}</p></div>'
        parts["alines.edition"] = "AL Edition"
        parts["alines.version"] = ""

    rows = []
    for key_id in QUICK_TABLE:
        key = by_id.get(key_id)
        if not key:
            continue
        name = t.get(f"keyname.{key_id}")
        desc = t.get(f"keydesc.{key_id}", "")
        if name is None:
            warnings.add(f"no translation for {key_id} ({key['action']})")
            name = html.escape(key["action"])
        rows.append(f'<tr><td>{name}</td><td>{kbd(key["key"])}</td><td>{desc}</td></tr>')
    parts["alines.keys_rows"] = "\n".join(rows) if rows else f'<tr><td colspan="3">{t["keys.soon"]}</td></tr>'

    if changelog:
        items = [f'<li><span class="v">{html.escape(e["version"])}</span><p>{html.escape(e["text"])}</p></li>'
                 for e in changelog["entries"][:5]]
        parts["alines.changelog"] = "\n".join(items)
    else:
        parts["alines.changelog"] = f'<li><span class="v">·</span><p>{t["log.soon"]}</p></li>'
    return parts


# ---------- pages ----------

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


def assets_version():
    """Short hash of src/assets' styles and scripts, for ?v= on their links."""
    digest = hashlib.sha256()
    for path in sorted((SRC / "assets").glob("*")):
        if path.suffix in (".css", ".js"):
            digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()[:10]


def render(text, values, where):
    def replace(match):
        key = match.group(1)
        if key not in values:
            fail(f"{where}: unknown placeholder {{{{{key}}}}}")
        return values[key]
    # Two passes: strings may hold {{root}}, {{key.x}} or {{page.x}} themselves.
    return PLACEHOLDER.sub(replace, PLACEHOLDER.sub(replace, text))


def arg(name):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def main():
    site = load_json(ROOT / "site.json")
    home = arg("--home") or site["home"]
    if home not in ("soon", "full"):
        fail("--home must be soon or full")
    langs = site["languages"]
    default_lang = langs[0]
    names = {lang: load_json(SRC / "i18n" / f"{lang}.json") for lang in langs}

    reference = set(names[default_lang])
    for lang in langs[1:]:
        keys = set(names[lang])
        if keys != reference:
            fail(f"i18n/{lang}.json differs from {default_lang}.json: missing {sorted(reference - keys)}, extra {sorted(keys - reference)}")

    data_dir = ROOT / "examples" / "alines" if "--example" in sys.argv else SRC / "data" / "alines"
    data = load_alines(data_dir)

    pages = {"index": home}
    for path in sorted((SRC / "pages").glob("*.html")):
        if path.stem not in ("soon", "full") and not path.stem.endswith(".nav"):
            pages[path.stem] = path.stem

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    version = assets_version()
    warnings = set()

    for lang in langs:
        strings = names[lang]
        shared = alines_parts(strings, data, warnings)
        for name, source in pages.items():
            here = page_dir(lang, default_lang, name)
            values = {"t." + k: v for k, v in strings.items()}
            values.update(shared)
            values["root"] = rel(here, "")
            values["lang"] = lang
            values["assets.version"] = version
            values["home"] = rel(here, page_dir(lang, default_lang, "index"))
            for other in pages:
                values["page." + other] = rel(here, page_dir(lang, default_lang, other))
            alternates, switcher = [], []
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
            nav = SRC / "pages" / f"{source}.nav.html"
            values["nav"] = render(nav.read_text(encoding="utf-8"), values, f"pages/{source}.nav.html ({lang})") if nav.exists() else ""
            body = (SRC / "pages" / f"{source}.html").read_text(encoding="utf-8")
            values["content"] = render(body, values, f"pages/{source}.html ({lang})")
            values["page_title"] = strings.get(f"{source}.title", strings["site.title"])
            values["page_description"] = strings.get(f"{source}.description", strings["site.description"])
            out_html = render(layout, values, f"layout.html ({lang}, {name})")
            target = OUT / here / "index.html" if here else OUT / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(out_html)

    shutil.copytree(SRC / "assets", OUT / "assets")
    (OUT / "CNAME").write_text(site["domain"] + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    built = sorted(str(p.relative_to(OUT)).replace("\\", "/") for p in OUT.rglob("index.html"))
    found = [n for n, v in data.items() if v]
    print(f"Built {len(built)} pages ({home} home, {', '.join(langs)}; data: {', '.join(found) or 'none'} from {data_dir.relative_to(ROOT)}):")
    for path in built:
        print("  " + path)
    for warning in sorted(warnings):
        print("Warning: " + warning)

    if "--check" in sys.argv:
        for path in OUT.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            if "{{" in text or "}}" in text:
                fail(f"{path}: a placeholder is left")
        print("Check OK")


if __name__ == "__main__":
    main()
