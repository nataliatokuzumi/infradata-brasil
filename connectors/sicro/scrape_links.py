import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from connectors.sicro.database import SicroDownloadsDatabase
from connectors.sicro.settings import sicro_base_url, database_path, sicro_regions


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self.links.append(href)


def normalize_url(base_url: str, href: str) -> str | None:
    if not href:
        return None
    if href.startswith(("mailto:", "tel:", "javascript:")):
        return None

    absolute_url = urljoin(base_url, href)
    parsed = urlparse(absolute_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return absolute_url


def should_follow(url: str) -> bool:
    path = urlparse(url).path.lower()
    print(path)
    return any(path.endswith(ext) for ext in (".7z", ".zip", ".rar", ".tar", ".gz")) or "." in path


def save_links(database: SicroDownloadsDatabase, source_url: str, links: list[str]) -> None:
    for link in links:
        tokens = link.split("/")
        region = tokens[-5]
        state_code = tokens[-4]
        year = tokens[-3]
        month = tokens[-2]
        filename = tokens[-1]
        revisado = "revisado" in filename.lower()
        extension = filename.split(".")[-1]
        year = year.split("-")[0] if "-" in year else year
        month = month.split("-")[0] if "-" in month else month
        # skip if URL already recorded
        try:
            if database.url_exists(link):
                continue
        except Exception:
            # defensive: if url_exists not available or DB error, fall back to insert
            pass

        database.insert_download(
            url=link,
            region=region,
            state_code=state_code,
            year=year,
            month=month,
            revisado=revisado,
            filename=filename,
            extension=extension,
            status="pending",
        )


def scrape_links(url: str, database: SicroDownloadsDatabase, visited: set[str] | None = None, depth: int = 0, max_depth: int = 5) -> list[str]:
    if visited is None:
        visited = set()

    if url in visited or depth > max_depth:
        return []

    visited.add(url)

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Falha ao acessar {url}: {exc}")
        return []

    parser = LinkParser()
    parser.feed(response.text)

    normalized_links = []
    page_links = []
    seen = set()
    for href in parser.links:
        normalized = normalize_url(url, href)
        if not normalized:
            continue

        lower_url = normalized.lower()
        if not normalized.startswith(sicro_base_url):
            continue
        if any(token in lower_url for token in ("notarevisional", "nota-revisional", "/search")):
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        last_segment = normalized.split("/")[-1]
        if "." in last_segment:
            normalized_links.append(normalized)
        else:
            page_links.append(normalized)

    save_links(database, url, normalized_links)

    for link in page_links:
        scrape_links(link, database, visited, depth + 1, max_depth)

    return normalized_links


def main() -> None:

    parser = argparse.ArgumentParser(description="Extrair links de uma página e salvar em um banco SQLite")
    parser.add_argument("--region", help="Região a ser analisada (ex: sudeste)", choices=sicro_regions)
    parser.add_argument("--db", default=database_path, help="Caminho para o banco de dados")
    parser.add_argument("--max-depth", type=int, default=5, help="Profundidade máxima de navegação (padrão: 5)")
    args = parser.parse_args()

    database = SicroDownloadsDatabase(db_path=str(Path(args.db).resolve()))

    regions = [args.region] if args.region else sicro_regions

    for region in regions:
        if region == 'nordeste':
            base_url = f"{sicro_base_url}/{region}"
            links = scrape_links(base_url, database, max_depth=args.max_depth)

            print(f"Links encontrados em {base_url}:")
            for link in links:
                print(link)
            print(f"\nURLs salvas em {Path(args.db).resolve()}")


if __name__ == "__main__":
    main()
