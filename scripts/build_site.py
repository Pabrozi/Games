from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SITE_CONFIG = json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))
PAGES = json.loads((ROOT / "config" / "pages.json").read_text(encoding="utf-8"))
TEMPLATE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
SOURCE_ROOT = ROOT / "src"


def absolute_url(path_or_url: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    base = SITE_CONFIG["site_url"].rstrip("/")
    return f"{base}/{path_or_url.lstrip('/')}"


def canonical_url(canonical_path: str) -> str:
    if canonical_path in ("", "/"):
        return SITE_CONFIG["site_url"].rstrip("/") + "/"
    return absolute_url(canonical_path)


def html_escape(value: str) -> str:
    return html.escape(value, quote=True)


def load_optional_file(relative_path: str | None) -> str:
    if not relative_path:
        return ""
    path = SOURCE_ROOT / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def render_fragment(text: str, page: dict[str, Any], canonical: str, og_image: str) -> str:
    replacements = {
        "{{SITE_NAME}}": SITE_CONFIG["site_name"],
        "{{SITE_URL}}": SITE_CONFIG["site_url"].rstrip("/"),
        "{{CANONICAL_URL}}": canonical,
        "{{CANONICAL_PATH}}": page["canonical_path"],
        "{{OG_IMAGE_URL}}": og_image,
        "{{APPLE_TOUCH_ICON_URL}}": absolute_url(SITE_CONFIG["apple_touch_icon"]),
        "{{CONTACT_EMAIL}}": SITE_CONFIG["contact_email"],
        "{{INLINE_AD_LABEL}}": SITE_CONFIG["inline_ad_label"],
    }
    rendered = text
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def render_nav(active_href: str | None) -> str:
    links = []
    for item in SITE_CONFIG["nav_links"]:
        classes = ' class="active"' if item["href"] == active_href else ""
        links.append(f'  <a{classes} href="{html_escape(item["href"])}">{html.escape(item["label"])}</a>')
    return "\n".join(links)


def render_footer_links() -> str:
    return " |\n    ".join(
        f'<a href="{html_escape(item["href"])}">{html.escape(item["label"])}</a>'
        for item in SITE_CONFIG["footer_links"]
    )


def build_page(page: dict[str, Any]) -> str:
    canonical = canonical_url(page["canonical_path"])
    og_image = absolute_url(page.get("og_image", SITE_CONFIG["default_og_image"]))
    body_classes = " ".join(page.get("body_classes", []))
    body_attributes = f' class="{html_escape(body_classes)}"' if body_classes else ""

    main_content = render_fragment(load_optional_file(page["content_file"]), page, canonical, og_image)
    extra_head = render_fragment(load_optional_file(page.get("extra_head_file")), page, canonical, og_image)
    page_script = render_fragment(load_optional_file(page.get("script_file")), page, canonical, og_image)

    replacements = {
        "{{HTML_LANG}}": SITE_CONFIG["html_lang"],
        "{{TITLE}}": html_escape(page["title"]),
        "{{DESCRIPTION}}": html_escape(page["description"]),
        "{{ROBOTS}}": html_escape(page.get("robots", SITE_CONFIG["default_robots"])),
        "{{THEME_COLOR}}": html_escape(page.get("theme_color", SITE_CONFIG["theme_color"])),
        "{{CANONICAL_URL}}": html_escape(canonical),
        "{{FAVICON_SVG}}": html_escape(SITE_CONFIG["favicon_svg"]),
        "{{FAVICON_PNG}}": html_escape(SITE_CONFIG["favicon_png"]),
        "{{APPLE_TOUCH_ICON}}": html_escape(SITE_CONFIG["apple_touch_icon"]),
        "{{WEB_MANIFEST}}": html_escape(SITE_CONFIG["manifest"]),
        "{{OG_LOCALE}}": html_escape(SITE_CONFIG["og_locale"]),
        "{{SITE_NAME}}": html_escape(SITE_CONFIG["site_name"]),
        "{{OG_TYPE}}": html_escape(page.get("og_type", SITE_CONFIG["default_og_type"])),
        "{{OG_TITLE}}": html_escape(page.get("og_title", page["title"])),
        "{{OG_DESCRIPTION}}": html_escape(page.get("og_description", page["description"])),
        "{{OG_IMAGE_URL}}": html_escape(og_image),
        "{{TWITTER_CARD}}": html_escape(page.get("twitter_card", SITE_CONFIG["default_twitter_card"])),
        "{{TWITTER_TITLE}}": html_escape(page.get("twitter_title", page.get("og_title", page["title"]))),
        "{{TWITTER_DESCRIPTION}}": html_escape(page.get("twitter_description", page.get("og_description", page["description"]))),
        "{{EXTRA_HEAD}}": ("\n" + extra_head) if extra_head else "",
        "{{BODY_ATTRIBUTES}}": body_attributes,
        "{{TAGLINE}}": html.escape(SITE_CONFIG["tagline"]),
        "{{NAV_LINKS}}": render_nav(page.get("active_nav")),
        "{{SIDE_AD_LABEL}}": html.escape(SITE_CONFIG["ad_label"]),
        "{{MAIN_CONTENT}}": main_content,
        "{{COPYRIGHT_YEAR}}": str(page.get("copyright_year", 2026)),
        "{{FOOTER_LINKS}}": render_footer_links(),
        "{{PAGE_SCRIPT}}": "",
    }

    if page_script:
        replacements["{{PAGE_SCRIPT}}"] = f"\n<script>\n{page_script}\n</script>"

    output = TEMPLATE
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, value)
    return output


def main() -> None:
    for page in PAGES:
        html_output = build_page(page).rstrip() + "\n"
        (ROOT / page["output"]).write_text(html_output, encoding="utf-8")
        print(f"Built {page['output']}")


if __name__ == "__main__":
    main()
