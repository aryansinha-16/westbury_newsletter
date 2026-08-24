# Westbury Intelligence — Project Context

## What this is
Daily competitive-intelligence newsletter for the Westbury leadership team
(Westbury = India sports/lifestyle footwear & apparel marketplace seller).
Runs as a Railway cron worker, researches a watchlist, and emails an HTML
newsletter via the Valuecart email MCP (SendGrid).

Cloned from the proven `rk_newsletter` architecture (same dedup, same email
path, Claude Haiku). Different watchlist + a three-section format.

## Three intelligence sections
1. **Marketplaces** — India e-commerce / fashion marketplaces:
   Amazon India, Flipkart, Myntra, Ajio, Tata CLiQ, Nykaa Fashion, Reliance Retail.
2. **Nike & competitors** — India footwear/sportswear:
   Nike India, Puma India, Adidas India, Skechers India, New Balance India, Asics India.
3. **Westbury competition** — **BrandMan Retail** (closest competitor: full-stack
   retail platform for global sports/lifestyle brands in India — New Balance, Saucony,
   Anta, Wilson, On Running, Skechers reseller, Rockport; runs Sneakrz mono-brand stores).

## Stack
- **Python 3.12** — plain Anthropic API tool-use loop (no CrewAI)
- **Anthropic API** — `claude-haiku-4-5-20251001`, max_tokens=8096
- **Serper API** — Google News, `tbs=qdr:1d`, `gl=in`
- **RSS feeds** — Inc42, YourStory, Entrackr, Mint (past-2-day pubDate filter)
- **Email** — Valuecart email MCP at `https://valuecart-email-mcp-production.up.railway.app/mcp/valuecart2026`
- **Railway** — Dockerfile build, cron triggers daily

## Key files
- `main.py` — whole pipeline: watchlist, tools, agentic loop, prompt, entry point
- `render.py` — the email template ("Broadsheet"), shared with the RK newsletter.
  The model does NOT write HTML; it returns content via `submit_edition`.
- `history.py` — GitHub-backed sent-story memory (cross-run dedup)
- `Dockerfile` / `railway.json` / `Procfile` / `requirements.txt` — deploy
- `sent_history.json` — committed history store (starts empty `[]`)

## Story de-duplication (no repeats across days)
Railway containers are ephemeral, so sent-story history lives in the repo as
`sent_history.json`, read/written via the GitHub Contents API (`history.py`).
- Two horizons, split 2026-08-24: `ARCHIVE_DAYS = 180` for the file and the
  code-level filter, `PROMPT_DAYS = 14` for the model's DO-NOT-REPEAT list. They
  used to be one constant at 10, which DELETED a story on day 11 and let it be
  re-sent — the cause of the ~2-week repeat cycle seen live on the RK newsletter
  (re-send gaps measured at 12-17 days, never below 10).
- Filters are (a) normalized headline key, which also collapses trailing outlet
  suffixes like "- Reuters", and (b) normalized URL, for the same article under
  a reworded headline.
- Stories are banked from the `submit_edition` payload, so URLs are exact. The
  old version scraped `href`s out of the sent HTML and kept only exact string
  matches, banking roughly half the newsletter.
- **`GITHUB_TOKEN` MUST be a fine-grained PAT with `Contents: Read and write`.**
  A read-only token loads fine (GET 200) but every save fails with
  `403 Resource not accessible by personal access token` → dedup silently dies and
  the newsletter repeats. This exact bug bit the RK newsletter; don't repeat it.
  Verify a new token by doing a no-op PUT to the Contents API, not just a GET.

## Railway deployment
- Create repo `aryansinha-16/westbury-newsletter` (master) — or set `GITHUB_REPO`.
- New Railway service from that repo (Dockerfile builder).
- Env vars: `ANTHROPIC_API_KEY`, `SERPER_API_KEY`, `NEWSLETTER_RECIPIENTS`, `GITHUB_TOKEN`
  (optional: `GITHUB_REPO`, `GITHUB_BRANCH`).
- Cron: Railway Settings → Deploy → Cron Schedule (e.g. `30 2 * * *` = 8 AM IST).
- Script runs once and exits; Railway cron handles scheduling.

## Run locally
```bash
cd C:\Users\syste\westbury_newsletter
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in keys
python main.py
```

## Content vs formatting (changed 2026-08-24)
The model returns CONTENT, `render.py` does FORMATTING. It calls `submit_edition`
with `subject`, `exec_summary` and `stories[{company, headline, why, url}]`;
Python groups those into the three `SECTIONS`, adds every quiet entity with its
last-known story, renders and mails. So: identical layout every day, a
fabricated URL cannot reach the email, and the "quiet today" line is guaranteed
rather than something the model has to remember.

## Status
⚠️ This service has written no `sent_history.json` since **2026-07-24** — it
looks stopped or failing on Railway. The code here is current; the deployment is
not verified.
