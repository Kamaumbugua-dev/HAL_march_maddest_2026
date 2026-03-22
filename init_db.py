"""
init_db.py — Parses the March Madness Excel file and populates SQLite database.
Run this once before starting the app: python init_db.py
"""
import sqlite3
import openpyxl
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'march_madness.db')
EXCEL_PATH = os.path.join(BASE_DIR, 'product pricing.xlsx')


def get_category(item_name: str) -> str:
    name = item_name.upper()

    # ── Freezers ──
    if 'VERTICAL COOLER' in name:
        return 'Freezers'
    if 'CHEST FREEZER' in name or 'FREEZER' in name:
        return 'Freezers'

    # ── Washer-Dryers (check before washing machines) ──
    if any(t in name for t in ['W/DRYER', 'W-DRYER', 'WASHER DRYER', 'WASHER/DRYER', 'WD3', ' WD ']):
        return 'Washer-Dryers'
    # LG-style: "WM FL W-DRYER" or model starts with "WD"
    if ('W-DRYER' in name) or (' WD FL' in name) or ('WD FL' in name):
        return 'Washer-Dryers'

    # ── Washing Machines ──
    if any(t in name for t in ['W/MACHINE', 'WASHING MACHINE', 'W/M ', 'W/M\t', ' WM ', 'WM FL', 'VWM-']):
        return 'Washing Machines'

    # ── Microwaves ──
    if 'MWO' in name or 'MICROWAVE' in name:
        return 'Microwaves'

    # ── TVs ──
    if any(t in name for t in ['ULED', 'QLED', 'OLED', 'FHD TV', '4K TV', 'UHD TV', 'SMART TV', 'LED TV', ' UHD']):
        return 'TVs'
    if name.rstrip().endswith(' TV') or ' TV ' in name:
        return 'TVs'

    # ── Air Fryers ──
    if 'AIR FRYER' in name or 'AIRFRYER' in name or ' AF ' in name:
        return 'Air Fryers'

    # ── Blenders ──
    if 'BLENDER' in name or 'NUTRI BULLET' in name or 'NUTRIBULLET' in name:
        return 'Blenders'

    # ── Cookers ──
    if 'COOKER' in name or 'STOVE' in name or 'HOB' in name:
        return 'Cookers'

    # ── Water Dispensers ──
    if 'DISPENSER' in name:
        return 'Water Dispensers'

    # ── Personal Care ──
    if 'STEAMER' in name or 'HAIR DRYER' in name or 'GARMENT' in name:
        return 'Personal Care'

    # ── Refrigerators ──
    if any(t in name for t in ['REF ', 'FRIDGE', 'REFRIGERATOR', 'TMF', 'SBS', 'BCD-', 'COMBO', 'RC-']):
        return 'Refrigerators'

    return 'Other'


def get_brand(item_name: str) -> str:
    name = item_name.upper()
    known_brands = [
        ('HISENSE', 'Hisense'),
        ('LG', 'LG'),
        ('SAMSUNG', 'Samsung'),
        ('VON', 'Von'),
        ('NUTRICOOK', 'NutriCook'),
        ('NUTRI BULLET', 'Nutri Bullet'),
        ('NUTRIBULLET', 'Nutri Bullet'),
        ('SIMFER', 'Simfer'),
        ('RAMTONS', 'Ramtons'),
        ('NASCO', 'Nasco'),
    ]
    for key, label in known_brands:
        if key in name:
            return label
    return 'Other'


def parse_price(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = re.sub(r'[^\d.]', '', str(val))
    return float(cleaned) if cleaned else 0.0


def parse_discount(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, float):
        return round(val * 100, 1) if val < 1 else round(val, 1)
    s = str(val).replace('%', '').strip()
    try:
        d = float(s)
        return round(d * 100, 1) if d < 1 else round(d, 1)
    except ValueError:
        return 0.0


CATEGORY_ICONS = {
    'Refrigerators':   '🧊',
    'Freezers':        '❄️',
    'Washing Machines':'🌊',
    'Washer-Dryers':   '💨',
    'Microwaves':      '📡',
    'TVs':             '📺',
    'Air Fryers':      '🍟',
    'Blenders':        '🌀',
    'Cookers':         '🔥',
    'Water Dispensers':'💧',
    'Personal Care':   '💇',
    'Other':           '📦',
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('DROP TABLE IF EXISTS products')
    c.execute('DROP TABLE IF EXISTS search_logs')

    c.execute('''
        CREATE TABLE products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code     TEXT,
            item_name     TEXT,
            sale_rrp      REAL,
            new_promo_rrp REAL,
            new_discount  REAL,
            category      TEXT,
            category_icon TEXT,
            brand         TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE search_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            query         TEXT,
            category      TEXT,
            results_count INTEGER,
            timestamp     TEXT
        )
    ''')

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    rows_inserted = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[1]:
            continue
        item_code, item_name, sale_rrp, new_promo_rrp, new_discount = (row + (None, None, None, None, None))[:5]
        item_code     = str(item_code).strip() if item_code else ''
        item_name     = str(item_name).strip()
        sale_rrp      = parse_price(sale_rrp)
        new_promo_rrp = parse_price(new_promo_rrp)
        new_discount  = parse_discount(new_discount)
        category      = get_category(item_name)
        icon          = CATEGORY_ICONS.get(category, '📦')
        brand         = get_brand(item_name)

        c.execute('''
            INSERT INTO products
                (item_code, item_name, sale_rrp, new_promo_rrp, new_discount, category, category_icon, brand)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_code, item_name, sale_rrp, new_promo_rrp, new_discount, category, icon, brand))
        rows_inserted += 1

    conn.commit()
    conn.close()
    print(f"[OK] Database initialised with {rows_inserted} products across multiple categories.")
    print(f"[DB] Database saved to: {DB_PATH}")


if __name__ == '__main__':
    init_db()
