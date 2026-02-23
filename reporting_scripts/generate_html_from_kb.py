#!/usr/bin/env python3
"""
SOLVE-IT Knowledge Base HTML Generator
=======================================
Fetches data from the SOLVE-IT GitHub repository and generates a
MITRE ATT&CK-style static HTML knowledge base viewer.

Usage:
    python generate_solveit.py                         # Fetch from GitHub
    python generate_solveit.py --local ./solve-it      # Use local clone
    python generate_solveit.py --output viewer.html    # Set output file
    python generate_solveit.py --no-verify-ssl         # Skip SSL cert check
    python generate_solveit.py --help

Requirements:
    Python 3.8+ (no external dependencies for fetching; optionally 'requests')
"""

import json
import os
import sys
import re
import ssl
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# GitHub endpoints
# ─────────────────────────────────────────────────────────────────────────────
GITHUB_RAW_BASE  = "https://raw.githubusercontent.com/SOLVE-IT-DF/solve-it/main"
GITHUB_API_BASE  = "https://api.github.com/repos/SOLVE-IT-DF/solve-it/contents"

# ─────────────────────────────────────────────────────────────────────────────
# Network helpers
# ─────────────────────────────────────────────────────────────────────────────

# Set to an unverified SSL context when --no-verify-ssl is passed
_ssl_context: ssl.SSLContext | None = None


