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
    resp    = _steve_response(message.lower(), conn)
    conn.close()
    return jsonify({'response': resp})


# ─── Steve Bot logic ──────────────────────────────────────────────────────────

def _steve_response(msg: str, conn) -> str:  # noqa: C901
    """Natural-language intent matching for Steve bot."""

    # ── helpers ──────────────────────────────────────────────────────────────
    def has(*phrases): return any(p in msg for p in phrases)
    def top_by(col, n=3, order='DESC'):
        return conn.execute(
            f'SELECT item_name, brand, new_discount, new_promo_rrp, sale_rrp '
            f'FROM products ORDER BY {col} {order} LIMIT ?', (n,)
        ).fetchall()

    # ── Greetings ────────────────────────────────────────────────────────────
    if has('hi', 'hello', 'hey', 'howdy', 'sup', 'hola', 'good morning', 'good afternoon', 'good evening'):
        return ("Hey! 👋 I'm **Steve**, your Maddest Offers assistant at Axon Lattice.\n"
                "I can help you find deals, suggest products, or answer anything about the offer. What's up?")

    # ── Goodbye ──────────────────────────────────────────────────────────────
    if has('bye', 'goodbye', 'see you', 'later', 'cya', 'farewell'):
        return "Goodbye! 👋 Don't miss the Maddest Offers — they won't last forever! 🏀"

    # ── Thanks ───────────────────────────────────────────────────────────────
    if has('thank', 'thanks', 'thx', 'appreciate', 'great', 'awesome', 'perfect', 'cool', 'nice'):
        return "You're welcome! 😊 Anything else I can help with?"

    # ── Worst deal (natural question!) ───────────────────────────────────────
    if has('worst deal', 'lowest discount', 'least discount', 'smallest discount', 'worst offer', 'least off', 'minimum discount'):
        rows = top_by('new_discount', 3, 'ASC')
        lines = '\n'.join(
            f"• **{r['item_name']}** — {r['new_discount']:.0f}% off → KES {r['new_promo_rrp']:,.0f}"
            for r in rows
        )
        return (f"The deals with the smallest discount are:\n\n{lines}\n\n"
                "Even these have solid savings — but for the biggest bang, check out the air fryers!")

    # ── Best deal ────────────────────────────────────────────────────────────
    if has('best deal', 'biggest discount', 'most off', 'highest discount', 'top deal',
           'hottest deal', 'cheapest', 'best offer', 'greatest discount', 'biggest saving'):
        rows = top_by('new_discount', 3, 'DESC')
        lines = '\n'.join(
            f"• **{r['item_name']}** — **{r['new_discount']:.0f}% OFF** → KES {r['new_promo_rrp']:,.0f}"
            for r in rows
        )
        return f"The hottest deals by discount are:\n\n{lines}\n\nSearch any of these above to see full details!"

    # ── Suggest deal for a specific brand ────────────────────────────────────
    for brand in ['hisense', 'lg', 'von', 'nutricook', 'nutri bullet', 'simfer']:
        if brand in msg and has('suggest', 'recommend', 'good deal', 'best', 'deal', 'top', 'show me'):
            rows = conn.execute(
                'SELECT item_name, new_discount, new_promo_rrp, category FROM products '
                'WHERE LOWER(brand) LIKE ? ORDER BY new_discount DESC LIMIT 3',
                (f'%{brand}%',)
            ).fetchall()
            if rows:
                lines = '\n'.join(
                    f"• **{r['item_name']}** — {r['new_discount']:.0f}% off → KES {r['new_promo_rrp']:,.0f}"
                    for r in rows
                )
                return f"Top {brand.title()} deals on offer:\n\n{lines}"

    # ── Suggest deals on best 2 brands ───────────────────────────────────────
    if has('best 2 brand', 'top 2 brand', 'two brand', '2 brand', 'best brands', 'top brands',
           'suggest', 'recommend') and has('brand', 'brands'):
        # Count products per brand (proxy for "best" brand)
        brand_rows = conn.execute(
            'SELECT brand, COUNT(*) as c FROM products GROUP BY brand ORDER BY c DESC LIMIT 2'
        ).fetchall()
        result = []
        for br in brand_rows:
            bname = br['brand']
            top = conn.execute(
                'SELECT item_name, new_discount, new_promo_rrp FROM products '
                'WHERE brand = ? ORDER BY new_discount DESC LIMIT 2',
                (bname,)
            ).fetchall()
            result.append(f"**{bname}** top picks:")
            for r in top:
                result.append(f"  • {r['item_name']} — {r['new_discount']:.0f}% off → KES {r['new_promo_rrp']:,.0f}")
        return '\n'.join(result) if result else "Let me find those for you — try searching on the home page!"

    # ── Suggest (generic) ─────────────────────────────────────────────────────
    if has('suggest', 'recommend', 'what should i buy', 'good deal', 'worth buying', 'worth it'):
        rows = top_by('new_discount', 3, 'DESC')
        lines = '\n'.join(
            f"• **{r['item_name']}** ({r['brand']}) — {r['new_discount']:.0f}% off → KES {r['new_promo_rrp']:,.0f}"
            for r in rows
        )
        return (f"Here are my top 3 picks right now:\n\n{lines}\n\n"
                "All three have the biggest discounts in the offer. Tap any card to see full details!")

    # ── Compare brands ────────────────────────────────────────────────────────
    if has('compare', 'vs', 'versus', 'better brand', 'which brand'):
        return ("Great question! Here's a quick brand rundown:\n\n"
                "• **LG** — Premium build, largest fridge selection, great TVs\n"
                "• **Hisense** — Best value, widest range (fridges + TVs + microwaves)\n"
                "• **Von** — Local favourite, big cooker & washer range\n"
                "• **NutriCook** — Highest discount (47%) air fryers!\n\n"
                "Search a brand name to see all their deals.")

    # ── Under budget ─────────────────────────────────────────────────────────
    for budget_kw in ['under 20', 'under 30', 'under 50', 'under 100', 'budget', 'affordable', 'cheap']:
        if budget_kw in msg:
            limit_map = {'under 20': 20000, 'under 30': 30000, 'under 50': 50000,
                         'under 100': 100000, 'budget': 30000, 'affordable': 30000, 'cheap': 20000}
            lim = limit_map[budget_kw]
            rows = conn.execute(
                'SELECT item_name, new_promo_rrp, new_discount FROM products '
                'WHERE new_promo_rrp <= ? ORDER BY new_promo_rrp ASC LIMIT 5', (lim,)
            ).fetchall()
            if rows:
                lines = '\n'.join(
                    f"• **{r['item_name']}** — KES {r['new_promo_rrp']:,.0f} ({r['new_discount']:.0f}% off)"
                    for r in rows
                )
                return f"Products under KES {lim:,.0f}:\n\n{lines}"
            return f"No products under KES {lim:,.0f} in the current offer."

    # ── What is this app ──────────────────────────────────────────────────────
    if has('what is this', 'what does this', 'about this', 'about the app', 'purpose', 'explain', 'what is axon'):
        total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        return (f"This is the **Axon Lattice Maddest Offers Finder** 🏀\n\n"
                f"We have **{total} products** from top brands like LG, Hisense, Von, NutriCook and more — "
                f"with discounts up to **47% off**! Type a model name or browse by category to check if your item is on offer.")

    # ── How to search ─────────────────────────────────────────────────────────
    if has('how to search', 'how do i', 'how to find', 'search tip', 'help', 'guide', 'tutorial'):
        return ("Here's how to find your deal: 🔍\n\n"
                "1. **Type a model name** — e.g. 'LG fridge', 'GL-C652', or 'air fryer'\n"
                "2. **Click Search** or press Enter\n"
                "3. **Browse by category** — use the tabs below the header\n"
                "4. **Tap any card** to see full price, discount & savings details\n\n"
                "The search handles partial names and typos — just type what you know!")

    # ── Brands ───────────────────────────────────────────────────────────────
    if has('brand', 'brands', 'manufacturer', 'make', 'who makes', 'which brands'):
        return ("We carry deals from these top brands:\n\n"
                "• **Hisense** — Fridges, Freezers, Microwaves, TVs, Washers\n"
                "• **LG** — Fridges, TVs, Washing Machines & Washer-Dryers\n"
                "• **Von** — Fridges, Washers, Cookers, Air Fryers & more\n"
                "• **NutriCook** — Air Fryers (up to 47% off!)\n"
                "• **Nutri Bullet** — Blenders\n"
                "• **Simfer** — Cookers")

    # ── Categories ───────────────────────────────────────────────────────────
    if has('categor', 'type', 'what products', 'what items', 'what appliance', 'what do you have', 'available'):
        cats = conn.execute(
            'SELECT category, category_icon, COUNT(*) as c FROM products GROUP BY category ORDER BY c DESC'
        ).fetchall()
        lines = '\n'.join(f"{r['category_icon']} **{r['category']}** — {r['c']} items" for r in cats)
        return f"Here are all categories in the Maddest Offers:\n\n{lines}\n\nClick any tab in the navbar to browse!"

    # ── Fridges ───────────────────────────────────────────────────────────────
    if has('fridge', 'refrigerator', 'ref '):
        count = conn.execute("SELECT COUNT(*) FROM products WHERE category='Refrigerators'").fetchone()[0]
        return (f"We have **{count} refrigerators** on offer from LG, Hisense, and Von! "
                "Discounts range from 26% to 36%. Search 'fridge' or click **Refrigerators** in the navbar.")

    # ── TVs ──────────────────────────────────────────────────────────────────
    if has(' tv', 'television', 'smart tv', 'screen', 'display'):
        count = conn.execute("SELECT COUNT(*) FROM products WHERE category='TVs'").fetchone()[0]
        return (f"We have **{count} Smart TVs** on offer — 4K ULED and FHD models. "
                "Search 'TV' or click **TVs** in the navbar!")

    # ── Washing ───────────────────────────────────────────────────────────────
    if has('wash', 'laundry', 'washer'):
        wm = conn.execute("SELECT COUNT(*) FROM products WHERE category='Washing Machines'").fetchone()[0]
        wd = conn.execute("SELECT COUNT(*) FROM products WHERE category='Washer-Dryers'").fetchone()[0]
        return (f"We have **{wm} washing machines** and **{wd} washer-dryer combos** on offer! "
                "Great savings on LG, Hisense, and Von models.")

    # ── Microwave ─────────────────────────────────────────────────────────────
    if has('microwave', 'mwo'):
        count = conn.execute("SELECT COUNT(*) FROM products WHERE category='Microwaves'").fetchone()[0]
        return (f"We have **{count} microwaves** on offer from Hisense — solo and grill models. "
                "Savings of up to 32%! Search 'microwave' to see them.")

    # ── Air Fryer ─────────────────────────────────────────────────────────────
    if has('air fryer', 'fryer', 'frying'):
        rows = conn.execute(
            "SELECT item_name, new_discount, new_promo_rrp FROM products "
            "WHERE category='Air Fryers' ORDER BY new_discount DESC"
        ).fetchall()
        lines = '\n'.join(f"• {r['item_name']} — {r['new_discount']:.0f}% off → KES {r['new_promo_rrp']:,.0f}" for r in rows)
        return f"Air fryers on offer (up to 47% off!):\n\n{lines}"

    # ── Water Dispenser ───────────────────────────────────────────────────────
    if has('water', 'dispenser', 'water dispenser'):
        rows = conn.execute(
            "SELECT item_name, new_discount, new_promo_rrp FROM products WHERE category='Water Dispensers'"
        ).fetchall()
        if rows:
            lines = '\n'.join(f"• {r['item_name']} — {r['new_discount']:.0f}% off → KES {r['new_promo_rrp']:,.0f}" for r in rows)
            return f"Water dispensers on offer:\n\n{lines}\n\nGreat savings on Von floor-standing dispensers!"

    # ── Discounts ────────────────────────────────────────────────────────────
    if has('discount', 'saving', 'how much off', 'percentage', 'percent'):
        mx = conn.execute('SELECT MAX(new_discount) FROM products').fetchone()[0]
        mn = conn.execute('SELECT MIN(new_discount) FROM products').fetchone()[0]
        return (f"Maddest Offers discounts range from **{mn:.0f}% to {mx:.0f}% off**! 🎉\n\n"
                "Check the **Analytics** page to see the top deals by discount.")

    # ── Prices ────────────────────────────────────────────────────────────────
    if has('price', 'cost', 'how much', 'ksh', 'kes', 'shilling'):
        lo = conn.execute('SELECT MIN(new_promo_rrp) FROM products').fetchone()[0]
        hi = conn.execute('SELECT MAX(new_promo_rrp) FROM products').fetchone()[0]
        return (f"Promo prices range from **KES {lo:,.0f}** to **KES {hi:,.0f}**.\n\n"
                "Search a specific model to see its exact promo price and savings!")

    # ── Count ─────────────────────────────────────────────────────────────────
    if has('how many', 'total', 'number of product', 'count'):
        count = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        return (f"There are **{count} products** in the Maddest Offers! "
                "Fridges, TVs, washers, microwaves, air fryers and more from 6 top brands.")

    # ── Analytics ─────────────────────────────────────────────────────────────
    if has('analytics', 'stat', 'report', 'popular', 'most searched', 'trending'):
        return ("Check the **Analytics** page (navbar at the top) to see:\n\n"
                "Most searched products, category breakdown, daily trends & top discounts!")

    # ── Default ──────────────────────────────────────────────────────────────
    return ("Hmm, I'm not sure about that! 🤔 Try asking:\n\n"
            "• 'What's the best deal?'\n"
            "• 'What's the worst deal?'\n"
            "• 'Suggest a good deal on LG'\n"
            "• 'Suggest deals on the best 2 brands'\n"
            "• 'Products under 30000'\n"
            "• 'What brands are available?'\n"
            "• 'How many air fryers are on offer?'\n\n"
            "Or type a model name in the search bar to check the offer!")


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
