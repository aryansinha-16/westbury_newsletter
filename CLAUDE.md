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
- `history.py` — GitHub-backed sent-story memory (cross-run dedup)
- `Dockerfile` / `railway.json` / `Procfile` / `requirements.txt` — deploy
- `sent_history.json` — committed history store (starts empty `[]`)

## Story de-duplication (no repeats across days)
Railway containers are ephemeral, so sent-story history lives in the repo as
`sent_history.json`, read/written via the GitHub Contents API (`history.py`).
- Each run loads last 10 days of sent headlines, normalizes to a loose key
  (sorted significant words), and (a) pre-filters search/RSS hits, (b) passes
  the headlines to the model as a "DO NOT REPEAT" list.
- After send, URLs in the email's `href`s are matched back to titles and appended.
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
