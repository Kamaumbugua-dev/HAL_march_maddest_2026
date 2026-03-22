# 🏀 Maddest Offers — Axon Lattice Deal Finder

> An internal staff portal for searching, exploring and comparing appliance deals in the Axon Lattice Maddest Offers promotion.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3+-black?style=flat-square&logo=flask)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat-square&logo=vite)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite)

---

## Overview

Maddest Offers is a full-stack internal web application that allows Axon Lattice staff to instantly check whether any appliance is part of the current promotional offer, view pricing details, compare savings, and discover the best deals across 11 categories and 6 brands.

Discounts range from **17% to 47% off** across 38 products including refrigerators, TVs, washing machines, air fryers, microwaves, freezers, blenders, cookers and more.

---

## Features

### Search
- **Fuzzy + semantic search** — handles typos, partial names, abbreviations (WM, MWO, REF) and model codes
- **ACTIVE badge** — exact matches (high confidence) appear in a dedicated section with a green pulse indicator
- **SORRY, ITEM NOT ON OFFER** — clear feedback with category shortcuts when an item isn't in the promotion
- **Autocomplete suggestions** — instant results as you type, local filtered from product data
- **Glowing search button** — animated hover glow effect
- **Category filtering** — filter by Refrigerators, TVs, Washing Machines, Air Fryers and more

### Steve — AI Assistant
- **Proactive deal finder** — tell Steve what you want ("find me an LG fridge") and he searches and returns matching product cards inline in the chat
- **Smart follow-up questions** — if your query is vague, Steve asks clarifying questions to narrow down the search
- **Budget deals** — ask "show me products under KES 30,000"
- **Brand comparison** — ask Steve to compare brands or show top picks from a specific brand
- **Quick reply buttons** — common queries available at one tap

### Analytics
- Total searches, top search terms, search activity over time
- Products by category (doughnut chart)
- Searches by category (bar chart)
- Top discounts table with savings breakdown
- Zero-result searches — identifies gaps in the offer

### Pages
| Page | Description |
|------|-------------|
| **Home** | Search, category browse, featured deals |
| **Analytics** | Charts and search insights |
| **FAQ** | 10 collapsible questions about the offer and portal |
| **About** | Brand breakdown, how-it-works, tech stack |
| **Contact** | Form connected to Formspree — delivers to inbox |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, Flask 2.3 |
| Search | RapidFuzz (fuzzy), scikit-learn TF-IDF (semantic) |
| Database | SQLite 3 |
| Frontend | React 18, Vite 8 |
| Charts | Chart.js 4, react-chartjs-2 |
| Email | Formspree |
| Deployment | Vercel (frontend + serverless API), Render (alternative) |

---

## Project Structure

```
march-madness/
├── app.py                  # Flask backend — search, Steve bot, analytics, contact APIs
├── init_db.py              # Parses Excel file and populates SQLite database
├── march_madness.db        # Pre-built SQLite database (38 products)
├── product pricing.xlsx    # Source data (official promotional price sheet)
├── requirements.txt        # Python dependencies
├── render.yaml             # Render.com deployment config
├── Procfile                # Gunicorn start command
├── vercel.json             # Vercel deployment config
├── api/
│   └── index.py            # Vercel serverless entry point
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── index.css
    │   └── components/
    │       ├── HomePage.jsx
    │       ├── AnalyticsPage.jsx
    │       ├── FAQPage.jsx
    │       ├── AboutPage.jsx
    │       ├── ContactPage.jsx
    │       ├── Navbar.jsx
    │       ├── ProductCard.jsx
    │       ├── ProductModal.jsx
    │       └── SteveBot.jsx
    ├── dist/               # Production build (committed for Vercel)
    ├── package.json
    └── vite.config.js
```

---

## Search Architecture

The search engine uses a multi-stage scoring pipeline:

1. **Exact item code match** — score 100
2. **Substring match** — if the full query appears in the product name, score 95
3. **Fuzzy matching** — RapidFuzz `partial_ratio` + `token_set_ratio` on original query
4. **Expanded query fuzzy** — same fuzzy matching on an expanded version of the query (abbreviations resolved: `WM → washing machine`, `MWO → microwave`, `REF → fridge`)
5. **TF-IDF semantic similarity** — `char_wb` analyser, ngram range (2,4), cosine similarity
6. **Multi-token coverage bonus** — products matching all query tokens receive a +12 point boost
7. **Adaptive threshold** — 10 for item codes, 50 for short queries (≤4 chars), 42 for normal queries

Results with score ≥ 82 are shown as **ACTIVE exact matches**. Results below threshold are filtered out entirely.

---

## Getting Started (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 20+

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/Kamaumbugua-dev/HAL_march_maddest_2026.git
cd HAL_march_maddest_2026

# Install Python dependencies
pip install -r requirements.txt

# Build the database from the Excel file
python init_db.py

# Start Flask
python app.py
```

Flask runs on `http://localhost:5000`.

### Frontend Setup (Dev Server with Hot Reload)

```bash
cd frontend
npm install
npm run dev
```

React dev server runs on `http://localhost:3000` and proxies `/api` requests to Flask.

### Production Build

```bash
cd frontend
npm run build
```

The built files are output to `frontend/dist/` and served by Flask.

---

## Deployment

### Vercel (Current)

The project is configured for Vercel via `vercel.json`:
- Static files are served from `frontend/dist/`
- All `/api/*` routes are handled by `api/index.py` as a Python serverless function
- The pre-built SQLite database is copied to `/tmp` at cold start for write access

**Environment Variables required on Vercel:**

| Variable | Description |
|----------|-------------|
| `RESEND_API_KEY` | Optional — only needed if switching from Formspree to Resend for email |

### Render (Alternative)

Configured via `render.yaml`. The build command runs `pip install`, `python init_db.py` and `npm run build` automatically. Start command: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT --timeout 120`.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Search products. Body: `{ query, category }` |
| `/api/categories` | GET | List all categories with counts |
| `/api/products` | GET | List all products |
| `/api/analytics` | GET | Analytics data (searches, trends, top discounts) |
| `/api/steve` | POST | Steve bot. Body: `{ message }`. Returns `{ response, products }` |
| `/api/contact` | POST | Contact form. Body: `{ name, email, subject, message }` |

---

## Brands & Categories

**Brands:** LG · Hisense · Von · NutriCook · Nutri Bullet · Simfer

**Categories:** Refrigerators · TVs · Washing Machines · Washer-Dryers · Microwaves · Air Fryers · Freezers · Blenders · Cookers · Water Dispensers · Personal Care

---

## License

Internal use only — Axon Lattice. Not for public distribution.
