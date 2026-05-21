#!/usr/bin/env python3
"""
Apollo.io people search — Canadian hospitality/entertainment/retail loyalty leaders.

Usage:
    export APOLLO_API_KEY="your_key_here"
    python apollo_search.py [--output leads.csv] [--max-results 200]
"""

import csv
import os
import sys
import time
import argparse
import requests

APOLLO_PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/search"

TARGET_TITLES = [
    "Chief Marketing Officer",
    "CMO",
    "VP of Marketing",
    "Vice President of Marketing",
    "VP Marketing",
    "Director of CRM",
    "Director CRM",
    "Director of Loyalty",
    "Director Loyalty",
    "Director of Customer Loyalty",
    "Head of CRM",
    "Head of Loyalty",
]

TARGET_INDUSTRIES = [
    "Hospitality",
    "Hotels and Motels",
    "Restaurants",
    "Food & Beverages",
    "Entertainment",
    "Leisure Travel & Tourism",
    "Gambling & Casinos",
    "Retail",
    "Supermarkets",
    "Sporting Goods",
]

CSV_COLUMNS = [
    "first_name",
    "last_name",
    "job_title",
    "company_name",
    "linkedin_url",
    "city",
]


def build_payload(page: int, per_page: int) -> dict:
    return {
        "page": page,
        "per_page": per_page,
        "person_titles": TARGET_TITLES,
        "person_locations": ["Canada"],
        "organization_locations": ["Canada"],
        "organization_industry_tag_names": TARGET_INDUSTRIES,
    }


def fetch_page(api_key: str, page: int, per_page: int = 25) -> dict:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    payload = build_payload(page, per_page)
    resp = requests.post(APOLLO_PEOPLE_SEARCH_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_person(person: dict) -> dict:
    org = person.get("organization") or {}
    return {
        "first_name": person.get("first_name", ""),
        "last_name": person.get("last_name", ""),
        "job_title": person.get("title", ""),
        "company_name": org.get("name", "") or person.get("organization_name", ""),
        "linkedin_url": person.get("linkedin_url", ""),
        "city": person.get("city", ""),
    }


def search(api_key: str, max_results: int, per_page: int = 25) -> list[dict]:
    results = []
    page = 1

    print(f"Searching Apollo.io (max {max_results} results, {per_page}/page)...")

    while len(results) < max_results:
        print(f"  Fetching page {page}...", end=" ", flush=True)
        try:
            data = fetch_page(api_key, page, per_page)
        except requests.HTTPError as exc:
            print(f"\nHTTP error on page {page}: {exc}")
            if exc.response is not None and exc.response.status_code in (429, 503):
                wait = 60
                print(f"Rate-limited — waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            break

        people = data.get("people", [])
        total = data.get("pagination", {}).get("total_entries", "?")
        print(f"got {len(people)} (total available: {total})")

        if not people:
            break

        for person in people:
            results.append(extract_person(person))
            if len(results) >= max_results:
                break

        total_pages = data.get("pagination", {}).get("total_pages", 1)
        if page >= total_pages:
            break

        page += 1
        time.sleep(1.2)  # stay within Apollo rate limits

    return results


def write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apollo.io Canadian loyalty leader search")
    parser.add_argument("--output", default="apollo_leads.csv", help="Output CSV path")
    parser.add_argument("--max-results", type=int, default=200, help="Max contacts to fetch")
    parser.add_argument("--per-page", type=int, default=25, choices=[10, 25, 50, 100],
                        help="Results per API page (100 requires paid plan)")
    args = parser.parse_args()

    api_key = os.environ.get("APOLLO_API_KEY", "").strip()
    if not api_key:
        sys.exit("Error: set APOLLO_API_KEY environment variable before running.")

    rows = search(api_key, args.max_results, args.per_page)

    if not rows:
        print("No results returned. Check your API key, plan limits, or search filters.")
        sys.exit(1)

    write_csv(rows, args.output)
    print(f"\nDone — {len(rows)} contacts written to {args.output}")


if __name__ == "__main__":
    main()
