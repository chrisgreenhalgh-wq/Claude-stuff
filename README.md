# LinkedIn Lead Scraper

Scrapes people search results from LinkedIn and exports them to CSV or JSON.

> **Important:** Using automated tools to scrape LinkedIn may violate their
> [Terms of Service](https://www.linkedin.com/legal/user-agreement). Use this
> tool only for legitimate, authorized purposes (e.g. researching your own
> connections or in jurisdictions where such activity is lawful). Rate limiting
> and human-like behaviour are built in but do not guarantee compliance.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Edit `config.yaml`:

```yaml
credentials:
  email: "you@example.com"
  password: "secret"

search:
  keywords: "software engineer"
  location: "San Francisco Bay Area"
  connection_degree: "2"   # "1", "2", or "3+"
  max_results: 100

output:
  format: "csv"   # or "json"
  filename: "leads"
  directory: "./output"
```

## Usage

```bash
# Basic run (browser visible, uses config.yaml)
python scraper.py

# Use a different config file
python scraper.py --config my_search.yaml

# Also visit each profile for email/about/phone (much slower)
python scraper.py --fetch-profiles

# Run headless (no browser window)
python scraper.py --headless

# Skip loading/saving the session cookie file
python scraper.py --no-save-session
```

## Output fields

| Field | Description |
|---|---|
| `name` | Full name |
| `profile_url` | LinkedIn profile URL |
| `job_title` | Current job title |
| `company` | Current company (from profile visit, if `--fetch-profiles`) |
| `location` | Location string |
| `connection_degree` | 1st / 2nd / 3rd+ |
| `mutual_connections` | Number of shared connections |
| `about` | About section (`--fetch-profiles`) |
| `email` | Contact email (`--fetch-profiles`, only if public) |
| `phone` | Phone (`--fetch-profiles`, only if public) |
| `website` | Website (`--fetch-profiles`, only if public) |
| `scraped_at` | ISO-8601 timestamp |

## Tips

- **Session persistence**: On first run the scraper logs in and saves a cookie
  file (`.session.json`). Subsequent runs reuse it to skip the login step.
- **Security checkpoints**: If LinkedIn shows a CAPTCHA or email verification
  challenge, complete it manually in the open browser window and press Enter in
  the terminal.
- **Proxy**: Set `scraper.proxy` in `config.yaml` to route traffic through a
  proxy (`http://user:pass@host:port`).
- **Rate limits**: Increase `min_delay` / `max_delay` if you see CAPTCHAs or
  unusual-activity warnings.
