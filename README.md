# Claude Stuff

A collection of AI-powered productivity tools.

---

## YouTube Transcript Notes (`youtube_notes.py`)

Converts any YouTube video into structured, detailed notes using Claude AI.

**How it works:**
1. Tries to fetch YouTube's built-in captions (fast, free)
2. Falls back to downloading audio and transcribing with OpenAI Whisper if no captions exist
3. Sends the transcript to Claude to produce well-organised Markdown notes

### Setup

```bash
pip install -r requirements-youtube.txt
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Usage

```bash
# Basic — prints notes to terminal
python youtube_notes.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Save notes to a Markdown file
python youtube_notes.py "https://youtu.be/VIDEO_ID" -o notes.md

# Force audio transcription (ignores YouTube captions)
python youtube_notes.py "https://youtu.be/VIDEO_ID" --force-audio

# Use a larger Whisper model for better accuracy on audio fallback
python youtube_notes.py "https://youtu.be/VIDEO_ID" --force-audio --whisper-model medium

# Pass API key inline
python youtube_notes.py "https://youtu.be/VIDEO_ID" --api-key sk-ant-...
```

**Accepted URL formats:**
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/shorts/VIDEO_ID`

### Options

| Flag | Default | Description |
|---|---|---|
| `-o / --output PATH` | — | Save notes as a Markdown file |
| `--whisper-model` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `--force-audio` | off | Skip captions; transcribe audio with Whisper |
| `--api-key` | `$ANTHROPIC_API_KEY` | Anthropic API key |

### Notes format

Each set of notes includes:
- **Summary** — 2–3 sentence overview
- **Key Topics** — headings with detailed bullets
- **Notable Quotes / Insights** — standout lines worth remembering
- **Key Takeaways** — concise action points or conclusions

---

## LinkedIn Lead Scraper (`scraper.py`)

Scrapes people search results from LinkedIn and exports them to CSV or JSON.

> **Important:** Using automated tools to scrape LinkedIn may violate their
> [Terms of Service](https://www.linkedin.com/legal/user-agreement). Use this
> tool only for legitimate, authorized purposes (e.g. researching your own
> connections or in jurisdictions where such activity is lawful). Rate limiting
> and human-like behaviour are built in but do not guarantee compliance.

### Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

### Configuration

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

### Usage

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

### Output fields

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