def fetch_url(url: str, timeout: int = 15) -> str | None:
    """Return decoded text content of a URL, or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SOLVE-IT-Generator/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        print(f"  [warn] {url}: {exc}", file=sys.stderr)
        return None


def fetch_json(url: str) -> dict | list | None:
    text = fetch_url(url)
    if text:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            print(f"  [warn] JSON error {url}: {exc}", file=sys.stderr)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_from_github() -> dict:
    """Fetch all SOLVE-IT data from GitHub."""
    print("Connecting to GitHub …")
    db: dict = {"techniques": [], "weaknesses": [], "mitigations": [], "objectives": []}

    for category in ("techniques", "weaknesses", "mitigations"):
        print(f"  Fetching {category} listing …")
        listing = fetch_json(f"{GITHUB_API_BASE}/data/{category}")
        if not listing:
            sys.exit(f"ERROR: Could not list data/{category} from GitHub. "
                     "Check network access or use --local.")
        files = [f for f in listing if f["name"].endswith(".json")]
        print(f"  Found {len(files)} {category} files.")
        for f in files:
            obj = fetch_json(f"{GITHUB_RAW_BASE}/data/{category}/{f['name']}")
            if obj:
                db[category].append(obj)

    # solve-it.json holds the canonical objectives / tactic ordering
    print("  Fetching objectives (solve-it.json) …")
    cfg = fetch_json(f"{GITHUB_RAW_BASE}/data/solve-it.json")
    if cfg:
        # solve-it.json may be a bare list or a dict wrapping objectives
        db["objectives"] = cfg if isinstance(cfg, list) else cfg.get("objectives", [])
    else:
        print("  [warn] Could not fetch solve-it.json – objectives will be empty.")

    print(f"  Loaded: {len(db['techniques'])} techniques, "
          f"{len(db['weaknesses'])} weaknesses, {len(db['mitigations'])} mitigations, "
          f"{len(db['objectives'])} objectives.")
    return db


def load_from_local(repo_path: str) -> dict:
    """Read SOLVE-IT data from a local clone of the repository."""
    root = Path(repo_path)
    if not root.exists():
        sys.exit(f"ERROR: Path does not exist: {repo_path}")

    db: dict = {"techniques": [], "weaknesses": [], "mitigations": [], "objectives": []}

    for category in ("techniques", "weaknesses", "mitigations"):
        folder = root / "data" / category
        if not folder.exists():
            print(f"  [warn] {folder} not found – skipping.", file=sys.stderr)
            continue
        files = list(folder.glob("*.json"))
        print(f"  Loading {len(files)} {category} from {folder} …")
        for fp in sorted(files):
            try:
                db[category].append(json.loads(fp.read_text(encoding="utf-8")))
            except Exception as exc:
                print(f"  [warn] {fp}: {exc}", file=sys.stderr)

    cfg_path = root / "data" / "solve-it.json"
    if not cfg_path.exists():
        cfg_path = root / "solve-it.json"  # fallback for older layouts
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            # solve-it.json may be a bare list of objectives, or a dict wrapping them
            db["objectives"] = cfg if isinstance(cfg, list) else cfg.get("objectives", [])
        except Exception as exc:
            print(f"  [warn] solve-it.json: {exc}", file=sys.stderr)

    print(f"  Loaded: {len(db['techniques'])} techniques, "
          f"{len(db['weaknesses'])} weaknesses, {len(db['mitigations'])} mitigations, "
          f"{len(db['objectives'])} objectives.")
    return db


# ─────────────────────────────────────────────────────────────────────────────
# Pre-processing / cross-referencing
# ─────────────────────────────────────────────────────────────────────────────

WEAKNESS_CATS = ["INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT"]
CAT_LABELS = {
    "INCOMP":   "Incomplete (INCOMP)",
    "INAC-EX":  "Inaccurate Extraction (INAC-EX)",
    "INAC-AS":  "Inaccurate Association (INAC-AS)",
    "INAC-ALT": "Inaccurate Alteration (INAC-ALT)",
    "INAC-COR": "Inaccurate Corruption (INAC-COR)",
    "MISINT":   "Misinterpretation (MISINT)",
}


def build_indices(db: dict) -> dict:
    """Build lookup dicts and reverse maps."""
    idx: dict = {}
    idx["techniques"]  = {t["id"]: t for t in db["techniques"]}
    idx["weaknesses"]  = {w["id"]: w for w in db["weaknesses"]}
    idx["mitigations"] = {m["id"]: m for m in db["mitigations"]}

    # weakness → list[technique_id]
    w2t: dict = {}
    for t in db["techniques"]:
        for wid in (t.get("weaknesses") or []):
            w2t.setdefault(wid, []).append(t["id"])
    idx["weakness_to_techniques"] = w2t

    # mitigation → list[weakness_id]
    m2w: dict = {}
    for w in db["weaknesses"]:
        for mid in (w.get("mitigations") or []):
            m2w.setdefault(mid, []).append(w["id"])
    idx["mitigation_to_weaknesses"] = m2w

    # Compute status for each technique if not already present
    for t in db["techniques"]:
        if "status" not in t:
            has_desc = bool((t.get("description") or "").strip())
            num_weak = len(t.get("weaknesses") or [])
            num_mit  = sum(
                len(idx["weaknesses"][wid].get("mitigations") or [])
                for wid in (t.get("weaknesses") or [])
                if wid in idx["weaknesses"]
            )
            if num_weak == 0:
                t["status"] = "placeholder"
            elif not has_desc or num_mit == 0:
                t["status"] = "partial"
            else:
                t["status"] = "complete"

    return idx


# ─────────────────────────────────────────────────────────────────────────────
# HTML generation helpers
# ─────────────────────────────────────────────────────────────────────────────

def esc(text: str) -> str:
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def technique_status_class(status: str) -> str:
    return {"complete": "status-green", "partial": "status-yellow",
            "placeholder": "status-red"}.get(status, "status-red")


def weakness_cats(w: dict) -> list[str]:
    return [c for c in WEAKNESS_CATS if w.get(c, "").strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Main HTML generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_html(db: dict, idx: dict) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Sanitise </script> sequences to prevent early tag closure when embedded in HTML
    data_json    = json.dumps(db, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    idx_json     = json.dumps({
        "weakness_to_techniques":  idx["weakness_to_techniques"],
        "mitigation_to_weaknesses": idx["mitigation_to_weaknesses"],
    }, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")

    n_t = len(db["techniques"])
    n_w = len(db["weaknesses"])
    n_m = len(db["mitigations"])
    n_o = len(db["objectives"])

    # Status counts
    statuses = [t.get("status", "placeholder") for t in db["techniques"]]
    # Unique non-trivial references across all item types
    _all_refs: set = set()
    for _items in (db["techniques"], db["weaknesses"], db["mitigations"]):
        for _item in _items:
            for _r in (_item.get("references") or []):
                if _r and _r.strip() and _r.strip().lower() != "todo":
                    _all_refs.add(_r.strip())
    n_r = len(_all_refs)

    n_complete    = statuses.count("complete")
    n_partial     = statuses.count("partial")
    n_placeholder = statuses.count("placeholder")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SOLVE-IT Knowledge Base</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">
<style>
/* ── Design tokens ─────────────────────────────────────────── */
:root {{
  --navy:      #1b2a4a;
  --navy-dark: #0e1a30;
  --navy-mid:  #253661;
  --blue:      #2256a6;
  --blue-lt:   #3a71cc;
  --blue-pale: #e8f0fa;
  --white:     #ffffff;
  --gray-50:   #f8f9fb;
  --gray-100:  #eef0f4;
  --gray-200:  #dde1ea;
  --gray-300:  #c5cad6;
  --gray-500:  #7a8299;
  --gray-700:  #3f4559;
  --gray-900:  #1a1d28;

  --red:        #c0392b;
  --red-bg:     #fdf3f2;
  --red-border: #f0c8c4;
  --yellow:     #b7741a;
  --yellow-bg:  #fdf8ee;
  --yellow-border: #f0d8a0;
  --green:      #1a7a4a;
  --green-bg:   #f0faf5;
  --green-border:#a8dfc0;

  --shadow-sm: 0 1px 3px rgba(0,0,0,.08);
  --shadow-md: 0 4px 16px rgba(0,0,0,.10);
  --shadow-lg: 0 8px 32px rgba(0,0,0,.15);

  --font-body: 'Source Sans 3', system-ui, sans-serif;
  --font-mono: 'Source Code Pro', monospace;
  --transition: 0.18s ease;
}}

/* ── Reset ─────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 15px; scroll-behavior: smooth; }}
body {{
  font-family: var(--font-body);
  background: var(--gray-50);
  color: var(--gray-900);
  min-height: 100vh;
}}
a {{ color: var(--blue); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
button {{ font-family: inherit; cursor: pointer; }}

/* ── Top nav ───────────────────────────────────────────────── */
.topnav {{
  background: var(--navy);
  color: var(--white);
  display: flex;
  align-items: center;
  gap: 0;
  height: 52px;
  position: sticky;
  top: 0;
  z-index: 500;
  box-shadow: 0 2px 8px rgba(0,0,0,.25);
}}
.topnav-brand {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  height: 100%;
  background: var(--navy-dark);
  border-right: 1px solid rgba(255,255,255,.08);
  text-decoration: none;
  color: inherit;
  flex-shrink: 0;
}}
.topnav-brand svg {{ opacity: .85; }}
.topnav-brand-name {{
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: .02em;
  color: #fff;
}}
.topnav-brand-name span {{ color: #6eb4ff; }}

.topnav-tabs {{
  display: flex;
  height: 100%;
  flex: 1;
}}
.topnav-tab {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  height: 100%;
  color: rgba(255,255,255,.65);
  font-size: .875rem;
  font-weight: 600;
  letter-spacing: .02em;
  border: none;
  background: transparent;
  border-bottom: 3px solid transparent;
  transition: var(--transition);
  text-transform: uppercase;
  cursor: pointer;
  white-space: nowrap;
}}
.topnav-tab:hover {{ color: #fff; background: rgba(255,255,255,.06); }}
.topnav-tab.active {{ color: #fff; border-bottom-color: #6eb4ff; }}
.topnav-tab.active.tab-t {{ border-bottom-color: #6eb4ff; }}
.topnav-tab.active.tab-w {{ border-bottom-color: #f4a839; }}
.topnav-tab.active.tab-m {{ border-bottom-color: #4cba7c; }}

.tab-badge {{
  font-family: var(--font-mono);
  font-size: .7rem;
  background: rgba(255,255,255,.15);
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 400;
}}

.topnav-search {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  margin-left: auto;
}}
.search-wrap {{
  position: relative;
  display: flex;
  align-items: center;
}}
.search-input {{
  background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 6px;
  padding: 5px 12px 5px 32px;
  color: #fff;
  font-family: var(--font-body);
  font-size: .875rem;
  width: 220px;
  transition: var(--transition);
}}
.search-input::placeholder {{ color: rgba(255,255,255,.4); }}
.search-input:focus {{
  outline: none;
  background: rgba(255,255,255,.15);
  border-color: rgba(255,255,255,.4);
  width: 280px;
}}
.search-icon {{
  position: absolute;
  left: 9px;
  color: rgba(255,255,255,.45);
  pointer-events: none;
}}
.search-clear {{
  position: absolute;
  right: 8px;
  color: rgba(255,255,255,.45);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  display: none;
  line-height: 1;
}}
.search-clear.visible {{ display: block; }}
.search-clear:hover {{ color: #fff; }}

/* ── Filter bar ────────────────────────────────────────────── */
.filterbar {{
  background: var(--white);
  border-bottom: 1px solid var(--gray-200);
  padding: 8px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  min-height: 48px;
}}
.filterbar-label {{
  font-size: .75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--gray-500);
}}
.filter-chip {{
  padding: 4px 12px;
  border: 1px solid var(--gray-300);
  border-radius: 20px;
  font-size: .8rem;
  font-weight: 600;
  background: var(--white);
  color: var(--gray-700);
  transition: var(--transition);
}}
.filter-chip:hover {{ background: var(--gray-100); border-color: var(--gray-400, #aaa); }}
.filter-chip.active {{
  background: var(--navy);
  color: #fff;
  border-color: var(--navy);
}}
.filter-chip.active.chip-red    {{ background: var(--red);    border-color: var(--red); }}
.filter-chip.active.chip-yellow {{ background: var(--yellow); border-color: var(--yellow); }}
.filter-chip.active.chip-green  {{ background: var(--green);  border-color: var(--green); }}

.filterbar-sep {{ width: 1px; height: 20px; background: var(--gray-200); }}
.filterbar-stats {{
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}}
.stat-pill {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: .8rem;
  color: var(--gray-500);
}}
.stat-dot {{
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.stat-dot.red    {{ background: var(--red); }}
.stat-dot.yellow {{ background: var(--yellow); }}
.stat-dot.green  {{ background: var(--green); }}
.stat-num {{ font-weight: 700; font-family: var(--font-mono); color: var(--gray-900); }}

.result-count {{
  font-size: .8rem;
  color: var(--gray-500);
  font-family: var(--font-mono);
}}

/* ── Page layout ───────────────────────────────────────────── */
.page-layout {{
  display: flex;
  height: calc(100vh - 100px);
  overflow: hidden;
}}
.main-area {{
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 20px;
  transition: margin-right .25s ease;
}}
.main-area.shifted {{ margin-right: 520px; }}

/* ── Stats banner ─────────────────────────────────────────── */
.stats-banner {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
  max-width: 900px;
}}
.stat-card {{
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: var(--shadow-sm);
}}
.stat-card-num {{
  font-size: 1.75rem;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--navy);
  line-height: 1;
}}
.stat-card-label {{
  font-size: .75rem;
  color: var(--gray-500);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .05em;
}}
.stat-card.red    {{ border-top: 3px solid var(--red); }}
.stat-card.yellow {{ border-top: 3px solid var(--yellow); }}
.stat-card.green  {{ border-top: 3px solid var(--green); }}
.stat-card.blue   {{ border-top: 3px solid var(--blue); }}

/* ── Matrix (ATT&CK style) ─────────────────────────────────── */
.matrix-container {{
  overflow-x: auto;
  padding-bottom: 16px;
}}
.matrix {{
  display: flex;
  gap: 0;
  min-width: fit-content;
  align-items: flex-start;
  border: 1px solid var(--gray-300);
  border-radius: 4px;
  overflow: hidden;
}}

@keyframes fadeUp {{
  from {{ opacity:0; transform:translateY(6px); }}
  to   {{ opacity:1; transform:translateY(0);   }}
}}

.tactic-col {{
  display: flex;
  flex-direction: column;
  min-width: 140px;
  flex: 1;
  flex-shrink: 0;
  border-right: 1px solid var(--gray-300);
  animation: fadeUp .25s ease forwards;
  opacity: 0;
}}
.tactic-col:last-child {{ border-right: none; }}

/* Sticky tactic header */
.tactic-header {{
  background: var(--navy);
  color: #fff;
  padding: 9px 10px 8px;
  font-size: .7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  text-align: center;
  line-height: 1.3;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: sticky;
  top: 0;
  z-index: 5;
  cursor: default;
}}
.tactic-header .tcount {{
  display: block;
  font-size: .62rem;
  font-weight: 400;
  opacity: .6;
  margin-top: 4px;
  text-transform: none;
  letter-spacing: 0;
}}
.tactic-cells {{
  display: flex;
  flex-direction: column;
  background: var(--white);
  flex: 1;
  min-height: 10px;
}}

/* Compact ATT&CK technique cell */
.tech-cell {{
  padding: 5px 8px;
  background: var(--white);
  border-bottom: 1px solid var(--gray-100);
  border-left: 3px solid transparent;
  cursor: pointer;
  transition: background .1s;
  position: relative;
}}
.tech-cell:last-child {{ border-bottom: none; }}
.tech-cell:hover {{ background: var(--blue-pale); }}
.tech-cell.selected {{ background: var(--blue-pale); border-left-color: var(--blue); }}

.tech-cell.status-red    {{ border-left-color: var(--red); }}
.tech-cell.status-yellow {{ border-left-color: var(--yellow); }}
.tech-cell.status-green  {{ border-left-color: var(--green); }}
.tech-cell.selected.status-red    {{ background:#fff4f3; }}
.tech-cell.selected.status-yellow {{ background:#fffbf0; }}
.tech-cell.selected.status-green  {{ background:#f0faf5; }}

.tech-cell-id {{
  font-family: var(--font-mono);
  font-size: .6rem;
  color: var(--gray-500);
  margin-bottom: 1px;
}}
.tech-cell-name {{
  font-size: .72rem;
  font-weight: 500;
  color: var(--blue);
  line-height: 1.3;
}}
.tech-cell:hover .tech-cell-name {{ text-decoration: underline; }}
.tech-cell-sub {{
  font-size: .62rem;
  color: var(--gray-500);
  margin-top: 2px;
}}

/* ── Weakness/Mitigation table view ───────────────────────── */
.table-section {{ margin-bottom: 24px; }}
.table-section-header {{
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 0 0 8px;
  border-bottom: 2px solid var(--navy);
  margin-bottom: 8px;
}}
.table-section-title {{
  font-size: 1rem;
  font-weight: 700;
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: .06em;
}}
.table-section-count {{
  font-family: var(--font-mono);
  font-size: .8rem;
  color: var(--gray-500);
}}
.attck-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: .85rem;
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}}
.attck-table th {{
  background: var(--navy);
  color: rgba(255,255,255,.9);
  font-size: .72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  padding: 10px 12px;
  text-align: left;
  white-space: nowrap;
}}
.attck-table th.sortable {{
  cursor: pointer;
  user-select: none;
  position: relative;
  padding-right: 22px;
}}
.attck-table th.sortable:hover {{ background: var(--navy-mid); }}
.sort-arrow {{
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: .6rem;
  opacity: .4;
}}
.attck-table th.sortable.active .sort-arrow {{ opacity: 1; }}
.attck-table td {{
  padding: 9px 12px;
  border-bottom: 1px solid var(--gray-100);
  vertical-align: top;
}}
.attck-table tr:last-child td {{ border-bottom: none; }}
.attck-table tbody tr {{ transition: background var(--transition); cursor: pointer; }}
.attck-table tbody tr:hover {{ background: var(--blue-pale); }}
.attck-table tbody tr.selected {{ background: var(--blue-pale); }}

.tid  {{ font-family: var(--font-mono); color: var(--blue); font-weight: 600; white-space: nowrap; font-size: .8rem; }}
.wid  {{ font-family: var(--font-mono); color: #7b3f00; font-weight: 600; white-space: nowrap; font-size: .8rem; }}
.mid  {{ font-family: var(--font-mono); color: var(--green); font-weight: 600; white-space: nowrap; font-size: .8rem; }}

.cat-tag {{
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: .68rem;
  font-weight: 700;
  margin: 1px;
  background: var(--gray-100);
  color: var(--gray-700);
  border: 1px solid var(--gray-200);
  font-family: var(--font-mono);
}}
.status-badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: .68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
}}
.status-badge.placeholder {{ background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }}
.status-badge.partial      {{ background: var(--yellow-bg); color: var(--yellow); border: 1px solid var(--yellow-border); }}
.status-badge.complete     {{ background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }}

.no-results {{
  text-align: center;
  padding: 40px;
  color: var(--gray-500);
  font-size: .9rem;
}}

/* ── Detail panel ─────────────────────────────────────────── */
.detail-panel {{
  position: fixed;
  top: 100px; /* topnav + filterbar */
  right: -540px;
  width: 520px;
  height: calc(100vh - 100px);
  background: var(--white);
  border-left: 1px solid var(--gray-200);
  box-shadow: var(--shadow-lg);
  transition: right .25s ease;
  z-index: 400;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
.detail-panel.open {{ right: 0; }}

.detail-topbar {{
  background: var(--navy);
  color: var(--white);
  padding: 14px 18px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}}
.detail-topbar-meta {{
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}}
.detail-topbar-id {{
  font-family: var(--font-mono);
  font-size: .8rem;
  color: #6eb4ff;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.detail-topbar-id .type-label {{
  font-size: .65rem;
  background: rgba(255,255,255,.15);
  padding: 1px 8px;
  border-radius: 3px;
  font-family: var(--font-body);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: rgba(255,255,255,.7);
}}
.detail-topbar-name {{
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.35;
  color: #fff;
}}
.detail-close {{
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 6px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,.7);
  cursor: pointer;
  flex-shrink: 0;
  transition: var(--transition);
}}
.detail-close:hover {{ background: rgba(255,255,255,.2); color: #fff; }}
.detail-back {{
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 6px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,.7);
  cursor: pointer;
  flex-shrink: 0;
  transition: var(--transition);
}}
.detail-back:hover {{ background: rgba(255,255,255,.2); color: #fff; }}
.detail-link {{
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 6px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,.7);
  cursor: pointer;
  flex-shrink: 0;
  transition: var(--transition);
  position: relative;
}}
.detail-link:hover {{ background: rgba(255,255,255,.2); color: #fff; }}
.detail-link.copied {{ background: var(--green); border-color: var(--green); color: #fff; }}

.detail-body {{
  flex: 1;
  overflow-y: auto;
  padding: 0;
}}

.detail-section {{
  padding: 16px 18px;
  border-bottom: 1px solid var(--gray-100);
}}
.detail-section:last-child {{ border-bottom: none; }}
.detail-section-title {{
  font-size: .7rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--gray-500);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.detail-section-title .badge {{
  background: var(--gray-100);
  padding: 1px 6px;
  border-radius: 10px;
  font-size: .65rem;
  color: var(--gray-500);
}}
.detail-text {{
  font-size: .875rem;
  line-height: 1.65;
  color: var(--gray-700);
}}
.detail-text + .detail-text {{ margin-top: 8px; }}

.detail-tags {{
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}}
.detail-tag {{
  padding: 3px 9px;
  background: var(--gray-100);
  border: 1px solid var(--gray-200);
  border-radius: 4px;
  font-size: .78rem;
  color: var(--gray-700);
}}

.detail-list {{ display: flex; flex-direction: column; gap: 4px; }}
.detail-row {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background var(--transition);
}}
.detail-row:hover {{ background: var(--gray-50); }}
.detail-row-id  {{ font-family: var(--font-mono); font-size: .72rem; font-weight: 600; flex-shrink: 0; width: 58px; }}
.detail-row-id.t {{ color: var(--blue); }}
.detail-row-id.w {{ color: #7b3f00; }}
.detail-row-id.m {{ color: var(--green); }}
.detail-row-name {{ font-size: .82rem; color: var(--gray-700); line-height: 1.35; }}

.ref-item {{
  font-size: .78rem;
  color: var(--gray-500);
  padding: 4px 0;
  border-bottom: 1px solid var(--gray-100);
  line-height: 1.5;
}}
.ref-item:last-child {{ border-bottom: none; }}

.cat-grid {{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}}

.empty-message {{
  font-size: .8rem;
  color: var(--gray-400, #aaa);
  font-style: italic;
}}

/* ── Propose update button ─────────────────────────────────── */
.propose-update-btn {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--blue);
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: .78rem;
  font-weight: 600;
  font-family: var(--font-body);
  text-decoration: none;
  cursor: pointer;
  transition: var(--transition);
}}
.propose-update-btn:hover {{ background: var(--blue-lt); text-decoration: none; color: #fff; }}
.propose-update-btn svg {{ flex-shrink: 0; }}

/* Transitions */
.view {{ animation: fadeIn .2s ease; }}
@keyframes fadeIn {{ from{{ opacity:0; }} to{{ opacity:1; }} }}
.hidden {{ display: none !important; }}

/* ── Responsive ────────────────────────────────────────────── */
@media (max-width: 768px) {{
  .topnav-tab-label {{ display: none; }}
  .search-input {{ width: 140px; }}
  .search-input:focus {{ width: 160px; }}
  .detail-panel {{ width: 100vw; }}
  .main-area.shifted {{ margin-right: 0; }}
  .stats-banner {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* ── Misc ──────────────────────────────────────────────────── */
.github-link {{
  margin-left: 8px;
  color: rgba(255,255,255,.5);
  display: flex;
  align-items: center;
}}
.github-link:hover {{ color: rgba(255,255,255,.85); }}
.ref-table {{ table-layout: fixed; width: 100%; }}
.ref-cell {{
  padding: 8px 12px;
  font-size: .82rem;
  line-height: 1.55;
  vertical-align: top;
  word-break: break-word;
}}
.ref-url {{ color: var(--blue-lt); text-decoration: none; word-break: break-all; }}
.ref-url:hover {{ text-decoration: underline; }}
.ref-cited-cell {{ padding: 8px 10px; vertical-align: top; }}
.ref-chip {{
  display: inline-block;
  margin: 2px 3px 2px 0;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: .68rem;
  font-family: var(--font-mono);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  border: 1px solid transparent;
  transition: opacity .15s;
}}
.ref-chip:hover {{ opacity: .72; }}
.chip-t {{ background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }}
.chip-w {{ background: #fee2e2; color: #991b1b; border-color: #fecaca; }}
.chip-m {{ background: #d1fae5; color: #065f46; border-color: #a7f3d0; }}
.generated-note {{
  padding: 12px 24px;
  font-size: .75rem;
  color: var(--gray-500);
  border-top: 1px solid var(--gray-200);
  background: var(--white);
  text-align: right;
}}
.subtechniques-toggle {{
  font-size: .68rem;
  color: var(--gray-500);
  margin-top: 3px;
  cursor: pointer;
  text-decoration: underline dotted;
}}
.subtechnique-cell {{
  margin: 0 4px 0 12px;
  padding: 5px 8px 5px 14px;
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-left: 3px solid var(--blue);
  border-radius: 0 3px 3px 0;
  cursor: pointer;
  transition: var(--transition);
  font-size: .72rem;
}}
.subtechnique-cell:hover {{ background: var(--blue-pale); }}
.subtechnique-cell .tech-cell-id {{ font-size: .62rem; }}
.col-anim-delay {{ animation-fill-mode: both; }}

</style>
</head>
<body>

<!-- ───────────────── Top navigation ───────────────── -->
<nav class="topnav">
  <a class="topnav-brand" href="https://solveit-df.org" target="_blank">
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <rect width="28" height="28" rx="5" fill="#6eb4ff" fill-opacity=".15"/>
      <path d="M7 21L14 7l7 14" stroke="#6eb4ff" stroke-width="2" stroke-linecap="round"/>
      <circle cx="14" cy="14" r="2.5" fill="#6eb4ff"/>
    </svg>
    <span class="topnav-brand-name">SOLVE<span>-IT</span></span>
  </a>
  <div class="topnav-tabs">
    <button class="topnav-tab tab-t active" data-view="techniques">
      <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M2 3h12v2H2V3zm0 4h12v2H2V7zm0 4h8v2H2v-2z"/></svg>
      <span class="topnav-tab-label">Techniques</span>
      <span class="tab-badge" id="badge-t">{n_t}</span>
    </button>
    <button class="topnav-tab tab-w" data-view="weaknesses">
      <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 12.5A5.5 5.5 0 118 2.5a5.5 5.5 0 010 11zm-.5-8h1v4h-1V5.5zm0 5h1v1h-1v-1z"/></svg>
      <span class="topnav-tab-label">Weaknesses</span>
      <span class="tab-badge" id="badge-w">{n_w}</span>
    </button>
    <button class="topnav-tab tab-m" data-view="mitigations">
      <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1l1.5 4.5H14l-3.75 2.75 1.5 4.5L8 10l-3.75 2.75 1.5-4.5L2 5.5h4.5L8 1z"/></svg>
      <span class="topnav-tab-label">Mitigations</span>
      <span class="tab-badge" id="badge-m">{n_m}</span>
    </button>
    <button class="topnav-tab tab-r" data-view="references">
      <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M3 2h8a1 1 0 011 1v1h1a1 1 0 011 1v9a1 1 0 01-1 1H4a1 1 0 01-1-1v-1H2a1 1 0 01-1-1V3a1 1 0 011-1h1zm1 1v9h8V3H4zM2 5v7h1V4H2v1zm10 8v1H4v-1h8z"/></svg>
      <span class="topnav-tab-label">References</span>
      <span class="tab-badge" id="badge-r">{n_r}</span>
    </button>
  </div>
  <div class="topnav-search">
    <div class="search-wrap">
      <svg class="search-icon" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
        <path d="M11.742 10.344a6.5 6.5 0 10-1.397 1.398l3.85 3.85a1 1 0 001.415-1.414l-3.868-3.834zm-5.242 1.156a5 5 0 110-10 5 5 0 010 10z"/>
      </svg>
      <input class="search-input" id="searchInput" type="search" placeholder="Search… (press /)">
      <button class="search-clear" id="searchClear" title="Clear">&#10005;</button>
    </div>
    <a href="https://github.com/SOLVE-IT-DF/solve-it" target="_blank" class="github-link" title="GitHub">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.202 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.741 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z"/></svg>
    </a>
  </div>
</nav>

<!-- ───────────────── Filter bar ───────────────── -->
<div class="filterbar" id="filterbar">
  <!-- Technique filters -->
  <div id="fb-techniques" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    <span class="filterbar-label">Status</span>
    <button class="filter-chip active" data-tf="all">All</button>
    <button class="filter-chip chip-green" data-tf="complete">Complete</button>
    <button class="filter-chip chip-yellow" data-tf="partial">Partial</button>
    <button class="filter-chip chip-red" data-tf="placeholder">Placeholder</button>
    <div class="filterbar-sep"></div>
    <div class="filterbar-stats">
      <div class="stat-pill"><div class="stat-dot green"></div><span class="stat-num">{n_complete}</span> complete</div>
      <div class="stat-pill"><div class="stat-dot yellow"></div><span class="stat-num">{n_partial}</span> partial</div>
      <div class="stat-pill"><div class="stat-dot red"></div><span class="stat-num">{n_placeholder}</span> placeholder</div>
      <div class="filterbar-sep"></div>
      <div class="stat-pill" title="{n_t} techniques across {n_o} objectives">
        <span class="stat-num">{n_t}</span> techniques &nbsp;·&nbsp; <span class="stat-num">{n_o}</span> objectives
      </div>
      <div class="filterbar-sep"></div>
      <span class="result-count" id="t-count"></span>
    </div>
  </div>
  <!-- Weakness filters -->
  <div id="fb-weaknesses" style="display:none;align-items:center;gap:8px;flex-wrap:wrap;">
    <span class="filterbar-label">Category</span>
    <button class="filter-chip active" data-wf="all">All</button>
    <button class="filter-chip active" data-wf="INCOMP">INCOMP</button>
    <button class="filter-chip active" data-wf="INAC-EX">INAC-EX</button>
    <button class="filter-chip active" data-wf="INAC-AS">INAC-AS</button>
    <button class="filter-chip active" data-wf="INAC-ALT">INAC-ALT</button>
    <button class="filter-chip active" data-wf="INAC-COR">INAC-COR</button>
    <button class="filter-chip active" data-wf="MISINT">MISINT</button>
    <div class="filterbar-sep"></div>
    <span class="filterbar-label">Mitigations</span>
    <button class="filter-chip active" data-mf="all">All</button>
    <button class="filter-chip" data-mf="has">Has Mitigations</button>
    <button class="filter-chip" data-mf="none">Unmitigated</button>
    <div class="filterbar-sep"></div>
    <span class="result-count" id="w-count"></span>
  </div>
  <!-- Mitigation filters -->
  <div id="fb-mitigations" style="display:none;align-items:center;gap:8px;flex-wrap:wrap;">
    <span class="result-count" id="m-count"></span>
  </div>
  <!-- Reference filters -->
  <div id="fb-references" style="display:none;align-items:center;gap:8px;flex-wrap:wrap;">
    <span class="filterbar-label">Sort by</span>
    <button class="filter-chip active" data-rf="cited">Most Cited</button>
    <button class="filter-chip" data-rf="alpha">A–Z</button>
    <div class="filterbar-sep"></div>
    <span class="filterbar-label">Cited by</span>
    <button class="filter-chip active" data-rtype="all">All</button>
    <button class="filter-chip" data-rtype="techniques">Techniques</button>
    <button class="filter-chip" data-rtype="weaknesses">Weaknesses</button>
    <button class="filter-chip" data-rtype="mitigations">Mitigations</button>
    <div class="filterbar-sep"></div>
    <span class="result-count" id="r-count"></span>
  </div>
</div>

<!-- ───────────────── Page body ───────────────── -->
<div class="page-layout">
  <div class="main-area" id="mainArea">

    <!-- Techniques view -->
    <div id="view-techniques" class="view">
      <div class="matrix-container">
        <div class="matrix" id="matrix"></div>
      </div>
    </div>

    <!-- Weaknesses view -->
    <div id="view-weaknesses" class="view hidden"></div>

    <!-- Mitigations view -->
    <div id="view-mitigations" class="view hidden"></div>

    <!-- References view -->
    <div id="view-references" class="view hidden"></div>

  </div><!-- /main-area -->

  <!-- Detail panel -->
  <div class="detail-panel" id="detailPanel">
    <div class="detail-topbar">
      <button class="detail-back hidden" id="dpBack" title="Back">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M7.78 12.53a.75.75 0 01-1.06 0L2.47 8.28a.75.75 0 010-1.06l4.25-4.25a.75.75 0 011.06 1.06L4.56 7.25H13a.75.75 0 010 1.5H4.56l3.22 3.22a.75.75 0 010 1.06z"/></svg>
      </button>
      <div class="detail-topbar-meta">
        <div class="detail-topbar-id" id="dp-id"></div>
        <div class="detail-topbar-name" id="dp-name"></div>
      </div>
      <button class="detail-link" id="dpLink" title="Copy link">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4.715 6.542L3.343 7.914a3 3 0 104.243 4.243l1.828-1.829A3 3 0 008.586 5.5L8 6.086a1.002 1.002 0 00-.154.199 2 2 0 01.861 3.337L6.88 11.45a2 2 0 11-2.83-2.83l.793-.792a4.018 4.018 0 01-.128-1.287z"/><path d="M11.285 9.458l1.372-1.372a3 3 0 10-4.243-4.243L6.586 5.671A3 3 0 007.414 10.5l.586-.586a1.002 1.002 0 00.154-.199 2 2 0 01-.861-3.337L9.12 4.55a2 2 0 112.83 2.83l-.793.792c.112.42.155.855.128 1.287z"/></svg>
      </button>
      <button class="detail-close" id="dpClose" title="Close (Esc)">&#10005;</button>
    </div>
    <div class="detail-body" id="dp-body"></div>
  </div>
</div>

<div class="generated-note">
  SOLVE-IT Knowledge Base &mdash; Generated {generated_at} &mdash;
  <a href="https://github.com/SOLVE-IT-DF/solve-it" target="_blank">github.com/SOLVE-IT-DF/solve-it</a>
</div>

<!-- ─────────────────────────── JavaScript ─────────────────────────── -->
<script>
// ── Embedded data ────────────────────────────────────────────────────
const DB  = {data_json};
const IDX = {idx_json};

// ── Build lookup maps ────────────────────────────────────────────────
const TMap = Object.fromEntries(DB.techniques.map(t  => [t.id,  t]));
const WMap = Object.fromEntries(DB.weaknesses.map(w  => [w.id,  w]));
const MMap = Object.fromEntries(DB.mitigations.map(m => [m.id, m]));

// Compute mitigation enrichment
DB.mitigations.forEach(m => {{
  const wids  = IDX.mitigation_to_weaknesses[m.id] || [];
  m._wcount   = wids.length;
  const tset  = new Set();
  wids.forEach(wid => (IDX.weakness_to_techniques[wid] || []).forEach(tid => tset.add(tid)));
  m._tcount   = tset.size;
}});

// ── State ────────────────────────────────────────────────────────────
const detailHistory = [];
const S = {{
  view:    'techniques',
  search:  '',
  tf:      'all',   // technique status filter
  wf:      new Set(['INCOMP','INAC-EX','INAC-AS','INAC-ALT','INAC-COR','MISINT']),   // weakness category filter
  mf:      'all',   // mitigation filter (has/none)
  ws:      'id',    // weakness sort column
  wsDir:   1,       // weakness sort direction (1=asc, -1=desc)
  sf:      'weaknesses', // mitigation sort column
  sfDir:   -1,      // mitigation sort direction (1=asc, -1=desc)
  rf:      'cited',  // reference sort
  rtype:   'all',    // reference type filter
  selected: null,   // {{id, type}}
}};

// ── Helpers ──────────────────────────────────────────────────────────
function esc(s) {{
  if (!s) return '';
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
const CATS = ['INCOMP','INAC-EX','INAC-AS','INAC-ALT','INAC-COR','MISINT'];
const CAT_LABELS = {{
  'INCOMP':   'Incomplete',
  'INAC-EX':  'Inaccurate Extraction',
  'INAC-AS':  'Inaccurate Association',
  'INAC-ALT': 'Inaccurate Alteration',
  'INAC-COR': 'Inaccurate Corruption',
  'MISINT':   'Misinterpretation',
}};

function sortTh(label, key, stateKey, stateDirKey, style) {{
  const active = S[stateKey] === key;
  const arrow = active ? (S[stateDirKey] === 1 ? '&#9650;' : '&#9660;') : '&#9650;';
  const cls = 'sortable' + (active ? ' active' : '');
  return `<th class="${{cls}}" data-sort-key="${{key}}" data-sort-group="${{stateKey}}" style="${{style||''}}">${{label}}<span class="sort-arrow">${{arrow}}</span></th>`;
}}

function wCats(w) {{
  return CATS.filter(c => w[c] && String(w[c]).trim());
}}

function matchesSearch(item) {{
  if (!S.search) return true;
  const q = S.search.toLowerCase();
  return (item.id||'').toLowerCase().includes(q)
      || (item.name||'').toLowerCase().includes(q)
      || (item.description||'').toLowerCase().includes(q);
}}

const REPO_URL = 'https://github.com/SOLVE-IT-DF/solve-it';
function joinLines(arr) {{ return (arr||[]).join('\\n'); }}
function updateFormUrl(type, obj) {{
  const templates = {{
    technique:  '2a_update-technique-form.yml',
    weakness:   '2b_update-weakness-form.yml',
    mitigation: '2c_update-mitigation-form.yml',
  }};
  const labels = {{
    technique:  'content: update technique,form input',
    weakness:   'content: update weakness,form input',
    mitigation: 'content: update mitigation,form input',
  }};
  if (!templates[type]) return '#';

  const p = new URLSearchParams();
  p.set('template', templates[type]);
  p.set('title', `Update ${{type}}: ${{obj.id}}`);
  p.set('labels', labels[type]);

  if (type === 'technique') {{
    p.set('technique-id', obj.id);
    p.set('new-technique-name', obj.name || '');
    p.set('new-description', obj.description || '');
    p.set('new-details', obj.details || '');
    p.set('synonyms', joinLines(obj.synonyms));
    p.set('examples', joinLines(obj.examples));
    p.set('weakness-ids', joinLines(obj.weaknesses));
    p.set('case-output', joinLines(obj.CASE_output_classes));
    p.set('references', joinLines(obj.references));
  }} else if (type === 'weakness') {{
    p.set('weakness-id', obj.id);
    p.set('new-weakness-name', obj.name || '');
    p.set('mitigation-ids', joinLines(obj.mitigations));
    p.set('references', joinLines(obj.references));
  }} else if (type === 'mitigation') {{
    p.set('mitigation-id', obj.id);
    p.set('new-mitigation-name', obj.name || '');
    if (obj.technique) p.set('linked-technique-id', obj.technique);
    p.set('references', joinLines(obj.references));
  }}

  return `${{REPO_URL}}/issues/new?${{p.toString()}}`;
}}
function updateBtn(type, obj) {{
  const url = updateFormUrl(type, obj);
  const btnColor = {{technique:'var(--blue)', weakness:'var(--red)', mitigation:'var(--green)'}}[type] || 'var(--blue)';
  const btnHover = {{technique:'var(--blue-lt)', weakness:'#e74c3c', mitigation:'#22a05b'}}[type] || 'var(--blue-lt)';
  const label = {{technique:'technique', weakness:'weakness', mitigation:'mitigation'}}[type] || type;
  return `<div class="detail-section" style="padding:12px 18px">
    <a href="${{url}}" target="_blank" rel="noopener" class="propose-update-btn"
       style="background:${{btnColor}}"
       onmouseover="this.style.background='${{btnHover}}'" onmouseout="this.style.background='${{btnColor}}'">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M11.013 1.427a1.75 1.75 0 012.474 0l1.086 1.086a1.75 1.75 0 010 2.474l-8.61 8.61c-.21.21-.47.364-.756.445l-3.251.93a.75.75 0 01-.927-.928l.929-3.25a1.75 1.75 0 01.445-.758l8.61-8.61zm1.414 1.06a.25.25 0 00-.354 0L3.463 11.098a.25.25 0 00-.064.108l-.558 1.953 1.953-.558a.25.25 0 00.108-.064l8.61-8.61a.25.25 0 000-.354L12.427 2.487z"/></svg>
      Propose an update to this ${{label}}
    </a>
  </div>`;
}}

function techStatus(t) {{
  return t.status || 'placeholder';
}}

function statusClass(s) {{
  return {{placeholder:'status-red', partial:'status-yellow', complete:'status-green'}}[s]||'status-red';
}}

function statusBadge(s) {{
  return `<span class="status-badge ${{s}}">${{s}}</span>`;
}}

// ── Rendering: Matrix ────────────────────────────────────────────────
function renderMatrix() {{
  const grid = document.getElementById('matrix');
  grid.innerHTML = '';

  const objs = DB.objectives.filter(obj => {{
    const techs = filteredTechniques(obj.techniques || []);
    return techs.length > 0 || !S.search;
  }});

  let totalShown = 0;
  const subIds = new Set();
  let colIdx = 0;

  objs.forEach((obj, i) => {{
    const techs = filteredTechniques(obj.techniques || []);
    if (techs.length === 0 && S.search) return;
    totalShown += techs.length;
    techs.forEach(tid => {{ const t = TMap[tid]; if (t) (t.subtechniques || []).forEach(s => subIds.add(s)); }});

    const col = document.createElement('div');
    col.className = 'tactic-col';
    col.style.animationDelay = `${{colIdx * 0.025}}s`;
    colIdx++;

    col.innerHTML = `
      <div class="tactic-header" title="${{esc(obj.description || obj.name)}}">
        <span>${{esc(obj.name)}}</span>
        <span class="tcount">${{(obj.techniques||[]).length}} technique${{(obj.techniques||[]).length!==1?'s':''}}</span>
      </div>
      <div class="tactic-cells" id="cells-${{i}}"></div>
    `;
    grid.appendChild(col);

    const cellsDiv = col.querySelector(`#cells-${{i}}`);
    techs.sort((a,b) => ((TMap[a]||{{}}).name||'').localeCompare((TMap[b]||{{}}).name||''));
    techs.forEach(tid => {{
      const t = TMap[tid];
      if (!t) return;
      const st   = techStatus(t);
      const cls  = statusClass(st);
      const sel  = S.selected && S.selected.id === t.id && S.selected.type === 'technique';
      const subs = (t.subtechniques || []).length;

      const cell = document.createElement('div');
      cell.className = `tech-cell ${{cls}}${{sel?' selected':''}}`;
      cell.dataset.id = t.id;
      cell.title = `${{t.id}} — ${{t.name}} (${{st}})`;
      cell.innerHTML = `
        <div class="tech-cell-id">${{esc(t.id)}}</div>
        <div class="tech-cell-name">${{esc(t.name)}}</div>
        ${{subs > 0 ? `<div class="tech-cell-sub">+ ${{subs}} sub-technique${{subs>1?'s':''}}</div>` : ''}}
      `;
      cell.addEventListener('click', () => showDetail(t.id, 'technique'));
      cellsDiv.appendChild(cell);
    }});
  }});

  const nSubs = subIds.size;
  document.getElementById('t-count').textContent = `${{totalShown}} shown` + (nSubs > 0 ? ` (${{nSubs}} sub-technique${{nSubs!==1?'s':''}} not shown)` : '');

  // Equalise tactic header heights to the tallest one
  const headers = grid.querySelectorAll('.tactic-header');
  headers.forEach(h => h.style.height = 'auto');
  const maxH = Math.max(...Array.from(headers, h => h.offsetHeight));
  if (maxH > 0) headers.forEach(h => h.style.height = maxH + 'px');
}};

function filteredTechniques(ids) {{
  return ids.filter(tid => {{
    const t = TMap[tid];
    if (!t) return false;
    if (S.tf !== 'all' && techStatus(t) !== S.tf) return false;
    if (!matchesSearch(t)) return false;
    return true;
  }});
}}

// ── Rendering: Weaknesses table ──────────────────────────────────────
function renderWeaknesses() {{
  const el = document.getElementById('view-weaknesses');
  let items = DB.weaknesses.filter(w => {{
    if (!matchesSearch(w)) return false;
    const cats = wCats(w);
    const hasMit = (w.mitigations || []).length > 0;
    if (!cats.some(c => S.wf.has(c))) return false;
    if (S.mf === 'has'  && !hasMit) return false;
    if (S.mf === 'none' && hasMit)  return false;
    return true;
  }});

  const wSortFns = {{
    id:   (a,b) => a.id.localeCompare(b.id),
    name: (a,b) => (a.name||'').localeCompare(b.name||''),
    cats: (a,b) => wCats(a).length - wCats(b).length,
    mits: (a,b) => (a.mitigations||[]).length - (b.mitigations||[]).length,
  }};
  const fn = wSortFns[S.ws] || wSortFns.id;
  items.sort((a,b) => fn(a,b) * S.wsDir);

  document.getElementById('w-count').textContent = `${{items.length}} shown`;

  if (!items.length) {{
    el.innerHTML = '<div class="no-results">No weaknesses match your filters.</div>';
    return;
  }}

  el.innerHTML = `
    <div class="table-section">
      <div class="table-section-header">
        <span class="table-section-title">${{S.wf.size === CATS.length ? 'All Weaknesses' : S.wf.size === 0 ? 'No Categories Selected' : Array.from(S.wf).map(c => esc(c)).join(' + ')}}</span>
        <span class="table-section-count">${{items.length}}</span>
      </div>
      <table class="attck-table">
        <thead><tr>
          ${{sortTh('ID','id','ws','wsDir','width:80px')}}
          ${{sortTh('Name','name','ws','wsDir','')}}
          ${{sortTh('Categories','cats','ws','wsDir','width:90px')}}
          ${{sortTh('Mitigations','mits','ws','wsDir','width:80px')}}
        </tr></thead>
        <tbody>
          ${{items.map(w => {{
            const cats = wCats(w);
            const mitCount = (w.mitigations||[]).length;
            const sel = S.selected && S.selected.id === w.id;
            return `<tr class="${{sel?'selected':''}}" data-wid="${{w.id}}" data-show-id="${{esc(w.id)}}" data-show-type="weakness">
              <td><span class="wid">${{esc(w.id)}}</span></td>
              <td>${{esc(w.name)}}</td>
              <td><div class="cat-grid">${{cats.map(c=>`<span class="cat-tag">${{c}}</span>`).join('')}}</div></td>
              <td style="text-align:center;font-family:var(--font-mono);font-size:.8rem">${{mitCount}}</td>
            </tr>`;
          }}).join('')}}
        </tbody>
      </table>
    </div>
  `;
}}

// ── Rendering: Mitigations table ─────────────────────────────────────
function renderMitigations() {{
  const el = document.getElementById('view-mitigations');
  let items = DB.mitigations.filter(m => matchesSearch(m));

  const sortFns = {{
    weaknesses: (a,b) => a._wcount - b._wcount,
    techniques: (a,b) => a._tcount - b._tcount,
    id:   (a,b) => a.id.localeCompare(b.id),
    name: (a,b) => a.name.localeCompare(b.name),
  }};
  const fn = sortFns[S.sf] || sortFns.id;
  items.sort((a,b) => fn(a,b) * S.sfDir);

  document.getElementById('m-count').textContent = `${{items.length}} shown`;

  if (!items.length) {{
    el.innerHTML = '<div class="no-results">No mitigations match your search.</div>';
    return;
  }}

  el.innerHTML = `
    <div class="table-section">
      <div class="table-section-header">
        <span class="table-section-title">All Mitigations</span>
        <span class="table-section-count">${{items.length}}</span>
      </div>
      <table class="attck-table">
        <thead><tr>
          ${{sortTh('ID','id','sf','sfDir','width:80px')}}
          ${{sortTh('Name','name','sf','sfDir','')}}
          ${{sortTh('Weaknesses','weaknesses','sf','sfDir','width:100px;text-align:center')}}
          ${{sortTh('Techniques','techniques','sf','sfDir','width:100px;text-align:center')}}
        </tr></thead>
        <tbody>
          ${{items.map(m => {{
            const sel = S.selected && S.selected.id === m.id;
            return `<tr class="${{sel?'selected':''}}" data-show-id="${{esc(m.id)}}" data-show-type="mitigation">
              <td><span class="mid">${{esc(m.id)}}</span></td>
              <td>${{esc(m.name)}}</td>
              <td style="text-align:center;font-family:var(--font-mono);font-size:.8rem">${{m._wcount||'—'}}</td>
              <td style="text-align:center;font-family:var(--font-mono);font-size:.8rem">${{m._tcount||'—'}}</td>
            </tr>`;
          }}).join('')}}
        </tbody>
      </table>
    </div>
  `;
}}

// ── Detail panel ─────────────────────────────────────────────────────
function showDetail(id, type, skipHash) {{
  // Push current selection onto history before navigating
  if (S.selected) detailHistory.push({{...S.selected}});
  S.selected = {{id, type}};
  if (!skipHash) history.replaceState(null, '', '#' + id);
  updateSelectionHighlights();
  updateBackButton();

  const obj = type === 'technique'  ? TMap[id]
            : type === 'weakness'   ? WMap[id]
            : type === 'mitigation' ? MMap[id]
            : null;
  if (!obj) return;

  const typeLabel = {{technique:'Technique',weakness:'Weakness',mitigation:'Mitigation'}}[type]||type;
  const idColor   = {{technique:'#6eb4ff',weakness:'#f4a839',mitigation:'#4cba7c'}}[type]||'#6eb4ff';

  document.getElementById('dp-id').innerHTML =
    `<span style="color:${{idColor}}">${{esc(id)}}</span>
     <span class="type-label">${{typeLabel}}</span>
     ${{type==='technique' ? statusBadge(techStatus(obj)) : ''}}`;
  document.getElementById('dp-name').textContent = obj.name || '';

  let body = '';

  if (type === 'technique') {{
    body += buildTechniqueDetail(obj);
  }} else if (type === 'weakness') {{
    body += buildWeaknessDetail(obj);
  }} else if (type === 'mitigation') {{
    body += buildMitigationDetail(obj);
  }}

  document.getElementById('dp-body').innerHTML = body;
  document.getElementById('detailPanel').classList.add('open');
  document.getElementById('mainArea').classList.add('shifted');
}}

function buildTechniqueDetail(t) {{
  let html = updateBtn('technique', t);

  if (t.description) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">Description</div>
      <div class="detail-text">${{esc(t.description)}}</div>
    </div>`;
  }}

  if (t.details) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">Details</div>
      <div class="detail-text">${{esc(t.details)}}</div>
    </div>`;
  }}

  if ((t.synonyms||[]).length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">Also Known As</div>
      <div class="detail-tags">${{t.synonyms.map(s=>`<span class="detail-tag">${{esc(s)}}</span>`).join('')}}</div>
    </div>`;
  }}

  if ((t.examples||[]).length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">Examples <span class="badge">${{t.examples.length}}</span></div>
      ${{t.examples.map(e=>`<div class="detail-text" style="padding:3px 0;border-bottom:1px solid #f0f0f0">${{esc(e)}}</div>`).join('')}}
    </div>`;
  }}

  if ((t.CASE_output_classes||[]).length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">CASE Output Classes</div>
      <div class="detail-tags">${{t.CASE_output_classes.map(c=>`<span class="detail-tag" style="font-family:var(--font-mono);font-size:.72rem">${{esc(c)}}</span>`).join('')}}</div>
    </div>`;
  }}

  // Sub-techniques
  if ((t.subtechniques||[]).length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">Sub-techniques <span class="badge">${{t.subtechniques.length}}</span></div>
      <div class="detail-list">
        ${{t.subtechniques.map(sid => {{
          const st = TMap[sid];
          return `<div class="detail-row" data-show-id="${{esc(sid)}}" data-show-type="technique">
            <span class="detail-row-id t">${{esc(sid)}}</span>
            <span class="detail-row-name">${{esc(st ? st.name : sid)}}</span>
          </div>`;
        }}).join('')}}
      </div>
    </div>`;
  }}

  // Weaknesses
  const wids = t.weaknesses || [];
  html += `<div class="detail-section">
    <div class="detail-section-title">Weaknesses <span class="badge">${{wids.length}}</span></div>
    ${{!wids.length ? '<div class="empty-message">No weaknesses documented.</div>' : ''}}
    <div class="detail-list">
      ${{wids.map(wid => {{
        const w = WMap[wid];
        const cats = w ? wCats(w) : [];
        return `<div class="detail-row" data-show-id="${{esc(wid)}}" data-show-type="weakness">
          <span class="detail-row-id w">${{esc(wid)}}</span>
          <span class="detail-row-name">
            ${{w ? esc(w.name) : esc(wid)}}
            ${{cats.length ? `<br><small style="color:var(--gray-500)">${{cats.join(', ')}}</small>` : ''}}
          </span>
        </div>`;
      }}).join('')}}
    </div>
  </div>`;

  // References
  if ((t.references||[]).length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">References <span class="badge">${{t.references.length}}</span></div>
      ${{t.references.map(r => `<div class="ref-item">${{esc(r)}}</div>`).join('')}}
    </div>`;
  }}

  return html;
}}

function buildWeaknessDetail(w) {{
  let html = updateBtn('weakness', w);

  const cats = wCats(w);
  if (cats.length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">Error Categories</div>
      <div class="cat-grid">
        ${{cats.map(c => `<span class="cat-tag" style="font-size:.78rem;padding:4px 10px">${{esc(c)}}<br><small style="font-weight:400;font-family:var(--font-body)">${{esc(CAT_LABELS[c]||'')}}</small></span>`).join('')}}
      </div>
    </div>`;
  }}

  // Techniques that include this weakness
  const tids = IDX.weakness_to_techniques[w.id] || [];
  html += `<div class="detail-section">
    <div class="detail-section-title">Techniques <span class="badge">${{tids.length}}</span></div>
    ${{!tids.length ? '<div class="empty-message">No techniques reference this weakness.</div>' : ''}}
    <div class="detail-list">
      ${{tids.map(tid => {{
        const t = TMap[tid];
        return `<div class="detail-row" data-show-id="${{esc(tid)}}" data-show-type="technique">
          <span class="detail-row-id t">${{esc(tid)}}</span>
          <span class="detail-row-name">${{esc(t ? t.name : tid)}}</span>
        </div>`;
      }}).join('')}}
    </div>
  </div>`;

  // Mitigations
  const mids = w.mitigations || [];
  html += `<div class="detail-section">
    <div class="detail-section-title">Mitigations <span class="badge">${{mids.length}}</span></div>
    ${{!mids.length ? '<div class="empty-message">No mitigations documented.</div>' : ''}}
    <div class="detail-list">
      ${{mids.map(mid => {{
        const m = MMap[mid];
        return `<div class="detail-row" data-show-id="${{esc(mid)}}" data-show-type="mitigation">
          <span class="detail-row-id m">${{esc(mid)}}</span>
          <span class="detail-row-name">${{esc(m ? m.name : mid)}}</span>
        </div>`;
      }}).join('')}}
    </div>
  </div>`;

  if ((w.references||[]).length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">References <span class="badge">${{w.references.length}}</span></div>
      ${{w.references.map(r => `<div class="ref-item">${{esc(r)}}</div>`).join('')}}
    </div>`;
  }}

  return html;
}}

function buildMitigationDetail(m) {{
  let html = updateBtn('mitigation', m);

  // Weaknesses addressed
  const wids = IDX.mitigation_to_weaknesses[m.id] || [];
  html += `<div class="detail-section">
    <div class="detail-section-title">Weaknesses Addressed <span class="badge">${{wids.length}}</span></div>
    ${{!wids.length ? '<div class="empty-message">No weaknesses reference this mitigation.</div>' : ''}}
    <div class="detail-list">
      ${{wids.map(wid => {{
        const w = WMap[wid];
        const cats = w ? wCats(w) : [];
        return `<div class="detail-row" data-show-id="${{esc(wid)}}" data-show-type="weakness">
          <span class="detail-row-id w">${{esc(wid)}}</span>
          <span class="detail-row-name">
            ${{esc(w ? w.name : wid)}}
            ${{cats.length ? `<br><small style="color:var(--gray-500)">${{cats.join(', ')}}</small>` : ''}}
          </span>
        </div>`;
      }}).join('')}}
    </div>
  </div>`;

  // Techniques via weaknesses
  const tset = new Set();
  wids.forEach(wid => (IDX.weakness_to_techniques[wid]||[]).forEach(tid => tset.add(tid)));
  const tids = Array.from(tset);
  html += `<div class="detail-section">
    <div class="detail-section-title">Applies To Techniques <span class="badge">${{tids.length}}</span></div>
    ${{!tids.length ? '<div class="empty-message">No techniques.</div>' : ''}}
    <div class="detail-list">
      ${{tids.map(tid => {{
        const t = TMap[tid];
        return `<div class="detail-row" data-show-id="${{esc(tid)}}" data-show-type="technique">
          <span class="detail-row-id t">${{esc(tid)}}</span>
          <span class="detail-row-name">${{esc(t ? t.name : tid)}}</span>
        </div>`;
      }}).join('')}}
    </div>
  </div>`;

  if (m.technique) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">Implemented By Technique</div>
      <div class="detail-row" data-show-id="${{esc(m.technique)}}" data-show-type="technique">
        <span class="detail-row-id t">${{esc(m.technique)}}</span>
        <span class="detail-row-name">${{esc(TMap[m.technique] ? TMap[m.technique].name : m.technique)}}</span>
      </div>
    </div>`;
  }}

  if ((m.references||[]).length) {{
    html += `<div class="detail-section">
      <div class="detail-section-title">References <span class="badge">${{m.references.length}}</span></div>
      ${{m.references.map(r => `<div class="ref-item">${{esc(r)}}</div>`).join('')}}
    </div>`;
  }}

  return html;
}}

function closeDetail(skipHash) {{
  S.selected = null;
  detailHistory.length = 0;
  document.getElementById('detailPanel').classList.remove('open');
  document.getElementById('mainArea').classList.remove('shifted');
  if (!skipHash) history.replaceState(null, '', location.pathname);
  updateSelectionHighlights();
  updateBackButton();
}}

function goBack() {{
  const prev = detailHistory.pop();
  if (!prev) return closeDetail();
  // Navigate without pushing to history (avoid showDetail's push)
  S.selected = prev;
  updateSelectionHighlights();
  updateBackButton();

  const obj = prev.type === 'technique'  ? TMap[prev.id]
            : prev.type === 'weakness'   ? WMap[prev.id]
            : prev.type === 'mitigation' ? MMap[prev.id]
            : null;
  if (!obj) return;

  const typeLabel = {{technique:'Technique',weakness:'Weakness',mitigation:'Mitigation'}}[prev.type]||prev.type;
  const idColor   = {{technique:'#6eb4ff',weakness:'#f4a839',mitigation:'#4cba7c'}}[prev.type]||'#6eb4ff';
  document.getElementById('dp-id').innerHTML =
    `<span style="color:${{idColor}}">${{esc(prev.id)}}</span>
     <span class="type-label">${{typeLabel}}</span>
     ${{prev.type==='technique' ? statusBadge(techStatus(obj)) : ''}}`;
  document.getElementById('dp-name').textContent = obj.name || '';

  let body = '';
  if (prev.type === 'technique') body = buildTechniqueDetail(obj);
  else if (prev.type === 'weakness') body = buildWeaknessDetail(obj);
  else if (prev.type === 'mitigation') body = buildMitigationDetail(obj);
  document.getElementById('dp-body').innerHTML = body;
}}

function updateBackButton() {{
  document.getElementById('dpBack').classList.toggle('hidden', detailHistory.length === 0);
}}

function updateSelectionHighlights() {{
  // Matrix cells
  document.querySelectorAll('.tech-cell').forEach(el => {{
    el.classList.toggle('selected',
      S.selected && S.selected.type === 'technique' && el.dataset.id === S.selected.id);
  }});
  // Table rows
  document.querySelectorAll('[data-wid]').forEach(el => {{
    el.classList.toggle('selected',
      S.selected && S.selected.type === 'weakness' && el.dataset.wid === S.selected.id);
  }});
}}

// ── Rendering: References table ─────────────────────────────────────
function linkify(text) {{
  if (!text) return '';
  const urlRe = /(https?:\\/\\/[^\\s,;\\)"]+)/g;
  let result = '', last = 0, m;
  while ((m = urlRe.exec(text)) !== null) {{
    result += esc(text.slice(last, m.index));
    result += '<a href="' + esc(m[1]) + '" target="_blank" rel="noopener" class="ref-url">' + esc(m[1]) + '</a>';
    last = urlRe.lastIndex;
  }}
  result += esc(text.slice(last));
  return result;
}}

function renderReferences() {{
  const el = document.getElementById('view-references');

  const refMap = {{}};
  const addRef = (r, type, id) => {{
    const key = (r||'').trim();
    if (!key || key.toLowerCase() === 'todo') return;
    if (!refMap[key]) refMap[key] = {{techniques:[], weaknesses:[], mitigations:[]}};
    if (!refMap[key][type].includes(id)) refMap[key][type].push(id);
  }};
  DB.techniques.forEach(t  => (t.references||[]).forEach(r => addRef(r,'techniques',t.id)));
  DB.weaknesses.forEach(w  => (w.references||[]).forEach(r => addRef(r,'weaknesses',w.id)));
  DB.mitigations.forEach(m => (m.references||[]).forEach(r => addRef(r,'mitigations',m.id)));

  let items = Object.entries(refMap).filter(([ref, cb]) => {{
    if (S.rtype !== 'all' && cb[S.rtype].length === 0) return false;
    if (!S.search) return true;
    const q = S.search.toLowerCase();
    return ref.toLowerCase().includes(q)
        || cb.techniques.some(id  => id.toLowerCase().includes(q) || ((TMap[id]||{{}}).name||'').toLowerCase().includes(q))
        || cb.weaknesses.some(id  => id.toLowerCase().includes(q) || ((WMap[id]||{{}}).name||'').toLowerCase().includes(q))
        || cb.mitigations.some(id => id.toLowerCase().includes(q) || ((MMap[id]||{{}}).name||'').toLowerCase().includes(q));
  }});

  if (S.rf === 'cited') {{
    items.sort((a,b) => {{
      const sa = a[1].techniques.length + a[1].weaknesses.length + a[1].mitigations.length;
      const sb = b[1].techniques.length + b[1].weaknesses.length + b[1].mitigations.length;
      return sb - sa || a[0].localeCompare(b[0]);
    }});
  }} else {{
    items.sort((a,b) => a[0].localeCompare(b[0]));
  }}

  document.getElementById('r-count').textContent = `${{items.length}} shown`;

  if (!items.length) {{
    el.innerHTML = '<div class="no-results">No references match your filters.</div>';
    return;
  }}

  const tLabel  = {{ techniques:'T', weaknesses:'W', mitigations:'M' }};
  const tClass  = {{ techniques:'chip-t', weaknesses:'chip-w', mitigations:'chip-m' }};
  const tDetail = {{ techniques:'technique', weaknesses:'weakness', mitigations:'mitigation' }};

  let html = `<div class="table-section"><table class="attck-table ref-table">
    <thead><tr><th>Reference</th><th style="width:280px">Cited by</th></tr></thead><tbody>`;

  items.forEach(([ref, cb]) => {{
    const chips = ['techniques','weaknesses','mitigations'].flatMap(type =>
      cb[type].map(id => {{
        const item = type==='techniques'?TMap[id]:type==='weaknesses'?WMap[id]:MMap[id];
        const name = esc((item||{{}}).name||id);
        return `<span class="ref-chip ${{tClass[type]}}" title="${{name}}"
          data-show-id="${{esc(id)}}" data-show-type="${{tDetail[type]}}">${{esc(tLabel[type]+':'+id)}}</span>`;
      }})).join('');
    html += `<tr><td class="ref-cell">${{linkify(ref)}}</td><td class="ref-cited-cell">${{chips}}</td></tr>`;
  }});

  html += '</tbody></table></div>';
  el.innerHTML = html;
}}

// ── View switching ────────────────────────────────────────────────────
function switchView(view, skipHash) {{
  S.view = view;
  S.selected = null;
  closeDetail(true);
  if (!skipHash) history.replaceState(null, '', view === 'techniques' ? location.pathname : '#' + view);

  document.querySelectorAll('.topnav-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.view === view));

  document.querySelectorAll('.view').forEach(el =>
    el.classList.toggle('hidden', el.id !== `view-${{view}}`));

  document.getElementById('fb-techniques').style.display  = view === 'techniques'  ? 'flex' : 'none';
  document.getElementById('fb-weaknesses').style.display  = view === 'weaknesses'  ? 'flex' : 'none';
  document.getElementById('fb-mitigations').style.display = view === 'mitigations' ? 'flex' : 'none';
  document.getElementById('fb-references').style.display  = view === 'references'  ? 'flex' : 'none';

  render();
}}

// ── Main render dispatcher ────────────────────────────────────────────
function render() {{
  if (S.view === 'techniques')  renderMatrix();
  if (S.view === 'weaknesses')  renderWeaknesses();
  if (S.view === 'mitigations') renderMitigations();
  if (S.view === 'references')  renderReferences();
}}

// ── Event wiring ──────────────────────────────────────────────────────
document.querySelectorAll('.topnav-tab').forEach(btn =>
  btn.addEventListener('click', () => switchView(btn.dataset.view)));

document.querySelectorAll('[data-tf]').forEach(btn =>
  btn.addEventListener('click', () => {{
    document.querySelectorAll('[data-tf]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    S.tf = btn.dataset.tf;
    render();
  }}));

document.querySelectorAll('[data-wf]').forEach(btn =>
  btn.addEventListener('click', () => {{
    const val = btn.dataset.wf;
    if (val === 'all') {{
      // Toggle all on/off
      if (S.wf.size === CATS.length) S.wf.clear();
      else CATS.forEach(c => S.wf.add(c));
    }} else if (S.wf.has(val)) {{
      S.wf.delete(val);
    }} else {{
      S.wf.add(val);
    }}
    // Update active states
    document.querySelectorAll('[data-wf]').forEach(b => {{
      if (b.dataset.wf === 'all') b.classList.toggle('active', S.wf.size === CATS.length);
      else b.classList.toggle('active', S.wf.has(b.dataset.wf));
    }});
    render();
  }}));

document.querySelectorAll('[data-mf]').forEach(btn =>
  btn.addEventListener('click', () => {{
    document.querySelectorAll('[data-mf]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    S.mf = btn.dataset.mf;
    render();
  }}));

const searchInput = document.getElementById('searchInput');
const searchClear = document.getElementById('searchClear');
let searchTimer;
searchInput.addEventListener('input', e => {{
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {{
    S.search = e.target.value.trim();
    searchClear.classList.toggle('visible', !!S.search);
    render();
  }}, 220);
}});
searchClear.addEventListener('click', () => {{
  searchInput.value = '';
  S.search = '';
  searchClear.classList.remove('visible');
  render();
}});

document.getElementById('dpClose').addEventListener('click', () => closeDetail());
document.getElementById('dpBack').addEventListener('click', goBack);
document.getElementById('dpLink').addEventListener('click', () => {{
  const url = location.href;
  navigator.clipboard.writeText(url).then(() => {{
    const btn = document.getElementById('dpLink');
    btn.classList.add('copied');
    btn.title = 'Copied!';
    setTimeout(() => {{ btn.classList.remove('copied'); btn.title = 'Copy link'; }}, 1500);
  }});
}});

// Delegated click handler for sortable column headers
document.addEventListener('click', function(e) {{
  const th = e.target.closest('th.sortable');
  if (th) {{
    const key = th.dataset.sortKey;
    const group = th.dataset.sortGroup;
    const dirKey = group + 'Dir';
    if (S[group] === key) {{
      S[dirKey] = S[dirKey] * -1;
    }} else {{
      S[group] = key;
      S[dirKey] = (key === 'id' || key === 'name') ? 1 : -1;
    }}
    render();
    return;
  }}
}});

// Delegated click handler for data-show-id/data-show-type attributes (avoids inline onclick XSS risk)
document.addEventListener('click', function(e) {{
  const el = e.target.closest('[data-show-id]');
  if (el) showDetail(el.dataset.showId, el.dataset.showType);
}});

document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') {{ closeDetail(); }}
  if (e.key === '/' && !e.ctrlKey && !e.metaKey && document.activeElement !== searchInput) {{
    e.preventDefault();
    searchInput.focus();
    searchInput.select();
  }}
}});

document.querySelectorAll('[data-rf]').forEach(btn =>
  btn.addEventListener('click', () => {{
    document.querySelectorAll('[data-rf]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    S.rf = btn.dataset.rf;
    render();
  }}));

document.querySelectorAll('[data-rtype]').forEach(btn =>
  btn.addEventListener('click', () => {{
    document.querySelectorAll('[data-rtype]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    S.rtype = btn.dataset.rtype;
    render();
  }}));

// ── Bootstrap ────────────────────────────────────────────────────────
function handleHash() {{
  const hash = location.hash.slice(1);
  if (!hash) return;
  // Tab views
  if (['techniques','weaknesses','mitigations','references'].includes(hash)) {{
    switchView(hash, true);
    return;
  }}
  // Item IDs — determine type from prefix
  const type = hash.startsWith('T') ? 'technique'
             : hash.startsWith('W') ? 'weakness'
             : hash.startsWith('M') ? 'mitigation'
             : null;
  if (type) {{
    const map = {{technique:TMap, weakness:WMap, mitigation:MMap}};
    if (map[type][hash]) {{
      // Switch to the right tab first
      const viewMap = {{technique:'techniques', weakness:'weaknesses', mitigation:'mitigations'}};
      switchView(viewMap[type], true);
      showDetail(hash, type, true);
    }}
  }}
}}
render();
handleHash();
window.addEventListener('hashchange', handleHash);
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an ATT&CK-style HTML viewer for the SOLVE-IT knowledge base.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_solveit.py
  python generate_solveit.py --output solveit-viewer.html
  python generate_solveit.py --local /path/to/solve-it
  python generate_solveit.py --local ./solve-it --output viewer.html
        """,
    )
    parser.add_argument("--local", metavar="PATH",
                        help="Path to a local clone of the SOLVE-IT repo (skips GitHub fetch).")
    parser.add_argument("--output", metavar="FILE", default="solveit-viewer.html",
                        help="Output HTML file path (default: solveit-viewer.html).")
    parser.add_argument("--no-verify-ssl", action="store_true",
                        help="Disable SSL certificate verification (workaround for certificate errors).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    global _ssl_context
    if getattr(args, "no_verify_ssl", False):
        _ssl_context = ssl._create_unverified_context()
        print("[warn] SSL certificate verification disabled (--no-verify-ssl).", file=sys.stderr)

    if args.local:
        db = load_from_local(args.local)
    else:
        db = load_from_github()

    # Sort for stable output
    for key in ("techniques", "weaknesses", "mitigations"):
        db[key].sort(key=lambda x: x.get("id", ""))

    idx = build_indices(db)
    html = generate_html(db, idx)

    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"\nGenerated: {out.resolve()}  ({size_kb:.1f} KB)")
    print(f"Open in your browser:  file://{out.resolve()}")


if __name__ == "__main__":
    main()
