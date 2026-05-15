"""
LinkedIn Lead Scraper
---------------------
Scrapes people search results from LinkedIn and exports them to CSV or JSON.

Usage:
    python scraper.py --config config.yaml

NOTE: Scraping LinkedIn may violate their Terms of Service. Use only for
legitimate, authorized purposes such as researching your own network or
in jurisdictions where such activity is lawful. The authors accept no
liability for misuse.
"""

import datetime
import json
import sys
from typing import List, Optional

import click
import yaml
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from exporters import export_leads
from models import Lead
from utils import (
    build_search_url,
    human_type,
    is_logged_in,
    load_session,
    random_delay,
    save_session,
    scroll_page,
    setup_logging,
)

console = Console()
log = setup_logging()

# ─── Selectors ────────────────────────────────────────────────────────────────

SEL_EMAIL = "#username"
SEL_PASSWORD = "#password"
SEL_SUBMIT = "button[type='submit']"
SEL_RESULT_CARD = "li.reusable-search__result-container"
SEL_NAME = "span.entity-result__title-text a"
SEL_TITLE = ".entity-result__primary-subtitle"
SEL_LOCATION = ".entity-result__secondary-subtitle"
SEL_DEGREE = ".dist-value"
SEL_NEXT_PAGE = "button[aria-label='Next']"


# ─── Auth ─────────────────────────────────────────────────────────────────────

def login(page: Page, email: str, password: str, min_d: float, max_d: float) -> bool:
    console.print("[bold yellow]Logging in to LinkedIn...[/]")
    page.goto("https://www.linkedin.com/login", timeout=30_000)
    random_delay(min_d, max_d)

    human_type(page, SEL_EMAIL, email)
    random_delay(0.5, 1.2)
    human_type(page, SEL_PASSWORD, password)
    random_delay(0.5, 1.0)

    page.click(SEL_SUBMIT)
    page.wait_for_load_state("networkidle", timeout=30_000)
    random_delay(min_d, max_d)

    if "checkpoint" in page.url or "challenge" in page.url:
        console.print("[bold red]LinkedIn is asking for a security checkpoint.[/]")
        console.print("Please complete it manually in the browser window, then press Enter.")
        input()
        page.wait_for_load_state("networkidle", timeout=60_000)

    if "feed" in page.url or page.locator(".global-nav__me-photo").count() > 0:
        console.print("[bold green]Login successful.[/]")
        return True

    console.print("[bold red]Login failed. Check your credentials.[/]")
    return False


# ─── Extraction ───────────────────────────────────────────────────────────────

def extract_leads_from_page(page: Page, min_d: float, max_d: float) -> List[Lead]:
    scroll_page(page, times=4, delay=0.8)
    random_delay(min_d, max_d)

    leads: List[Lead] = []
    cards = page.locator(SEL_RESULT_CARD).all()

    for card in cards:
        try:
            name_el = card.locator(SEL_NAME).first
            name = name_el.inner_text(timeout=3_000).strip()
            profile_url = name_el.get_attribute("href") or ""
            if profile_url and "?" in profile_url:
                profile_url = profile_url.split("?")[0]

            title = _safe_text(card, SEL_TITLE)
            location = _safe_text(card, SEL_LOCATION)
            degree = _safe_text(card, SEL_DEGREE)

            if not name or "LinkedIn Member" in name:
                continue

            leads.append(
                Lead(
                    name=name,
                    profile_url=profile_url,
                    job_title=title,
                    location=location,
                    connection_degree=degree,
                    scraped_at=datetime.datetime.utcnow().isoformat(),
                )
            )
        except Exception as exc:
            log.debug("Skipping card: %s", exc)
            continue

    return leads


def _safe_text(parent, selector: str) -> Optional[str]:
    try:
        el = parent.locator(selector).first
        if el.count() > 0:
            return el.inner_text(timeout=2_000).strip() or None
    except Exception:
        pass
    return None


def fetch_profile_details(page: Page, lead: Lead, min_d: float, max_d: float) -> None:
    """Visit the lead's profile and enrich with additional fields."""
    if not lead.profile_url:
        return
    try:
        page.goto(lead.profile_url, timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=20_000)
        random_delay(min_d, max_d)

        # Current company (often missing from search results)
        if not lead.company:
            try:
                exp_el = page.locator("#experience ~ div .t-bold span").first
                lead.company = exp_el.inner_text(timeout=3_000).strip() or None
            except Exception:
                pass

        # About section
        try:
            about_el = page.locator(".pv-about__summary-text span").first
            lead.about = about_el.inner_text(timeout=3_000).strip() or None
        except Exception:
            pass

        # Contact info modal
        try:
            contact_btn = page.locator("a#top-card-text-details-contact-info")
            if contact_btn.count() > 0:
                contact_btn.click()
                page.wait_for_selector(".pv-contact-info__contact-type", timeout=5_000)
                random_delay(0.5, 1.5)

                for item in page.locator(".pv-contact-info__contact-type").all():
                    label = _safe_text(item, ".pv-contact-info__header") or ""
                    value = _safe_text(item, ".pv-contact-info__ci-container") or ""
                    if "Email" in label:
                        lead.email = value
                    elif "Phone" in label:
                        lead.phone = value
                    elif "Website" in label:
                        lead.website = value

                close_btn = page.locator("button[aria-label='Dismiss']")
                if close_btn.count() > 0:
                    close_btn.click()
        except Exception:
            pass

    except Exception as exc:
        log.debug("Profile fetch failed for %s: %s", lead.profile_url, exc)


