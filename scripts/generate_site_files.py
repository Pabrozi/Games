from __future__ import annotations

import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))
PAGES = json.loads((ROOT / "config" / "pages.json").read_text(encoding="utf-8"))


def list_html_pages() -> list[str]:
    excluded = set(CONFIG.get("exclude_from_sitemap", []))
    pages = []

    for page in PAGES:
        if not page.get("include_in_sitemap", True):
            continue
        if page["output"] in excluded:
            continue
        pages.append(page["output"])

    return sorted(pages)


def page_url(filename: str) -> str:
    base = CONFIG["site_url"].rstrip("/")
    if filename == "index.html":
        return f"{base}/"
    return f"{base}/{filename}"


def generate_sitemap(pages: list[str]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = date.today().isoformat()

    for page in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{page_url(page)}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def generate_robots() -> str:
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {CONFIG['site_url'].rstrip('/')}/sitemap.xml",
            "",
        ]
    )


def main() -> None:
    pages = list_html_pages()
    (ROOT / "sitemap.xml").write_text(generate_sitemap(pages), encoding="utf-8")
    (ROOT / "robots.txt").write_text(generate_robots(), encoding="utf-8")
    print(f"Generated sitemap.xml for {len(pages)} pages")
    print("Generated robots.txt")


if __name__ == "__main__":
    main()
