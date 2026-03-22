"""
app.py — Maddest Offers Deal Finder
Axon Lattice Internal Tool  |  Flask + SQLite + Fuzzy + TF-IDF Search
"""
import os
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, send_from_directory, request
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ─── Setup ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'march_madness.db'))
REACT_DIR  = os.path.join(BASE_DIR, 'frontend', 'dist')  # Vite build output

app = Flask(__name__, static_folder=None)   # disable default static handling


# ─── Serve React SPA (defined last so API routes take priority) ───────────────
def _serve_react_spa(path):
    """Serve the React build; fall back to index.html for client-side routing."""
    target = os.path.join(REACT_DIR, path)
    if path and os.path.isfile(target):
        return send_from_directory(REACT_DIR, path)
    return send_from_directory(REACT_DIR, 'index.html')

# TF-IDF globals (loaded once at startup)
_tfidf_vectorizer = None
_tfidf_matrix     = None
_product_list     = []   # ordered list matching tfidf matrix rows

# ─── DB helpers ───────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_tfidf():
    """Pre-build TF-IDF matrix from all products for semantic search."""
    global _tfidf_vectorizer, _tfidf_matrix, _product_list
    conn = get_db()
    rows = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    _product_list = [dict(r) for r in rows]
    if not _product_list:
        return
    corpus = [
        f"{p['item_name']} {p['category']} {p['brand']} {p['item_code']}"
        for p in _product_list
    ]
    _tfidf_vectorizer = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(2, 4),
        max_features=8000,
        sublinear_tf=True,
    )
    _tfidf_matrix = _tfidf_vectorizer.fit_transform(corpus)


# ─── Query expansion (maps common terms → abbreviations used in product names) ─

EXPANSIONS = {
    'fridge':        ['fridge', 'ref', 'refrigerator', 'tmf', 'sbs', 'bcd'],
    'refrigerator':  ['fridge', 'ref', 'refrigerator', 'tmf', 'sbs'],
    'freezer':       ['freezer', 'chest freezer', 'fc'],
    'washing':       ['washing', 'w/m', 'wm', 'washer'],
    'washer':        ['washer', 'w/m', 'wm', 'washing machine'],
    'dryer':         ['dryer', 'w/dryer', 'w-dryer', 'wd'],
    'microwave':     ['microwave', 'mwo'],
    'mwo':           ['microwave', 'mwo'],
    'tv':            ['tv', 'television', 'uled', 'fhd', 'uhd', '4k'],
    'television':    ['tv', 'television', 'uled', 'fhd'],
    'air fryer':     ['air fryer', 'airfryer', 'af'],
    'fryer':         ['fryer', 'air fryer', 'af'],
    'blender':       ['blender', 'nutribullet', 'nutri bullet'],
    'cooker':        ['cooker', 'stove', 'hob'],
    'dispenser':     ['dispenser', 'water dispenser'],
    'steamer':       ['steamer', 'garment'],
}

def expand_query(query: str) -> str:
    """Expand abbreviations and synonyms to improve matching."""
    q = query.lower().strip()
    extras = []
    for key, alts in EXPANSIONS.items():
        if key in q:
            extras.extend(alts)
    if extras:
        return q + ' ' + ' '.join(extras)
    return q


# ─── Search ───────────────────────────────────────────────────────────────────

