"""
api/index.py — Vercel serverless entry point for the Flask app.
Copies the pre-built SQLite DB to /tmp (writable) on cold start.
"""
import sys
import os
import shutil

# Make the root package importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Copy DB to /tmp so writes (search logs) work on Vercel's read-only filesystem
_src_db = os.path.join(ROOT, 'march_madness.db')
_tmp_db = '/tmp/march_madness.db'
if os.path.exists(_src_db) and not os.path.exists(_tmp_db):
    shutil.copy2(_src_db, _tmp_db)

# Tell app.py to use the writable copy
os.environ.setdefault('DB_PATH', _tmp_db)

from app import app  # noqa: E402 — must come after env var is set