# ─── Main scraping loop ───────────────────────────────────────────────────────

def run_scrape(
    page: Page,
    cfg: dict,
    search_cfg: dict,
    output_cfg: dict,
    scraper_cfg: dict,
) -> List[Lead]:
    min_d = scraper_cfg.get("min_delay", 2.5)
    max_d = scraper_cfg.get("max_delay", 6.0)
    max_pages = scraper_cfg.get("max_pages", 10)
    max_results = search_cfg.get("max_results", 100)
    fetch_profiles = scraper_cfg.get("fetch_profiles", False)

    search_url = build_search_url(search_cfg)
    console.print(f"[cyan]Search URL:[/] {search_url}")
    page.goto(search_url, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    random_delay(min_d, max_d)

    all_leads: List[Lead] = []
    page_num = 1

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Scraping page {page_num}...", total=None)

        while page_num <= max_pages and len(all_leads) < max_results:
            progress.update(task, description=f"Scraping page {page_num} — {len(all_leads)} leads so far")
            leads = extract_leads_from_page(page, min_d, max_d)

            if not leads:
                console.print(f"[yellow]No results on page {page_num}, stopping.[/]")
                break

            if fetch_profiles:
                for lead in leads:
                    fetch_profile_details(page, lead, min_d, max_d)
                    random_delay(min_d, max_d)
                    # Navigate back to search results
                    page.go_back()
                    page.wait_for_load_state("networkidle", timeout=20_000)
                    random_delay(min_d / 2, max_d / 2)

            all_leads.extend(leads)

            # Flush to disk after each page
            filepath = export_leads(
                leads,
                output_cfg.get("directory", "./output"),
                output_cfg.get("filename", "leads"),
                output_cfg.get("format", "csv"),
            )

            if len(all_leads) >= max_results:
                console.print(f"[green]Reached max_results={max_results}.[/]")
                break

            # Paginate
            next_btn = page.locator(SEL_NEXT_PAGE)
            if next_btn.count() == 0 or not next_btn.is_enabled():
                console.print("[yellow]No more pages.[/]")
                break

            next_btn.scroll_into_view_if_needed()
            random_delay(min_d, max_d)
            next_btn.click()
            page.wait_for_load_state("networkidle", timeout=30_000)
            random_delay(min_d, max_d)
            page_num += 1

    return all_leads


# ─── CLI ──────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--config", "-c", default="config.yaml", help="Path to config YAML file.")
@click.option("--fetch-profiles", is_flag=True, default=False, help="Visit each profile page for more data (slower).")
@click.option("--headless", is_flag=True, default=False, help="Run browser in headless mode.")
@click.option("--no-save-session", is_flag=True, default=False, help="Do not save/load browser session.")
def main(config: str, fetch_profiles: bool, headless: bool, no_save_session: bool) -> None:
    with open(config, "r") as f:
        cfg = yaml.safe_load(f)

    creds = cfg.get("credentials", {})
    search_cfg = cfg.get("search", {})
    output_cfg = cfg.get("output", {})
    scraper_cfg = cfg.get("scraper", {})
    scraper_cfg["fetch_profiles"] = fetch_profiles

    if headless:
        scraper_cfg["headless"] = True

    email = creds.get("email") or click.prompt("LinkedIn email")
    password = creds.get("password") or click.prompt("LinkedIn password", hide_input=True)

    launch_opts: dict = {
        "headless": scraper_cfg.get("headless", False),
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    }
    if scraper_cfg.get("proxy"):
        launch_opts["proxy"] = {"server": scraper_cfg["proxy"]}

    with sync_playwright() as pw:
        browser: Browser = pw.chromium.launch(**launch_opts)
        context: BrowserContext = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page: Page = context.new_page()

        # Mask automation fingerprint
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        session_file = scraper_cfg.get("session_file", ".session.json")
        use_session = scraper_cfg.get("save_session", True) and not no_save_session
        logged_in = False

        if use_session and load_session(page, session_file):
            console.print("[dim]Loaded saved session, checking if still valid...[/]")
            logged_in = is_logged_in(page)
            if logged_in:
                console.print("[green]Session still valid — skipping login.[/]")

        if not logged_in:
            logged_in = login(
                page, email, password,
                scraper_cfg.get("min_delay", 2.5),
                scraper_cfg.get("max_delay", 6.0),
            )
            if not logged_in:
                console.print("[red]Could not log in. Exiting.[/]")
                browser.close()
                sys.exit(1)
            if use_session:
                save_session(page, session_file)
                console.print(f"[dim]Session saved to {session_file}[/]")

        leads = run_scrape(page, cfg, search_cfg, output_cfg, scraper_cfg)

        browser.close()

    if not leads:
        console.print("[yellow]No leads found.[/]")
        return

    filepath = export_leads(
        leads,
        output_cfg.get("directory", "./output"),
        output_cfg.get("filename", "leads"),
        output_cfg.get("format", "csv"),
    )

    console.print(f"\n[bold green]Done! {len(leads)} leads saved to {filepath}[/]")

    table = Table(title="Sample leads (first 5)", show_lines=True)
    for col in ["name", "job_title", "company", "location", "profile_url"]:
        table.add_column(col.replace("_", " ").title(), overflow="fold")
    for lead in leads[:5]:
        d = lead.to_dict()
        table.add_row(
            d.get("name") or "",
            d.get("job_title") or "",
            d.get("company") or "",
            d.get("location") or "",
            d.get("profile_url") or "",
        )
    console.print(table)


if __name__ == "__main__":
    main()