def search_products(query: str, category: str = 'All', limit: int = 20):
    query = query.strip()
    conn  = get_db()

    if category and category != 'All':
        rows = conn.execute('SELECT * FROM products WHERE category = ?', (category,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM products').fetchall()
    conn.close()

    products = [dict(r) for r in rows]
    if not products:
        return []

    is_code_query = query.isdigit()
    q_lower       = query.lower()
    q_expanded    = expand_query(query)   # e.g. "washing machine" → adds "wm w/m washer"
    q_exp_lower   = q_expanded.lower()
    scored        = []

    for p in products:
        score         = 0.0
        name_lower    = p['item_name'].lower()
        # Build a rich corpus string for this product for expanded matching
        corpus_str    = f"{name_lower} {p['category'].lower()} {p['brand'].lower()} {p['item_code']}"

        # 1. Exact item-code / substring code match
        if is_code_query:
            if query == p['item_code']:
                score = 100.0
            elif query in p['item_code']:
                score = 94.0

        # 2a. Model-number substring match — if the whole query appears inside the name
        if not is_code_query and q_lower in name_lower:
            score = max(score, 95.0)

        # 2b. Fuzzy on item name — original query
        partial   = fuzz.partial_ratio(q_lower, name_lower)
        token_set = fuzz.token_set_ratio(q_lower, name_lower)
        score     = max(score, max(partial, token_set) * 0.90)

        # 2c. Fuzzy on item name — expanded query (catches abbreviations like WM, MWO, REF)
        if q_expanded != q_lower:
            exp_partial   = fuzz.partial_ratio(q_exp_lower, corpus_str)
            exp_token_set = fuzz.token_set_ratio(q_exp_lower, corpus_str)
            score = max(score, max(exp_partial, exp_token_set) * 0.85)

        # 3. Brand match boost
        if p['brand'].lower() in q_lower:
            score = max(score, fuzz.partial_ratio(p['brand'].lower(), q_lower) * 0.70)

        # 4. Category name match
        score = max(score, fuzz.ratio(q_lower, p['category'].lower()) * 0.70)

        scored.append([score, p])

    # 5. TF-IDF semantic layer on expanded query
    if _tfidf_vectorizer is not None and len(query) >= 2:
        try:
            q_vec       = _tfidf_vectorizer.transform([q_expanded])
            code_to_idx = {p['item_code']: i for i, p in enumerate(_product_list)}
            indices     = [code_to_idx.get(p['item_code']) for _, p in scored]
            valid       = [(i, j) for j, i in enumerate(indices) if i is not None]
            if valid:
                global_idx = [i for i, _ in valid]
                local_idx  = [j for _, j in valid]
                tfidf_sims = cosine_similarity(q_vec, _tfidf_matrix[global_idx])[0]
                for k, j in enumerate(local_idx):
                    scored[j][0] = max(scored[j][0], tfidf_sims[k] * 100 * 0.88)
        except Exception:
            pass

    # 6. Multi-token coverage bonus — reward products matching more query words
    query_tokens = [t for t in q_lower.split() if len(t) >= 3]
    if len(query_tokens) >= 2:
        for entry in scored:
            s, p = entry
            corpus = f"{p['item_name'].lower()} {p['category'].lower()} {p['brand'].lower()}"
            expanded_tokens = q_exp_lower.split()
            matched = sum(1 for t in expanded_tokens if t in corpus)
            if matched >= len(query_tokens):
                entry[0] = s + 12.0   # bonus for matching all query tokens

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Adaptive threshold: precise for specific codes, relaxed for broad queries
    if is_code_query:
        threshold = 10
    elif len(query) <= 4:          # short queries like "LG", "TMF"
        threshold = 50
    else:                          # normal queries
        threshold = 42

    filtered = [(round(s, 1), p) for s, p in scored if s >= threshold]
    return filtered[:limit]


# ─── API Routes ───────────────────────────────────────────────────────────────


@app.route('/api/search', methods=['POST'])
def api_search():
    data     = request.get_json(force=True)
    query    = (data.get('query') or '').strip()
    category = (data.get('category') or 'All').strip()

    if not query and category == 'All':
        return jsonify({'results': [], 'message': '', 'in_offer': None, 'count': 0})

    if not query and category != 'All':
        conn    = get_db()
        rows    = conn.execute(
            'SELECT * FROM products WHERE category = ?', (category,)
        ).fetchall()
        conn.close()
        results_data = [{'score': 100, 'product': dict(r)} for r in rows]
    else:
        found        = search_products(query, category)
        results_data = [{'score': s, 'product': p} for s, p in found]

    count    = len(results_data)
    in_offer = count > 0

    if query:
        msg = (
            f"Found {count} product{'s' if count != 1 else ''} on the March Madness offer!"
            if in_offer
            else f"'{query}' is not in the March Madness offer. Browse categories for similar deals."
        )
    else:
        msg = f"Showing all {count} products in {category}."

    # Log the search
    if query or category != 'All':
        conn = get_db()
        conn.execute(
            'INSERT INTO search_logs (query, category, results_count, timestamp) VALUES (?, ?, ?, ?)',
            (query, category, count, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    return jsonify({'results': results_data, 'message': msg, 'in_offer': in_offer, 'count': count})


@app.route('/api/categories')
def api_categories():
    conn  = get_db()
    rows  = conn.execute(
        'SELECT category, category_icon, COUNT(*) as cnt '
        'FROM products GROUP BY category ORDER BY cnt DESC'
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/products')
def api_products():
    category = request.args.get('category', 'All')
    conn     = get_db()
    if category != 'All':
        rows = conn.execute('SELECT * FROM products WHERE category = ?', (category,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/analytics')
def api_analytics():
    conn = get_db()

    top_searches = conn.execute('''
        SELECT query, SUM(1) as count
        FROM search_logs
        WHERE query != ''
        GROUP BY LOWER(TRIM(query))
        ORDER BY count DESC
        LIMIT 10
    ''').fetchall()

    cat_searches = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM search_logs
        WHERE category != 'All' AND category != '' AND category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
    ''').fetchall()

    daily = conn.execute('''
        SELECT DATE(timestamp) as day, COUNT(*) as count
        FROM search_logs
        GROUP BY DATE(timestamp)
        ORDER BY day ASC
        LIMIT 14
    ''').fetchall()

    total = conn.execute('SELECT COUNT(*) FROM search_logs').fetchone()[0]

    cat_dist = conn.execute('''
        SELECT category, category_icon, COUNT(*) as count
        FROM products GROUP BY category ORDER BY count DESC
    ''').fetchall()

    top_discounts = conn.execute('''
        SELECT item_name, brand, new_discount, new_promo_rrp, sale_rrp, category_icon
        FROM products ORDER BY new_discount DESC LIMIT 5
    ''').fetchall()

    zero_results = conn.execute('''
        SELECT query, COUNT(*) as count
        FROM search_logs
        WHERE results_count = 0 AND query != ''
        GROUP BY LOWER(TRIM(query))
        ORDER BY count DESC
        LIMIT 5
    ''').fetchall()

    conn.close()
    return jsonify({
        'top_searches':         [dict(r) for r in top_searches],
        'category_searches':    [dict(r) for r in cat_searches],
        'daily_searches':       [dict(r) for r in daily],
        'total_searches':       total,
        'category_distribution':[dict(r) for r in cat_dist],
        'top_discounts':        [dict(r) for r in top_discounts],
        'zero_results':         [dict(r) for r in zero_results],
    })


@app.route('/api/steve', methods=['POST'])
def steve_bot():
    data    = request.get_json(force=True)
    message = (data.get('message') or '').strip()
    conn    = get_db()
    resp, products = _steve_response(message.lower(), conn)
    conn.close()
    return jsonify({'response': resp, 'products': products})


@app.route('/api/contact', methods=['POST'])
def api_contact():
    """Send a contact form message via Resend."""
    data    = request.get_json(force=True)
    name    = (data.get('name')    or '').strip()
    email   = (data.get('email')   or '').strip()
    subject = (data.get('subject') or 'Contact Form Message').strip()
    message = (data.get('message') or '').strip()

    if not name or not email or not message:
        return jsonify({'ok': False, 'error': 'Name, email and message are required.'}), 400

    api_key = os.environ.get('RESEND_API_KEY', '')
    if not api_key:
        return jsonify({'ok': False, 'error': 'Mail service not configured.'}), 503

    try:
        import urllib.request, json as _json
        payload = _json.dumps({
            'from':    'Maddest Offers <onboarding@resend.dev>',
            'to':      ['delivered@resend.dev'],
            'reply_to': email,
            'subject': f'[Contact] {subject} — from {name}',
            'html':    (f'<p><strong>From:</strong> {name} ({email})</p>'
                        f'<p><strong>Subject:</strong> {subject}</p>'
                        f'<hr><p>{message.replace(chr(10), "<br>")}</p>'),
        }).encode()
        req = urllib.request.Request(
            'https://api.resend.com/emails',
            data=payload,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req, timeout=10)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ─── Steve Bot logic ──────────────────────────────────────────────────────────

# Keywords that signal the user wants to find/search a product
_SEARCH_TRIGGERS = [
    'find', 'show me', 'do you have', 'looking for', 'want', 'need a',
    'search for', 'check if', 'is there', 'any deals on', 'got any',
    'find me', 'get me', 'what about', 'tell me about', 'price of',
    'cost of', 'is the', 'on offer', 'available', 'deals on', 'deal on',
]

_AMBIGUOUS = ['something', 'item', 'product', 'appliance', 'stuff', 'thing', 'anything']

_CATEGORIES = {
    'fridge': 'Refrigerators', 'refrigerator': 'Refrigerators', 'ref': 'Refrigerators',
    'tv': 'TVs', 'television': 'TVs', 'screen': 'TVs',
    'washer': 'Washing Machines', 'washing machine': 'Washing Machines', 'wm': 'Washing Machines',
    'washer dryer': 'Washer-Dryers', 'washer-dryer': 'Washer-Dryers', 'wd': 'Washer-Dryers',
    'microwave': 'Microwaves', 'mwo': 'Microwaves',
    'air fryer': 'Air Fryers', 'fryer': 'Air Fryers', 'airfryer': 'Air Fryers',
    'freezer': 'Freezers', 'chest freezer': 'Freezers',
    'blender': 'Blenders', 'nutribullet': 'Blenders',
    'cooker': 'Cookers', 'stove': 'Cookers',
    'dispenser': 'Water Dispensers', 'water dispenser': 'Water Dispensers',
}


def _extract_search_term(msg: str) -> str:
    """Strip trigger words and return the likely product term."""
    term = msg
    for t in sorted(_SEARCH_TRIGGERS, key=len, reverse=True):
        term = term.replace(t, ' ')
    # Strip filler
    for filler in ['me', 'a', 'an', 'the', 'any', 'some', 'please', 'for', 'on', 'if', 'is']:
        term = (' ' + term + ' ').replace(f' {filler} ', ' ').strip()
    return term.strip(' ?,.')


def _steve_response(msg: str, conn) -> tuple:  # noqa: C901
    """Natural-language intent matching for Steve bot. Returns (text, products_list)."""

    def has(*phrases): return any(p in msg for p in phrases)
    def r(text, products=None): return (text, products or [])

    def top_by(col, n=3, order='DESC'):
        return conn.execute(
            f'SELECT * FROM products ORDER BY {col} {order} LIMIT ?', (n,)
        ).fetchall()

    def products_for_category(cat):
        return [dict(row) for row in conn.execute(
            'SELECT * FROM products WHERE category=? ORDER BY new_discount DESC', (cat,)
        ).fetchall()]

    def do_search(term):
        """Run search and return list of product dicts (top 3)."""
        found = search_products(term, 'All', limit=3)
        return [p for _, p in found]

    # ── Greetings ────────────────────────────────────────────────────────────
    if has('hi', 'hello', 'hey', 'howdy', 'sup', 'hola', 'good morning', 'good afternoon', 'good evening'):
        return r("Hey! 👋 I'm **Steve**, your Maddest Offers assistant.\n\n"
                 "I can **find deals** for you, suggest products, compare brands, or answer anything about the offer.\n\n"
                 "Just tell me what you're looking for — like *'find me an LG fridge'* or *'what's the best air fryer deal?'*")

    # ── Goodbye ──────────────────────────────────────────────────────────────
    if has('bye', 'goodbye', 'see you', 'later', 'cya', 'farewell'):
        return r("Goodbye! 👋 Don't miss the Maddest Offers — they won't last forever! 🏀")

    # ── Thanks ───────────────────────────────────────────────────────────────
    if has('thank', 'thanks', 'thx', 'appreciate', 'great', 'awesome', 'perfect', 'cool', 'nice'):
        return r("You're welcome! 😊 Anything else I can help you find?")

    # ── Worst deal ───────────────────────────────────────────────────────────
    if has('worst deal', 'lowest discount', 'least discount', 'smallest discount', 'worst offer', 'minimum discount'):
        rows = top_by('new_discount', 3, 'ASC')
        prods = [dict(r2) for r2 in rows]
        return r("Here are the deals with the **smallest discounts** — still real savings though! 👇", prods)

    # ── Best deal ────────────────────────────────────────────────────────────
    if has('best deal', 'biggest discount', 'most off', 'highest discount', 'top deal',
           'hottest deal', 'best offer', 'greatest discount', 'biggest saving', 'hottest deal'):
        rows = top_by('new_discount', 3, 'DESC')
        prods = [dict(r2) for r2 in rows]
        return r("These are the **hottest deals** right now — biggest discounts in the offer! 🔥", prods)

    # ── Under budget ─────────────────────────────────────────────────────────
    for budget_kw in ['under 20', 'under 30', 'under 50', 'under 100', 'budget', 'affordable', 'cheap']:
        if budget_kw in msg:
            lim_map = {'under 20': 20000, 'under 30': 30000, 'under 50': 50000,
                       'under 100': 100000, 'budget': 30000, 'affordable': 30000, 'cheap': 20000}
            lim = lim_map[budget_kw]
            rows = conn.execute(
                'SELECT * FROM products WHERE new_promo_rrp <= ? ORDER BY new_promo_rrp ASC LIMIT 3', (lim,)
            ).fetchall()
            prods = [dict(r2) for r2 in rows]
            if prods:
                return r(f"Here are deals **under KES {lim:,.0f}** — great value picks! 💰", prods)
            return r(f"No products under KES {lim:,.0f} in the current offer. Try a higher budget!")

    # ── Suggest deals on best 2 brands ───────────────────────────────────────
    if has('best 2 brand', 'top 2 brand', 'two brand', '2 brand', 'best brands', 'top brands') and has('brand', 'brands'):
        brand_rows = conn.execute(
            'SELECT brand, COUNT(*) as c FROM products GROUP BY brand ORDER BY c DESC LIMIT 2'
        ).fetchall()
        prods = []
        brand_names = []
        for br in brand_rows:
            bname = br['brand']
            brand_names.append(bname)
            top = conn.execute(
                'SELECT * FROM products WHERE brand=? ORDER BY new_discount DESC LIMIT 1', (bname,)
            ).fetchall()
            prods.extend([dict(r2) for r2 in top])
        return r(f"Top picks from the **best 2 brands** — **{' & '.join(brand_names)}** 🏆", prods)

    # ── Suggest for a specific brand ─────────────────────────────────────────
    for brand in ['hisense', 'lg', 'von', 'nutricook', 'nutri bullet', 'simfer']:
        if brand in msg and has('suggest', 'recommend', 'good deal', 'best', 'deal', 'top', 'show', 'find'):
            rows = conn.execute(
                'SELECT * FROM products WHERE LOWER(brand) LIKE ? ORDER BY new_discount DESC LIMIT 3',
                (f'%{brand}%',)
            ).fetchall()
            prods = [dict(r2) for r2 in rows]
            if prods:
                return r(f"Here are the top **{brand.title()}** deals on offer right now! 👇", prods)

    # ── Generic suggestion ────────────────────────────────────────────────────
    if has('suggest', 'recommend', 'what should i buy', 'worth buying', 'worth it', 'surprise me'):
        rows = top_by('new_discount', 3, 'DESC')
        prods = [dict(r2) for r2 in rows]
        return r("My **top 3 picks** right now — biggest savings in the entire offer! 🎯", prods)

    # ── Compare brands ────────────────────────────────────────────────────────
    if has('compare', 'vs', 'versus', 'better brand', 'which brand'):
        return r("Great question! Here's a quick brand rundown:\n\n"
                 "• **LG** — Premium build, largest fridge & washer selection\n"
                 "• **Hisense** — Best value, widest range (fridges, TVs, microwaves)\n"
                 "• **Von** — Local favourite, great cookers & washers\n"
                 "• **NutriCook** — Highest discount (47%) on air fryers!\n"
                 "• **Simfer** — Quality cookers\n"
                 "• **Nutri Bullet** — Premium blenders\n\n"
                 "Tell me a brand and I'll show you their best deals!")

    # ── What is this app ──────────────────────────────────────────────────────
    if has('what is this', 'about this', 'about the app', 'purpose', 'explain', 'what is axon'):
        total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        return r(f"This is the **Axon Lattice Maddest Offers Finder** 🏀\n\n"
                 f"We have **{total} products** on offer — from LG, Hisense, Von, NutriCook and more — "
                 f"with discounts **up to 47% off**!\n\nJust ask me to find something or use the search bar above.")

    # ── How to search ─────────────────────────────────────────────────────────
    if has('how to search', 'how do i', 'how to find', 'help', 'guide', 'tutorial', 'how does'):
        return r("Here's how to find your deal: 🔍\n\n"
                 "1. **Tell me what you want** — e.g. *'find me an LG fridge'* and I'll search for you!\n"
                 "2. **Use the search bar** — type a model name or item code\n"
                 "3. **Browse by category** — click the tabs on the home page\n"
                 "4. **Tap any card** to see full price, discount & savings\n\n"
                 "I handle partial names, typos and abbreviations — just type what you know!")

    # ── Analytics ─────────────────────────────────────────────────────────────
    if has('analytics', 'stat', 'report', 'popular', 'most searched', 'trending'):
        return r("Check the **Analytics** page (in the top navbar) to see:\n\n"
                 "Most searched products, category breakdown, daily trends & top discounts!")

    # ── Brands list ───────────────────────────────────────────────────────────
    if has('brand', 'brands', 'manufacturer', 'make', 'who makes', 'which brands'):
        return r("We carry deals from these top brands:\n\n"
                 "• **Hisense** — Fridges, Freezers, Microwaves, TVs, Washers\n"
                 "• **LG** — Fridges, TVs, Washing Machines & Washer-Dryers\n"
                 "• **Von** — Fridges, Washers, Cookers, Air Fryers & more\n"
                 "• **NutriCook** — Air Fryers (up to 47% off!)\n"
                 "• **Nutri Bullet** — Blenders\n"
                 "• **Simfer** — Cookers\n\n"
                 "Tell me a brand and I'll find their best deals! 🎯")

    # ── Categories list ───────────────────────────────────────────────────────
    if has('categor', 'what products', 'what items', 'what appliance', 'what do you have', 'what do you sell'):
        cats = conn.execute(
            'SELECT category, category_icon, COUNT(*) as c FROM products GROUP BY category ORDER BY c DESC'
        ).fetchall()
        lines = '\n'.join(f"{r2['category_icon']} **{r2['category']}** — {r2['c']} items" for r2 in cats)
        return r(f"Here are all categories in the Maddest Offers:\n\n{lines}\n\nAsk me to find something from any category!")

    # ── Discounts ────────────────────────────────────────────────────────────
    if has('discount', 'saving', 'how much off', 'percentage', 'percent'):
        mx = conn.execute('SELECT MAX(new_discount) FROM products').fetchone()[0]
        mn = conn.execute('SELECT MIN(new_discount) FROM products').fetchone()[0]
        return r(f"Maddest Offers discounts range from **{mn:.0f}% to {mx:.0f}% off**! 🎉\n\n"
                 "Want me to show you the biggest discounts right now?")

    # ── Prices ────────────────────────────────────────────────────────────────
    if has('price', 'cost', 'how much', 'ksh', 'kes', 'shilling'):
        lo = conn.execute('SELECT MIN(new_promo_rrp) FROM products').fetchone()[0]
        hi = conn.execute('SELECT MAX(new_promo_rrp) FROM products').fetchone()[0]
        return r(f"Promo prices range from **KES {lo:,.0f}** to **KES {hi:,.0f}**.\n\n"
                 "Tell me what you're looking for and I'll find the exact price for you!")

    # ── Count ─────────────────────────────────────────────────────────────────
    if has('how many', 'total', 'number of product', 'count'):
        count = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        return r(f"There are **{count} products** in the Maddest Offers!\n"
                 "Fridges, TVs, washers, microwaves, air fryers and more from 6 top brands.")

    # ── SEARCH INTENT — detect and search proactively ─────────────────────────
    has_trigger = any(t in msg for t in _SEARCH_TRIGGERS)
    has_product_kw = any(k in msg for k in _CATEGORIES.keys())
    has_brand_kw   = any(b in msg for b in ['hisense', 'lg', 'von', 'nutricook', 'simfer', 'nutribullet'])

    if has_trigger or has_product_kw or has_brand_kw:
        # Check if the query is too vague
        is_vague = any(v in msg for v in _AMBIGUOUS) and not has_product_kw and not has_brand_kw
        if is_vague:
            return r("I'd love to help! Could you be more specific? 🤔\n\n"
                     "For example, are you looking for a:\n"
                     "• **Fridge** or Freezer?\n"
                     "• **Washing Machine** or Washer-Dryer?\n"
                     "• **TV**, Microwave, or Air Fryer?\n"
                     "• **Cooker**, Blender, or Water Dispenser?\n\n"
                     "Just tell me the category and I'll find the best deals!")

        # Try to map to a specific category first
        matched_cat = None
        for kw, cat in _CATEGORIES.items():
            if kw in msg:
                matched_cat = cat
                break

        if matched_cat:
            # Check for brand within same message
            brand_filter = None
            for b in ['hisense', 'lg', 'von', 'nutricook', 'simfer']:
                if b in msg:
                    brand_filter = b
                    break

            if brand_filter:
                search_term = f"{brand_filter} {matched_cat.lower().rstrip('s')}"
            else:
                search_term = matched_cat

            prods = do_search(search_term)
            if prods:
                brand_txt = f" from **{brand_filter.title()}**" if brand_filter else ""
                return r(f"Found **{len(prods)} {matched_cat}**{brand_txt} on the Maddest Offer! Here are the top deals 👇", prods)
            else:
                return r(f"Hmm, I couldn't find any **{matched_cat}** matching your request. 😕\n\n"
                         f"Are you looking for a different brand or type? Try asking:\n"
                         f"• 'Show me all {matched_cat}'\n"
                         f"• 'Best deal on a {matched_cat.rstrip('s')}'")

        # General search intent — extract term and search
        search_term = _extract_search_term(msg)
        if len(search_term) >= 2:
            prods = do_search(search_term)
            if prods:
                return r(f"I found these deals matching **\"{search_term}\"** for you! 🎉", prods)
            else:
                # Ask a follow-up
                return r(f"I searched for **\"{search_term}\"** but couldn't find an exact match. 🤔\n\n"
                         f"Could you tell me more? For example:\n"
                         f"• Which **brand** are you interested in? (LG, Hisense, Von…)\n"
                         f"• Which **category**? (Fridge, TV, Washer, Air Fryer…)\n"
                         f"• Or try searching the **model code** directly in the search bar above.")

    # ── Default / fallback ─────────────────────────────────────────────────────
    return r("Hmm, I'm not sure about that one! 🤔 Here's what I can do:\n\n"
             "• *'Find me an LG fridge'* — I'll search for you\n"
             "• *'What's the best air fryer deal?'* — I'll show top picks\n"
             "• *'Suggest deals under KES 30,000'* — budget deals\n"
             "• *'Compare LG vs Hisense'* — brand comparison\n"
             "• *'Show me the biggest discounts'* — hottest offers\n\n"
             "What are you looking for? 🛍️")


# ─── Register SPA catch-all AFTER all API routes ─────────────────────────────
app.add_url_rule('/', defaults={'path': ''}, view_func=_serve_react_spa)
app.add_url_rule('/<path:path>', view_func=_serve_react_spa)

# ─── Startup ──────────────────────────────────────────────────────────────────

def ensure_db():
    if not os.path.exists(DB_PATH):
        print("[DB] Database not found -- initialising...")
        from init_db import init_db
        init_db()
    load_tfidf()
    print(f"[OK] TF-IDF loaded for {len(_product_list)} products.")


# Always initialise DB + TF-IDF whether running via gunicorn or directly
ensure_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
