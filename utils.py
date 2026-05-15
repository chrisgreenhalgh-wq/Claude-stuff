import json
import logging
import random
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page


def setup_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
        level=getattr(logging, level.upper(), logging.INFO),
    )
    return logging.getLogger("linkedin-scraper")


def random_delay(min_s: float, max_s: float) -> None:
    time.sleep(random.uniform(min_s, max_s))


def human_type(page: Page, selector: str, text: str, delay_ms: int = 80) -> None:
    page.click(selector)
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.04, delay_ms / 1000))


def save_session(page: Page, session_file: str) -> None:
    cookies = page.context.cookies()
    Path(session_file).write_text(json.dumps(cookies, indent=2))


def load_session(page: Page, session_file: str) -> bool:
    path = Path(session_file)
    if not path.exists():
        return False
    cookies = json.loads(path.read_text())
    page.context.add_cookies(cookies)
    return True


def is_logged_in(page: Page) -> bool:
    page.goto("https://www.linkedin.com/feed/", timeout=30_000)
    return "feed" in page.url


def scroll_page(page: Page, times: int = 3, delay: float = 1.0) -> None:
    for _ in range(times):
        page.mouse.wheel(0, random.randint(300, 700))
        time.sleep(delay)


def build_search_url(cfg: dict) -> str:
    base = "https://www.linkedin.com/search/results/people/?"
    params: list[str] = []

    if cfg.get("keywords"):
        params.append(f"keywords={cfg['keywords'].replace(' ', '%20')}")
    if cfg.get("location"):
        params.append(f"geoUrn=%5B%22{cfg['location'].replace(' ', '%20')}%22%5D")
    if cfg.get("current_company"):
        params.append(f"company={cfg['current_company'].replace(' ', '%20')}")
    if cfg.get("job_title"):
        params.append(f"title={cfg['job_title'].replace(' ', '%20')}")

    degree_map = {"1": "F", "2": "S", "3+": "O"}
    if cfg.get("connection_degree") and cfg["connection_degree"] in degree_map:
        params.append(f"network=%5B%22{degree_map[cfg['connection_degree']]}%22%5D")

    return base + "&".join(params)
