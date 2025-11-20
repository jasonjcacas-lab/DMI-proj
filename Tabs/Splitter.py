# -*- coding: utf-8 -*-
import os, io, re, json, hashlib
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES
from PIL import Image, ImageTk, ImageOps, ImageFilter
import fitz  # PyMuPDF
import pytesseract
from pytesseract import Output
from datetime import datetime
from time import perf_counter
import threading

# ------------------ Paths ------------------
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Bindocs_output")
RULES_PATH = os.path.join(THIS_DIR, "rules.json")
_UI_SETTINGS_PATH = os.path.join(PROJECT_ROOT, "ui_settings.json")
_SIZE_PRESETS = {
    "Small": {"geometry": (640, 480), "progress_thickness": 4},
    "Medium": {"geometry": (760, 540), "progress_thickness": 6},
    "Large": {"geometry": (880, 620), "progress_thickness": 8},
}
_DEFAULT_UI_SETTINGS = {"window_size": "Medium"}

try:
    from .region_hints import REGION_HINTS as _REGION_HINTS_DATA
except Exception:
    _REGION_HINTS_DATA = []

# Region hint measurements use a 0.0–1.1 scale where 1.1 == 11 inches.
_REGION_SCALE_MAX = 1.1


def _hint_value_to_fraction(v):
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return None
    # Clamp inside [0, 1.1] then normalise to [0, 1.0]
    fv = max(0.0, min(_REGION_SCALE_MAX, fv))
    return fv / _REGION_SCALE_MAX


def _normalise_band(band):
    if (
        not isinstance(band, (list, tuple))
        or len(band) != 2
    ):
        return None
    start = _hint_value_to_fraction(band[0])
    end = _hint_value_to_fraction(band[1])
    if start is None or end is None:
        return None
    if end < start:
        start, end = end, start
    if abs(end - start) < 1e-6:
        end = min(1.0, start + 0.01)
    return (max(0.0, start), min(1.0, end))


def _build_region_index(raw):
    index = {}
    for entry in raw or []:
        rule_name = entry.get("rule")
        target = entry.get("target")
        pattern = entry.get("pattern")
        bands = entry.get("bands") or []
        if not (rule_name and target and pattern and bands):
            continue
        normalised = []
        for band in bands:
            nb = _normalise_band(band)
            if nb:
                normalised.append(nb)
        if not normalised:
            continue
        target_map = index.setdefault(rule_name, {}).setdefault(target, [])
        target_map.append({"pattern": pattern, "bands": normalised})
    return index


_REGION_HINTS_INDEX = _build_region_index(_REGION_HINTS_DATA)

# ------------------ Debug ------------------
DEBUG = False
def _dbg(msg):
    if DEBUG:
        print(msg)

# ------------------ Globals ------------------
_DOC = None
_ALLOW_OCR = False
_TEXT_CACHE_RAW = {}
_TEXT_CACHE_CLEAN = {}
_REGION_TEXT_CACHE = {}
_RANGE_LOOKBACK_HINTS = {}
_FORCED_OCR_CACHE = set()
_OCR_PAGE_DPI = {}
_OCR_PAGE_CONF = {}
_OCR_RESULT_CACHE = {}
_OCR_PAGE_SIG = {}
_PATTERN_HIT_CACHE = {}
_PATTERN_FIRST_CACHE = {}
_PATTERN_CACHE_BY_PAGE = defaultdict(set)
_CACHE_ROOT = os.path.join(PROJECT_ROOT, "Cache")
_CACHE_OCR_BINDER = os.path.join(_CACHE_ROOT, "ocr")
_CACHE_OCR_TEMPLATES = os.path.join(_CACHE_ROOT, "templates")
_SSA_SETTINGS_PATH = os.path.join(_CACHE_ROOT, "ssa_settings.json")
_CACHE_BINDER_KEY = None
_CACHE_BINDER_DIR = None
_CANCELLED = False
_TEMPLATE_CACHE_VERSION = 1
_TEMPLATE_CACHE_MAX_PER_RULE = 20
_TEMPLATE_CACHE_MAX_BYTES = 200 * 1024 * 1024  # ~200 MB
_ADAPTIVE_DPI_STEPS = (200, 260, 320, 360)
_FORCE_OCR_TEXT_THRESHOLD = 80
SCAN_MODE_QUICK = "quick"
SCAN_MODE_ACCURACY = "accuracy"
_SCAN_MODE = SCAN_MODE_ACCURACY
_PREBATCH_RULES = {
    "Dealer Application": (8, 0),
    "Non-Listed Driver Limitation": (4, 1),
    "Named Driver Exclusion": (2, 0),
}
def set_scan_mode(mode: str):
    global _SCAN_MODE
    if mode in (SCAN_MODE_QUICK, SCAN_MODE_ACCURACY):
        _SCAN_MODE = mode


def get_scan_mode() -> str:
    return _SCAN_MODE


# ------------------ Text Extraction ------------------
def _ensure_dir(path: str):
    if not path:
        return
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _clear_pattern_caches():
    _PATTERN_HIT_CACHE.clear()
    _PATTERN_FIRST_CACHE.clear()
    _PATTERN_CACHE_BY_PAGE.clear()


def _invalidate_pattern_cache(page_idx: int):
    keys = _PATTERN_CACHE_BY_PAGE.pop(page_idx, None)
    if not keys:
        return
    for key in keys:
        _PATTERN_HIT_CACHE.pop(key, None)
        _PATTERN_FIRST_CACHE.pop(key, None)


def _ensure_cache_dirs():
    _ensure_dir(_CACHE_OCR_BINDER)
    _ensure_dir(_CACHE_OCR_TEMPLATES)


def _binder_cache_key(pdf_path: str):
    try:
        stat = os.stat(pdf_path)
        h = hashlib.sha1()
        h.update(os.path.abspath(pdf_path).lower().encode("utf-8", "ignore"))
        h.update(str(stat.st_size).encode())
        h.update(str(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9))).encode())
        return h.hexdigest()
    except Exception:
        return None


def _cache_file_path(page_idx: int, scope: str):
    if not _CACHE_BINDER_DIR:
        return None
    scope = scope or "full"
    filename = f"{page_idx:05d}_{scope}.json"
    return os.path.join(_CACHE_BINDER_DIR, filename)


def _load_disk_cache(page_idx: int, scope: str):
    path = _cache_file_path(page_idx, scope)
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        data.setdefault("scope", scope or "full")
        if "raw" not in data or "clean" not in data:
            return None
        data.setdefault("dpi", 0)
        data.setdefault("avg_conf", None)
        data.setdefault("length", len(data.get("clean") or ""))
        if "image_sig" not in data:
            data["image_sig"] = None
        return data
    except Exception:
        return None


def _save_disk_cache(page_idx: int, scope: str, entry: dict):
    if not entry:
        return
    path = _cache_file_path(page_idx, scope)
    if not path:
        return
    tmp = f"{path}.tmp"
    try:
        _ensure_dir(os.path.dirname(path))
        payload = {
            "raw": entry.get("raw", ""),
            "clean": entry.get("clean", ""),
            "dpi": int(entry.get("dpi", 0) or 0),
            "avg_conf": entry.get("avg_conf"),
            "length": int(entry.get("length", len(entry.get("clean", "") or "")) or 0),
            "scope": scope or entry.get("scope") or "full",
            "image_sig": entry.get("image_sig"),
        }
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _apply_cached_result(page_idx: int, scope: str, entry: dict):
    if not entry:
        return
    scope = scope or "full"
    key = (page_idx, scope)
    _OCR_RESULT_CACHE[key] = dict(entry)
    _invalidate_pattern_cache(page_idx)
    raw_val = entry.get("raw")
    clean_val = entry.get("clean")
    if raw_val is not None:
        _TEXT_CACHE_RAW[page_idx] = raw_val
    if clean_val is not None:
        _TEXT_CACHE_CLEAN[page_idx] = clean_val
    dpi_val = entry.get("dpi")
    if dpi_val:
        _OCR_PAGE_DPI[key] = dpi_val
    conf_val = entry.get("avg_conf")
    if conf_val is not None:
        _OCR_PAGE_CONF[key] = conf_val
    sig_val = entry.get("image_sig")
    if sig_val:
        _OCR_PAGE_SIG[key] = sig_val


def _template_rule_slug(rule_name: str) -> str:
    if not rule_name:
        return "UNKNOWN"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", rule_name.upper()).strip("_")
    return slug[:80] or "UNKNOWN"


def _template_rule_dir(rule_name: str) -> str:
    slug = _template_rule_slug(rule_name)
    path = os.path.join(_CACHE_OCR_TEMPLATES, slug)
    return path


def _template_extract_tokens(clean_text: str, limit: int = 60):
    tokens = []
    if not clean_text:
        return tokens
    for tok in clean_text.split():
        if len(tok) <= 2:
            continue
        if tok in tokens:
            continue
        tokens.append(tok)
        if len(tokens) >= limit:
            break
    return tokens


def _template_load_entry(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("version") != _TEMPLATE_CACHE_VERSION:
        return None
    data["_path"] = path
    data.setdefault("tokens", [])
    data.setdefault("tokens_count", len(data.get("tokens") or []))
    data.setdefault("hits", 0)
    if not data.get("last_used"):
        data["last_used"] = data.get("created")
    return data


def _template_collect_entries(rule_name: str):
    rule_dir = _template_rule_dir(rule_name)
    if not rule_dir or not os.path.isdir(rule_dir):
        return []
    entries = []
    try:
        for fname in os.listdir(rule_dir):
            if not fname.lower().endswith(".json"):
                continue
            path = os.path.join(rule_dir, fname)
            entry = _template_load_entry(path)
            if entry:
                entries.append(entry)
    except Exception:
        return []
    return entries


def _template_now_iso():
    return datetime.utcnow().isoformat() + "Z"


def _template_timestamp(value):
    if not value:
        return 0.0
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).timestamp()
    except Exception:
        return 0.0


def _template_write_entry(path: str, data: dict):
    tmp = f"{path}.tmp"
    payload = {k: v for k, v in data.items() if not k.startswith("_")}
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _template_mark_usage(entry: dict):
    if not entry:
        return
    path = entry.get("_path")
    if not path:
        return
    entry["hits"] = int(entry.get("hits", 0) or 0) + 1
    entry["last_used"] = _template_now_iso()
    entry.setdefault("tokens_count", len(entry.get("tokens") or []))
    payload = dict(entry)
    _template_write_entry(path, payload)
    try:
        entry["_size"] = os.path.getsize(path)
    except Exception:
        pass


def _template_entry_rank(entry: dict):
    hits = int(entry.get("hits", 0) or 0)
    tokens_count = int(entry.get("tokens_count", len(entry.get("tokens") or [])) or 0)
    uniq_score = int(entry.get("length", 0) or 0)
    last_used_ts = _template_timestamp(entry.get("last_used"))
    created_ts = _template_timestamp(entry.get("created"))
    size_score = -int(entry.get("_size", 0) or 0)
    return (hits, tokens_count, uniq_score, last_used_ts, created_ts, size_score)


def _template_match(rule_name: str, seed_text: str, seed_sig: str = None):
    clean_seed = _clean_text(seed_text or "")
    prefix_seed = clean_seed[:200] if clean_seed else ""
    token_seed = set(_template_extract_tokens(clean_seed, limit=50)) if clean_seed else set()
    if not prefix_seed and not token_seed and not seed_sig:
        return None
    candidates = _template_collect_entries(rule_name)
    best_entry = None
    best_score = 0
    for entry in candidates:
        prefix = entry.get("prefix", "")
        tokens = set(entry.get("tokens") or [])
        score = 0
        if prefix and prefix_seed:
            if prefix.startswith(prefix_seed) or prefix_seed.startswith(prefix):
                score += 100
        if token_seed and tokens:
            score += len(token_seed & tokens)
        if seed_sig and entry.get("image_sig"):
            if entry["image_sig"] == seed_sig:
                score += 200
        if score > best_score and score >= 5:
            best_score = score
            best_entry = entry
    if best_entry:
        _template_mark_usage(best_entry)
    return best_entry


def _template_evict_rule(rule_name: str):
    rule_dir = _template_rule_dir(rule_name)
    if not rule_dir or not os.path.isdir(rule_dir):
        return
    try:
        entries = _template_collect_entries(rule_name)
    except Exception:
        return
    if len(entries) <= _TEMPLATE_CACHE_MAX_PER_RULE:
        return
    entries.sort(key=_template_entry_rank)
    while len(entries) > _TEMPLATE_CACHE_MAX_PER_RULE and entries:
        entry = entries.pop(0)
        path = entry.get("_path")
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def _template_evict_global():
    root = _CACHE_OCR_TEMPLATES
    if not os.path.isdir(root):
        return
    entries = []
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.lower().endswith(".json"):
                continue
            path = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(path)
            except Exception:
                size = 0
            entry = _template_load_entry(path)
            if not entry:
                continue
            entry["_size"] = size
            total += size
            entries.append(entry)
    if total <= _TEMPLATE_CACHE_MAX_BYTES:
        return
    entries.sort(key=_template_entry_rank)
    for entry in entries:
        if total <= _TEMPLATE_CACHE_MAX_BYTES:
            break
        path = entry.get("_path")
        size = entry.get("_size", 0)
        try:
            if path and os.path.exists(path):
                os.remove(path)
                total -= size
        except Exception:
            pass


def _template_save(rule_name: str, entry: dict, clean_text: str):
    if not rule_name or not entry or not clean_text:
        return
    rule_dir = _template_rule_dir(rule_name)
    _ensure_dir(rule_dir)
    prefix = clean_text[:200]
    fingerprint_base = clean_text[:400]
    fingerprint = hashlib.sha1(fingerprint_base.encode("utf-8", "ignore")).hexdigest()
    path = os.path.join(rule_dir, f"{fingerprint}.json")
    existing = _template_load_entry(path)
    created_ts = existing.get("created") if existing else _template_now_iso()
    last_used_ts = existing.get("last_used") if existing else created_ts
    hits = int(existing.get("hits", 0) if existing else 0)
    tokens = _template_extract_tokens(clean_text, limit=60)
    payload = {
        "version": _TEMPLATE_CACHE_VERSION,
        "rule": rule_name,
        "created": created_ts,
        "last_used": last_used_ts,
        "prefix": prefix,
        "tokens": tokens,
        "tokens_count": len(tokens),
        "hits": hits,
        "raw": entry.get("raw", ""),
        "clean": entry.get("clean", ""),
        "dpi": int(entry.get("dpi", 0) or 0),
        "avg_conf": entry.get("avg_conf"),
        "length": int(entry.get("length", len(entry.get("clean", "") or "")) or 0),
        "image_sig": entry.get("image_sig"),
    }
    _template_write_entry(path, payload)
    _template_evict_rule(rule_name)
    _template_evict_global()


def _image_signature_from_image(img, size: int = 48) -> str:
    if img.mode != "L":
        img = img.convert("L")
    small = img.resize((size, size), Image.BILINEAR)
    data = small.tobytes()
    return hashlib.sha1(data).hexdigest()


def _page_signature(page_idx: int, scope: str = "full", dpi: int = 160):
    if _DOC is None:
        return None
    key = (page_idx, scope)
    existing = _OCR_PAGE_SIG.get(key)
    if existing:
        return existing
    try:
        page = _DOC[page_idx]
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        if scope == "full":
            sig = _image_signature_from_image(img)
        else:
            sig = _image_signature_from_image(img)
        _OCR_PAGE_SIG[key] = sig
        return sig
    except Exception:
        return None


def begin_text_session(pdf_path: str, allow_ocr: bool):
    global _DOC, _ALLOW_OCR, _TEXT_CACHE_RAW, _TEXT_CACHE_CLEAN
    global _CACHE_BINDER_KEY, _CACHE_BINDER_DIR
    if _DOC is not None:
        try: _DOC.close()
        except Exception: pass
    _DOC = fitz.open(pdf_path)
    _ALLOW_OCR = allow_ocr
    _TEXT_CACHE_RAW.clear()
    _TEXT_CACHE_CLEAN.clear()
    _REGION_TEXT_CACHE.clear()
    _RANGE_LOOKBACK_HINTS.clear()
    _FORCED_OCR_CACHE.clear()
    _OCR_PAGE_DPI.clear()
    _OCR_PAGE_CONF.clear()
    _OCR_RESULT_CACHE.clear()
    _OCR_PAGE_SIG.clear()
    _clear_pattern_caches()
    _CACHE_BINDER_KEY = _binder_cache_key(pdf_path)
    _CACHE_BINDER_DIR = None
    if _CACHE_BINDER_KEY:
        _ensure_cache_dirs()
        _CACHE_BINDER_DIR = os.path.join(_CACHE_OCR_BINDER, _CACHE_BINDER_KEY)

def set_cancelled(value: bool = True):
    """Set cancellation flag to stop processing."""
    global _CANCELLED
    _CANCELLED = value


def is_cancelled() -> bool:
    """Check if processing has been cancelled."""
    return _CANCELLED


def end_text_session():
    global _DOC, _TEXT_CACHE_RAW, _TEXT_CACHE_CLEAN
    global _CACHE_BINDER_KEY, _CACHE_BINDER_DIR
    try:
        if _DOC is not None: _DOC.close()
    except Exception: pass
    _DOC = None
    _TEXT_CACHE_RAW.clear()
    _TEXT_CACHE_CLEAN.clear()
    _REGION_TEXT_CACHE.clear()
    _RANGE_LOOKBACK_HINTS.clear()
    _FORCED_OCR_CACHE.clear()
    _OCR_PAGE_DPI.clear()
    _OCR_PAGE_CONF.clear()
    _OCR_RESULT_CACHE.clear()
    _OCR_PAGE_SIG.clear()
    _clear_pattern_caches()
    _CACHE_BINDER_KEY = None
    _CACHE_BINDER_DIR = None
    global _CANCELLED
    _CANCELLED = False


def assess_binder_scan_profile(pdf_path: str, sample_limit: int = 12):
    """
    Inspect a subset of pages to decide if OCR should be enabled and whether to skip the fast scan.
    Returns (allow_ocr, skip_quick, stats_dict).
    """
    stats = {
        "sample_pages": 0,
        "low_pages": 0,
        "med_pages": 0,
        "high_pages": 0,
        "low_ratio": 0.0,
        "med_ratio": 0.0,
        "high_ratio": 0.0,
        "skip_reason": None,
    }
    allow_ocr = True
    skip_quick = False
    skip_reason = None
    tmp = None

    try:
        tmp = fitz.open(pdf_path)
        total_pages = len(tmp)
        sample_cap = max(1, sample_limit)
        sample = min(total_pages, sample_cap)
        if sample <= 0:
            raise ValueError("empty pdf")
        if sample == total_pages:
            indices = list(range(sample))
        else:
            indices = sorted(
                set(
                    int(round(k * (total_pages - 1) / (sample - 1 or 1)))
                    for k in range(sample)
                )
            )

        low_text = med_text = high_text = 0
        for idx in indices:
            raw_txt = (tmp[idx].get_text("text") or "").strip()
            ln = len(raw_txt)
            if ln < 80:
                low_text += 1
            if ln < 250:
                med_text += 1
            if ln > 600:
                high_text += 1

        sample_count = len(indices)
        stats["sample_pages"] = sample_count
        stats["low_pages"] = low_text
        stats["med_pages"] = med_text
        stats["high_pages"] = high_text

        suspect_ratio_low = low_text / float(sample_count or 1)
        suspect_ratio_med = med_text / float(sample_count or 1)
        high_ratio = high_text / float(sample_count or 1)

        stats["low_ratio"] = suspect_ratio_low
        stats["med_ratio"] = suspect_ratio_med
        stats["high_ratio"] = high_ratio

        allow_ocr = (suspect_ratio_med > 0.4) or (
            high_text < max(1, int(0.6 * sample_count))
        )

        if allow_ocr and sample_count:
            high_sparse_cap = max(1, sample_count // 4)
            if suspect_ratio_low >= 0.22:
                skip_reason = f"low_text_ratio={suspect_ratio_low:.2f}"
            elif suspect_ratio_med >= 0.5:
                skip_reason = f"med_text_ratio={suspect_ratio_med:.2f}"
            elif high_text <= high_sparse_cap and suspect_ratio_med >= 0.4:
                skip_reason = f"sparse_high_text={high_text}/{sample_count}"

        skip_quick = bool(skip_reason)

    except Exception as exc:
        stats["error"] = str(exc)
        allow_ocr = True
        skip_quick = True
        if not skip_reason:
            skip_reason = "error"
    finally:
        try:
            if tmp is not None:
                tmp.close()
        except Exception:
            pass

    stats["allow_ocr"] = allow_ocr
    stats["skip_quick"] = skip_quick
    stats["skip_reason"] = skip_reason
    return allow_ocr, skip_quick, stats


def _clean_text(s: str) -> str:
    if not s: return ""
    s = s.upper().replace("'","'")
    s = re.sub(r"[^A-Z0-9#+/]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def _page_text_blocks(idx: int) -> str:
    """Return concatenated text from PyMuPDF text blocks for page idx."""
    if _DOC is None: return ""
    try:
        blocks = _DOC[idx].get_text("blocks") or []
        texts = []
        for b in blocks:
            t = (b[4] or "").strip()
            if t:
                texts.append(t)
        return "\n".join(texts)
    except Exception:
        return ""

def _page_text_words(idx: int) -> str:
    """Return concatenated text from 'words' (sorted left-to-right, top-to-bottom)."""
    if _DOC is None: return ""
    try:
        words = _DOC[idx].get_text("words") or []  # (x0,y0,x1,y1,"word",block,line,word_no)
        words.sort(key=lambda w: (round(w[1], 1), w[0]))
        return " ".join(w[4] for w in words if w[4])
    except Exception:
        return ""

def _merge_and_clean(*parts: str) -> str:
    raw = " \n ".join(p for p in parts if p)
    return _clean_text(raw)

def _select_initial_dpi(page_idx: int, scope: str, requested=None) -> int:
    base = 200 if scope == "full" else 200
    if requested is not None:
        try:
            base = max(base, int(requested))
        except Exception:
            pass
    try:
        if _looks_like_table(page_idx):
            base = max(base, 320 if scope == "full" else 300)
    except Exception:
        pass
    return max(150, min(360, base))

def _next_dpi(current: int) -> int:
    for step in _ADAPTIVE_DPI_STEPS:
        if step > current:
            return step
    return current

def _scope_quality_threshold(scope: str) -> int:
    return 80 if scope == "full" else 35

def _needs_escalation(scope: str, text_length: int, avg_conf, dpi: int) -> bool:
    max_dpi = _ADAPTIVE_DPI_STEPS[-1]
    if dpi >= max_dpi:
        return False
    if avg_conf is not None and avg_conf < 85.0:
        return True
    if text_length < _scope_quality_threshold(scope):
        return True
    return False

def _update_page_cache(page_idx: int, raw: str):
    existing_raw = _TEXT_CACHE_RAW.get(page_idx, "")
    if raw:
        raw_clean = _clean_text(raw)
        existing_clean = _clean_text(existing_raw) if existing_raw else ""
        if not existing_raw:
            combined = raw
        elif raw_clean == existing_clean or raw.strip() == existing_raw.strip():
            combined = existing_raw
        elif existing_raw.strip() and existing_raw.strip() in raw:
            combined = raw
        elif raw.strip() and raw.strip() in existing_raw:
            combined = existing_raw
        else:
            combined = f"{existing_raw}\n{raw}"
    else:
        combined = existing_raw
    _TEXT_CACHE_RAW[page_idx] = combined
    _TEXT_CACHE_CLEAN[page_idx] = _clean_text(combined)
    _invalidate_pattern_cache(page_idx)

def _ocr_page_region_into_cache(i: int, region: str = "full", pct: float = 0.35, dpi: int = None, binarize: bool = True):
    """
    OCR page i and update RAW/CLEAN caches with adaptive DPI.
    region: "full" | "bottom_strip" | "middle_band"
    pct: height fraction for region (0.05..0.95), used for strips/bands
    """
    global _DOC, _TEXT_CACHE_RAW, _TEXT_CACHE_CLEAN
    if _DOC is None or _CANCELLED:
        return

    scope = region or "full"
    key = (i, scope)
    cache_entry = _OCR_RESULT_CACHE.get(key)
    if cache_entry is None:
        disk_entry = _load_disk_cache(i, scope)
        if disk_entry:
            cache_entry = dict(disk_entry)
            _apply_cached_result(i, scope, cache_entry)
    target_dpi = _select_initial_dpi(i, scope, requested=dpi)
    if cache_entry:
        cached_dpi = cache_entry.get("dpi", 0)
        cached_len = cache_entry.get("length", 0)
        cached_conf = cache_entry.get("avg_conf")
        needs_upgrade = False
        if dpi is not None and cached_dpi < target_dpi:
            needs_upgrade = True
        if cached_len < _scope_quality_threshold(scope):
            needs_upgrade = True
        if cached_conf is not None and cached_conf < 85.0 and cached_dpi < _ADAPTIVE_DPI_STEPS[-1]:
            needs_upgrade = True
        if not needs_upgrade:
            _TEXT_CACHE_RAW[i] = cache_entry.get("raw", _TEXT_CACHE_RAW.get(i, ""))
            _TEXT_CACHE_CLEAN[i] = cache_entry.get("clean", _TEXT_CACHE_CLEAN.get(i, ""))
            _OCR_PAGE_DPI[key] = cached_dpi
            if cached_conf is not None:
                _OCR_PAGE_CONF[key] = cached_conf
            return
        target_dpi = max(target_dpi, cached_dpi)
    pct = max(0.05, min(0.95, float(pct)))
    current_dpi = max(target_dpi, _OCR_PAGE_DPI.get(key, target_dpi))
    image_sig = None

    while True:
        if _CANCELLED:
            break
        avg_conf = None
        try:
            page = _DOC[i]
            pix = page.get_pixmap(dpi=current_dpi, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
            width, height = img.size

            if scope == "bottom_strip":
                top = int(height * (1.0 - pct))
                img = img.crop((0, top, width, height))
            elif scope == "middle_band":
                band_h = int(height * pct)
                top = max(0, (height // 2) - band_h // 2)
                img = img.crop((0, top, width, min(height, top + band_h)))

            if binarize:
                img = ImageOps.autocontrast(img)
                img = img.filter(ImageFilter.MedianFilter(size=3))
                img = img.point(lambda p: 255 if p > 200 else (0 if p < 120 else p))
            if scope == "full":
                try:
                    image_sig = _image_signature_from_image(img)
                except Exception:
                    image_sig = None

            data = pytesseract.image_to_data(
                img,
                config="--oem 1 --psm 6 -l eng",
                output_type=Output.DICT
            )

            words = data.get("text", [])
            confs = data.get("conf", [])
            block_nums = data.get("block_num", [])
            par_nums = data.get("par_num", [])
            line_nums = data.get("line_num", [])

            lines = []
            current_line = []
            current_key = None
            conf_vals = []

            for idx, word in enumerate(words):
                w = (word or "").strip()
                if not w:
                    continue
                try:
                    conf_val = float(confs[idx])
                except Exception:
                    conf_val = -1.0
                if conf_val >= 0:
                    conf_vals.append(conf_val)
                key_tuple = (
                    block_nums[idx] if idx < len(block_nums) else 0,
                    par_nums[idx] if idx < len(par_nums) else 0,
                    line_nums[idx] if idx < len(line_nums) else 0
                )
                if current_key is None:
                    current_key = key_tuple
                    current_line = [w]
                elif key_tuple != current_key:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [w]
                    current_key = key_tuple
                else:
                    current_line.append(w)

            if current_line:
                lines.append(" ".join(current_line))

            raw = "\n".join(lines).strip()
            avg_conf = (sum(conf_vals) / len(conf_vals)) if conf_vals else None
        except Exception as e:
            _dbg(f"OCR (region={scope}) warn p{i+1}: {e}")
            raw = ""
            avg_conf = None

        _update_page_cache(i, raw)
        cleaned = _clean_text(raw)
        combined_clean = _TEXT_CACHE_CLEAN.get(i, cleaned)
        length_metric = len(combined_clean) if scope == "full" else len(cleaned)
        _OCR_PAGE_DPI[key] = current_dpi
        if avg_conf is not None:
            _OCR_PAGE_CONF[key] = avg_conf
        final_raw = _TEXT_CACHE_RAW.get(i, raw)
        final_clean = _TEXT_CACHE_CLEAN.get(i, combined_clean)
        _OCR_RESULT_CACHE[key] = {
            "raw": final_raw,
            "clean": final_clean,
            "dpi": current_dpi,
            "avg_conf": avg_conf,
            "length": length_metric,
            "scope": scope,
            "image_sig": image_sig,
        }

        if not _needs_escalation(scope, length_metric, avg_conf, current_dpi):
            break

        next_dpi = _next_dpi(current_dpi)
        if next_dpi <= current_dpi:
            break

        if DEBUG:
            _dbg(f"[OCR] Escalate DPI p{i+1} scope={scope} {current_dpi}->{next_dpi} "
                 f"(conf={avg_conf if avg_conf is not None else 'n/a'}, len={length_metric})")

        current_dpi = next_dpi
    final_entry = _OCR_RESULT_CACHE.get(key)
    if final_entry:
        if scope == "full" and image_sig and not final_entry.get("image_sig"):
            final_entry["image_sig"] = image_sig
        _save_disk_cache(i, scope, final_entry)

def page_text(pdf_path, page_index):
    """
    Populate RAW cache with best-effort text:
      - native 'text'
      - plus table-friendly 'blocks' and 'words'
      - escalate to OCR only when allowed by caller
    """
    global _DOC, _ALLOW_OCR, _TEXT_CACHE_RAW
    if page_index in _TEXT_CACHE_RAW:
        return _TEXT_CACHE_RAW[page_index]

    raw_text = ""
    blocks_text = ""
    words_text = ""
    if _DOC:
        try:
            raw_text = (_DOC[page_index].get_text("text") or "").strip()
        except Exception:
            raw_text = ""
        blocks_text = _page_text_blocks(page_index)
        words_text  = _page_text_words(page_index)

    merged = "\n".join(t for t in (raw_text, blocks_text, words_text) if t)

    # Escalate to OCR only if permitted and merged text is thin
    if (not merged or len(_clean_text(merged)) < 100) and _ALLOW_OCR and _DOC:
        try:
            _ocr_page_region_into_cache(page_index, region="full", pct=0.9, dpi=None, binarize=True)
            merged = _TEXT_CACHE_RAW.get(page_index, merged)
        except Exception as e:
            _dbg(f"OCR warn p{page_index+1}: {e}")

    _TEXT_CACHE_RAW[page_index] = merged
    return merged

def _page_cleaned(pdf_path, idx) -> str:
    if idx in _TEXT_CACHE_CLEAN:
        return _TEXT_CACHE_CLEAN[idx]
    raw = page_text(pdf_path, idx)
    cleaned = _clean_text(raw)
    _TEXT_CACHE_CLEAN[idx] = cleaned
    return cleaned

def _suspect_pages():
    if _DOC is None: return []
    suspects = []
    for i in range(len(_DOC)):
        t = (_DOC[i].get_text("text") or "").strip()
        if len(t) < 100:
            suspects.append(i)
    return suspects


def _region_cache_key(page_idx: int, band):
    return (page_idx, round(band[0], 4), round(band[1], 4))


def _get_region_clean(page_idx: int, start_frac: float, end_frac: float) -> str:
    if _DOC is None:
        return ""
    start = max(0.0, min(1.0, float(start_frac)))
    end = max(0.0, min(1.0, float(end_frac)))
    if end < start:
        start, end = end, start
    if abs(end - start) < 1e-4:
        end = min(1.0, start + 0.01)
    band = (start, end)
    key = _region_cache_key(page_idx, band)
    if key in _REGION_TEXT_CACHE:
        return _REGION_TEXT_CACHE[key]

    try:
        page = _DOC[page_idx]
        rect = page.rect
        top = rect.y0 + rect.height * start
        bottom = rect.y0 + rect.height * end
        clip = fitz.Rect(rect.x0, top, rect.x1, bottom)

        text = (page.get_text("text", clip=clip) or "").strip()
        if not text:
            blocks = page.get_text("blocks", clip=clip) or []
            if blocks:
                block_lines = [(blk[4] or "").strip() for blk in blocks if (blk[4] or "").strip()]
                text = "\n".join(block_lines)
        if not text:
            words = page.get_text("words", clip=clip) or []
            if words:
                words.sort(key=lambda w: (round(w[1], 1), w[0]))
                text = " ".join(w[4] for w in words if w[4])
        if not text and _ALLOW_OCR:
            try:
                pix = page.get_pixmap(clip=clip, dpi=300, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
                img = ImageOps.autocontrast(img)
                text = pytesseract.image_to_string(img, config="--oem 1 --psm 6 -l eng")
            except Exception as e:
                _dbg(f"OCR region warn p{page_idx+1}: {e}")
                text = ""
    except Exception as e:
        _dbg(f"Region extraction warn p{page_idx+1}: {e}")
        text = ""

    cleaned = _clean_text(text)
    _REGION_TEXT_CACHE[key] = cleaned
    return cleaned


def _resolve_pattern_list(rule: dict, target: str):
    if not rule or not target:
        return None
    if target.startswith("start.") and isinstance(rule.get("start"), dict):
        key = target.split(".", 1)[1]
        lst = rule["start"].get(key)
        return lst if isinstance(lst, list) else None
    if target.startswith("end.") and isinstance(rule.get("end"), dict):
        key = target.split(".", 1)[1]
        lst = rule["end"].get(key)
        return lst if isinstance(lst, list) else None
    lst = rule.get(target)
    return lst if isinstance(lst, list) else None


def _attach_region_hints(rule: dict):
    hints = _REGION_HINTS_INDEX.get(rule.get("name"))
    if not hints:
        return
    store = rule.setdefault("_region_hints", {})
    for target, entries in hints.items():
        compiled_list = _resolve_pattern_list(rule, target)
        if not compiled_list:
            continue
        target_store = store.setdefault(target, {})
        for entry in entries:
            pattern_text = entry["pattern"]
            bands = [tuple(b) for b in entry["bands"]]
            for compiled in compiled_list:
                if compiled.pattern == pattern_text:
                    target_store[compiled] = bands


def _pattern_hits(rule: dict, target: str, patterns, page_idx: int, cleaned_texts, pdf_path: str = None) -> int:
    if not patterns:
        return 0
    rid = rule.get("_cache_id")
    if rid is None:
        rid = id(rule)
    cache_key = (rid, target, page_idx)
    cached = _PATTERN_HIT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    cleaned_text = cleaned_texts[page_idx]
    total = 0
    hint_map = (rule.get("_region_hints") or {}).get(target)
    for pat in patterns:
        matched = False
        if hint_map and pat in hint_map:
            for band in hint_map[pat]:
                region_text = _get_region_clean(page_idx, band[0], band[1])
                if region_text and pat.search(region_text):
                    matched = True
                    total += 1
                    break
        if not matched and pat.search(cleaned_text):
            total += 1
    _PATTERN_HIT_CACHE[cache_key] = total
    _PATTERN_CACHE_BY_PAGE[page_idx].add(cache_key)
    return total


def _pattern_first_match(rule: dict, target: str, patterns, page_idx: int, cleaned_texts, pdf_path: str = None):
    if not patterns:
        return None
    rid = rule.get("_cache_id")
    if rid is None:
        rid = id(rule)
    cache_key = (rid, ("first", target), page_idx)
    if cache_key in _PATTERN_FIRST_CACHE:
        return _PATTERN_FIRST_CACHE[cache_key]
    cleaned_text = cleaned_texts[page_idx]
    hint_map = (rule.get("_region_hints") or {}).get(target)
    for pat in patterns:
        if hint_map and pat in hint_map:
            for band in hint_map[pat]:
                region_text = _get_region_clean(page_idx, band[0], band[1])
                if region_text and pat.search(region_text):
                    _PATTERN_FIRST_CACHE[cache_key] = pat
                    _PATTERN_CACHE_BY_PAGE[page_idx].add(cache_key)
                    return pat
        if pat.search(cleaned_text):
            _PATTERN_FIRST_CACHE[cache_key] = pat
            _PATTERN_CACHE_BY_PAGE[page_idx].add(cache_key)
            return pat
    _PATTERN_FIRST_CACHE[cache_key] = None
    _PATTERN_CACHE_BY_PAGE[page_idx].add(cache_key)
    return None

# ------------------ Rules ------------------
def load_rules(path=RULES_PATH):
    with open(path,"r",encoding="utf-8") as f:
        rules = json.load(f)

    # Filter out disabled SSA rules
    enabled_ssas = _load_ssa_settings()
    # Always filter: keep non-SSA rules, and only enabled SSA rules
    rules = [r for r in rules if not r.get("name", "").startswith("SSA ") or r.get("name", "") in enabled_ssas]

    def _compile_list(lst): return [re.compile(p) for p in lst]

    for r in rules:
        for k in ("require_any","helpful_cues","forbid_any"):
            if k in r and isinstance(r[k], list):
                r[k] = _compile_list(r[k])
        if "start" in r:
            for k in ("any_cues","next_page_hits","fallback_cues"):
                if k in r["start"] and isinstance(r["start"][k], list):
                    r["start"][k] = _compile_list(r["start"][k])
            for k in ("lookback_prev_forbid",):
                if k in r["start"] and isinstance(r["start"][k], list):
                    r["start"][k] = _compile_list(r["start"][k])
        if "end" in r:
            for k in ("first_cue",):
                if k in r["end"] and isinstance(r["end"][k], list):
                    r["end"][k] = _compile_list(r["end"][k])
        _attach_region_hints(r)

    rules.sort(key=lambda x: x.get("priority",0), reverse=True)
    for idx, r in enumerate(rules):
        r["_cache_id"] = idx
    return rules

def _hits(text, patterns): 
    return sum(1 for p in patterns if p.search(text))

# ------------------ Matching ------------------
DEBUG_SINGLE_PAGE_RULES = {
    "Excess Hazards Coverage NY",
    "SSA IL",
    "SSA WI",
    "Named Driver Exclusion",
    "Named Driver Exclusion WS",
}

FORCE_OCR_RULES = {
    "SSA IL",
    "SSA WI",
    "Named Driver Exclusion",
    "Named Driver Exclusion WS",
}


def _force_full_page_ocr(page_idx: int, reason: str = "", force: bool = False,
                         rule_name: str = None, seed_text: str = None):
    key = (page_idx, "full")
    if not force and key in _FORCED_OCR_CACHE:
        if DEBUG and reason:
            _dbg(f"[OCR] Skip re-OCR page {page_idx+1}: {reason} (cached)")
        cached = _OCR_RESULT_CACHE.get(key)
        if cached:
            _apply_cached_result(page_idx, "full", cached)
            if rule_name:
                clean_text = cached.get("clean") or _TEXT_CACHE_CLEAN.get(page_idx, "")
                if clean_text:
                    _template_save(rule_name, cached, clean_text)
        return
    if key not in _OCR_RESULT_CACHE:
        disk_entry = _load_disk_cache(page_idx, "full")
        if disk_entry and not force:
            _apply_cached_result(page_idx, "full", disk_entry)
            _FORCED_OCR_CACHE.add(key)
            if DEBUG and reason:
                _dbg(f"[OCR] Restored cached OCR page {page_idx+1}: {reason}")
            return
    if not force and rule_name:
        template_seed = seed_text
        if not template_seed:
            template_seed = _TEXT_CACHE_CLEAN.get(page_idx) or _TEXT_CACHE_RAW.get(page_idx) or ""
        template_entry = _template_match(rule_name, template_seed)
        if not template_entry:
            template_sig = _page_signature(page_idx, "full")
            if template_sig:
                template_entry = _template_match(rule_name, template_seed, template_sig)
        if template_entry:
            _apply_cached_result(page_idx, "full", template_entry)
            _FORCED_OCR_CACHE.add(key)
            _save_disk_cache(page_idx, "full", _OCR_RESULT_CACHE.get(key))
            if DEBUG:
                _dbg(f"[OCR] Template cache hit p{page_idx+1} rule={rule_name}")
            return
    if key in _FORCED_OCR_CACHE and not force:
        return
    try:
        if reason:
            print(f"[OCR] Forcing OCR on page {page_idx+1}: {reason}")
        _ocr_page_region_into_cache(page_idx, region="full", pct=0.9, dpi=300, binarize=True)
        _FORCED_OCR_CACHE.add(key)
        if rule_name:
            entry = _OCR_RESULT_CACHE.get(key)
            clean_text = entry.get("clean") if entry else _TEXT_CACHE_CLEAN.get(page_idx, "")
            if entry and clean_text:
                _template_save(rule_name, entry, clean_text)
    except Exception as e:
        print(f"[OCR] Error forcing OCR on page {page_idx+1}: {e}")


def _maybe_force_full_page_ocr(page_idx: int, reason: str, page_txt: str,
                               allow_force: bool, rule_name: str = None) -> bool:
    if not allow_force:
        return False
    if len(page_txt or "") >= _FORCE_OCR_TEXT_THRESHOLD:
        return False
    _force_full_page_ocr(page_idx, reason, rule_name=rule_name, seed_text=page_txt)
    return True


def _prebatch_rule_pages(rule_name: str, cleaned_texts, start_idx: int, pdf_path: str):
    if _DOC is None:
        return
    cfg = _PREBATCH_RULES.get(rule_name)
    if not cfg:
        return
    span, lookback = cfg
    total_pages = len(_DOC)
    start_page = max(0, start_idx - lookback)
    end_page = min(start_idx + span, total_pages)
    for j in range(start_page, end_page):
        if _CANCELLED:
            break
        text_len = len(cleaned_texts[j]) if j < len(cleaned_texts) else 0
        key = (j, "full")
        if text_len >= _FORCE_OCR_TEXT_THRESHOLD:
            continue
        if key in _FORCED_OCR_CACHE:
            continue
        seed = cleaned_texts[j] if j < len(cleaned_texts) else ""
        _force_full_page_ocr(j, f"{rule_name} prebatch", rule_name=rule_name, seed_text=seed)
        if j < len(cleaned_texts):
            cleaned_texts[j] = _page_cleaned(pdf_path, j)


def match_single_page_rule(cleaned_texts, page_idx: int, rule: dict, pdf_path: str) -> bool:
    cleaned_text = cleaned_texts[page_idx]
    rule_name = rule.get("name", "")
    debug_rule = rule_name in DEBUG_SINGLE_PAGE_RULES

    # Check start.any_cues if present
    if "start" in rule and "any_cues" in rule["start"]:
        start_hits = _pattern_hits(rule, "start.any_cues", rule["start"]["any_cues"], page_idx, cleaned_texts, pdf_path)
        if start_hits == 0 and rule_name in FORCE_OCR_RULES:
            if _maybe_force_full_page_ocr(page_idx, "start cue missing", cleaned_text, True, rule_name):
                cleaned_text = _page_cleaned(pdf_path, page_idx)
                cleaned_texts[page_idx] = cleaned_text
                start_hits = _pattern_hits(rule, "start.any_cues", rule["start"]["any_cues"], page_idx, cleaned_texts, pdf_path)
        if start_hits == 0:
            if debug_rule:
                print(f"[Debug] '{rule_name}' failed: start.any_cues not found")
                print(f"  Text sample: {cleaned_text[:200]}..." if cleaned_text else "  <empty text>")
            return False
        if debug_rule:
            print(f"[Debug] '{rule_name}' start.any_cues hits: {start_hits}")

    if "forbid_any" in rule and _pattern_hits(rule, "forbid_any", rule["forbid_any"], page_idx, cleaned_texts, pdf_path) > 0:
        if debug_rule:
            print(f"[Debug] '{rule_name}' failed: forbid_any matched")
            for pattern in rule["forbid_any"]:
                if pattern.search(cleaned_text):
                    print(f"  Matched forbid pattern: {pattern.pattern[:80]}")
        return False
    if "require_any" in rule:
        req_hits = _pattern_hits(rule, "require_any", rule["require_any"], page_idx, cleaned_texts, pdf_path)
        if req_hits == 0 and rule_name in FORCE_OCR_RULES:
            if _maybe_force_full_page_ocr(page_idx, "require cue missing", cleaned_text, True, rule_name):
                cleaned_text = _page_cleaned(pdf_path, page_idx)
                cleaned_texts[page_idx] = cleaned_text
                req_hits = _pattern_hits(rule, "require_any", rule["require_any"], page_idx, cleaned_texts, pdf_path)
        if req_hits == 0:
            if debug_rule:
                print(f"[Debug] '{rule_name}' failed: require_any not found")
                print(f"  Text sample: {cleaned_text[:200]}...")
            return False

    if "helpful_cues" in rule:
        helpful_hits = _pattern_hits(rule, "helpful_cues", rule["helpful_cues"], page_idx, cleaned_texts, pdf_path)
        min_helpful = rule.get("min_helpful", 0)
        if helpful_hits < min_helpful and rule_name in FORCE_OCR_RULES:
            if _maybe_force_full_page_ocr(page_idx, "helpful cue missing", cleaned_text, True, rule_name):
                cleaned_text = _page_cleaned(pdf_path, page_idx)
                cleaned_texts[page_idx] = cleaned_text
                helpful_hits = _pattern_hits(rule, "helpful_cues", rule["helpful_cues"], page_idx, cleaned_texts, pdf_path)
        if helpful_hits < min_helpful:
            if debug_rule:
                print(f"[Debug] '{rule_name}' failed: helpful_cues ({helpful_hits}) < min_helpful ({min_helpful})")
                print(f"  Text sample: {cleaned_text[:200]}...")
            return False

    if debug_rule:
        print(f"[Debug] '{rule_name}' MATCHED!")
    _maybe_save_template(rule_name, page_idx)
    return True

DEBUG_RANGE_RULES = {
    "Non-Listed Driver Limitation",
}

FORCE_OCR_RANGE_RULES = {
    "Non-Listed Driver Limitation",
}


def match_range_start(cleaned_texts, i, rule: dict, pdf_path: str) -> bool:
    """
    Start-page gate for range rules. Enforces:
      - top-level forbid_any / require_any / helpful_cues (+min_helpful)
      - start.any_cues (at least one)
      - start.next_page_hits (optional lookahead)
    """
    s = rule.get("start", {})
    page_txt = cleaned_texts[i]
    rule_name = rule.get("name", "")
    debug_rule = rule_name in DEBUG_RANGE_RULES

    # Enforce top-level exclusions/inclusions for range rules
    # reset any previous hint
    _RANGE_LOOKBACK_HINTS.pop((rule_name, i), None)

    if "forbid_any" in rule and _pattern_hits(rule, "forbid_any", rule["forbid_any"], i, cleaned_texts, pdf_path) > 0:
        if debug_rule:
            print(f"[Debug] '{rule_name}' failed: forbid_any matched")
        return False
    require_from_prev = False
    if "require_any" in rule and _pattern_hits(rule, "require_any", rule["require_any"], i, cleaned_texts, pdf_path) == 0:
        req_hits = 0
        if rule_name in FORCE_OCR_RANGE_RULES:
            if _maybe_force_full_page_ocr(i, "range require cue missing", page_txt, True, rule_name):
                page_txt = _page_cleaned(pdf_path, i)
                cleaned_texts[i] = page_txt
                req_hits = _pattern_hits(rule, "require_any", rule["require_any"], i, cleaned_texts, pdf_path)
        else:
            req_hits = _pattern_hits(rule, "require_any", rule["require_any"], i, cleaned_texts, pdf_path)

        if req_hits == 0:
            s = rule.get("start", {}) or {}
            fallback_cues = s.get("fallback_cues")
            fallback_current = _hits(page_txt, fallback_cues) if fallback_cues else 0
            if (s.get("fallback_to_previous")
                and fallback_cues and fallback_current > 0
                and i > 0):
                prev_txt = cleaned_texts[i - 1]
                if rule_name in FORCE_OCR_RANGE_RULES:
                    if _maybe_force_full_page_ocr(i - 1, "range require previous", prev_txt, True, rule_name):
                        prev_txt = _page_cleaned(pdf_path, i - 1)
                        cleaned_texts[i - 1] = prev_txt
                if _pattern_hits(rule, "require_any", rule["require_any"], i - 1, cleaned_texts, pdf_path) > 0:
                    _RANGE_LOOKBACK_HINTS[(rule_name, i)] = True
                    require_from_prev = True
                else:
                    if debug_rule:
                        print(f"[Debug] '{rule_name}' failed: require_any not found")
                    return False
            else:
                if debug_rule:
                    print(f"[Debug] '{rule_name}' failed: require_any not found")
                return False
    if "helpful_cues" in rule:
        helpful_hits = _pattern_hits(rule, "helpful_cues", rule["helpful_cues"], i, cleaned_texts, pdf_path)
        if helpful_hits < rule.get("min_helpful", 0):
            if rule_name in FORCE_OCR_RANGE_RULES:
                if _maybe_force_full_page_ocr(i, "range helpful cue missing", page_txt, True, rule_name):
                    page_txt = _page_cleaned(pdf_path, i)
                    cleaned_texts[i] = page_txt
                    helpful_hits = _pattern_hits(rule, "helpful_cues", rule["helpful_cues"], i, cleaned_texts, pdf_path)
            if helpful_hits < rule.get("min_helpful", 0) and require_from_prev and i > 0:
                prev_txt = cleaned_texts[i - 1]
                if rule_name in FORCE_OCR_RANGE_RULES:
                    if _maybe_force_full_page_ocr(i - 1, "range helpful previous", prev_txt, True, rule_name):
                        prev_txt = _page_cleaned(pdf_path, i - 1)
                        cleaned_texts[i - 1] = prev_txt
                helpful_hits_prev = _pattern_hits(rule, "helpful_cues", rule["helpful_cues"], i - 1, cleaned_texts, pdf_path)
                if helpful_hits_prev >= rule.get("min_helpful", 0):
                    helpful_hits = helpful_hits_prev
            if helpful_hits < rule.get("min_helpful", 0):
                if debug_rule:
                    print(f"[Debug] '{rule_name}' failed: helpful_cues ({helpful_hits}) < min_helpful")
                return False

    # Must hit at least one start.any_cues (if provided)
    if "any_cues" in s:
        start_hits = _pattern_hits(rule, "start.any_cues", s["any_cues"], i, cleaned_texts, pdf_path)
        if start_hits == 0 and rule_name in FORCE_OCR_RANGE_RULES:
            if _maybe_force_full_page_ocr(i, "range start cue missing", page_txt, True, rule_name):
                page_txt = _page_cleaned(pdf_path, i)
                cleaned_texts[i] = page_txt
                start_hits = _pattern_hits(rule, "start.any_cues", s["any_cues"], i, cleaned_texts, pdf_path)
        if start_hits == 0:
            if debug_rule:
                print(f"[Debug] '{rule_name}' failed: start.any_cues not found")
                print(f"  Text sample: {page_txt[:200]}...")
            return False
        if debug_rule:
            print(f"[Debug] '{rule_name}' start.any_cues hits: {start_hits}")

    # Optional lookahead requirement
    if "next_page_hits" in s and (i + 1) < len(cleaned_texts):
        lookahead_hits = _hits(cleaned_texts[i + 1], s["next_page_hits"])
        if lookahead_hits < s.get("min_hits_next", 1):
            if debug_rule:
                print(f"[Debug] '{rule_name}' failed: next_page_hits {lookahead_hits} < required")
            return False

    if debug_rule:
        print(f"[Debug] '{rule_name}' MATCHED start page {i+1}")
    return True

def signature_end_index(cleaned_texts, start_idx):
    """
    Special end rules for e-sign packages.
    Returns (end_index, hit_ok)
    """
    n = len(cleaned_texts)
    start_page = cleaned_texts[start_idx]

    if re.search(r"\bDOCUMENT\s+COMPLETION\s+CERTIFICATE\b", start_page):
        last = None
        for j in range(start_idx, n):
            if re.search(r"\bDOCUMENT\s+HISTORY\b", cleaned_texts[j]):
                last = j
        return (last, True) if last is not None else (n-1, False)

    if re.search(r"\bDEALER\s+POLICY\s+BIND\s+PACKAGE\b", start_page):
        last = None
        for j in range(start_idx, n):
            if (re.search(r"\bAGREEMENT\s+COMPLETED\b", cleaned_texts[j])
                or re.search(r"\bADOBE\s+ACROBAT\s+SIGN\b", cleaned_texts[j])):
                last = j
        return (last, True) if last is not None else (n-1, False)

    return n-1, False

# ------------------ Helpers for table/starts and end positioning ------------------
def _looks_like_table(page_idx: int) -> bool:
    """
    Heuristic for 'table-like' pages using PyMuPDF:
      - axis-aligned lines / rectangles
      - dense text rows
      - many small blocks
    """
    if _DOC is None:
        return False
    try:
        page = _DOC[page_idx]

        # 1) Vector drawings
        segs = 0
        rects = 0
        for d in (page.get_drawings() or []):
            for it in d.get("items", []):
                kind = it[0]
                if kind == "l":  # line
                    (x0, y0, x1, y1) = it[1]
                    if abs(x0 - x1) < 1 or abs(y0 - y1) < 1:
                        segs += 1
                elif kind == "re":  # rectangle
                    rects += 1

        # 2) Word rows density
        words = page.get_text("words") or []
        row_buckets = {}
        for w in words:
            y0 = int(round(w[1] / 3.0)) * 3
            row_buckets[y0] = row_buckets.get(y0, 0) + 1
        dense_rows = sum(1 for cnt in row_buckets.values() if cnt >= 5)

        # 3) Many small blocks
        blocks = page.get_text("blocks") or []
        small_blocks = 0
        for b in blocks:
            x0, y0, x1, y1 = b[:4]
            w = max(0, x1 - x0)
            h = max(0, y1 - y0)
            area = w * h
            if 1500 <= area <= 120000:
                small_blocks += 1

        if segs >= 8: return True
        if rects >= 2: return True
        if dense_rows >= 8: return True
        if small_blocks >= 18: return True
        return False
    except Exception:
        return False

def _first_match_pos(text, patterns):
    """Earliest match position across patterns (in cleaned text)."""
    pos = None
    for p in patterns or []:
        m = p.search(text)
        if m:
            s = m.start()
            pos = s if pos is None or s < pos else pos
    return pos

def _collect_all_range_start_pats(rules):
    """Collect all compiled start.any_cues from range rules."""
    pats = []
    for r in rules:
        if r.get("scope") == "range":
            s = r.get("start", {})
            if isinstance(s.get("any_cues"), list):
                pats.extend(s["any_cues"])
    return pats

# ------------------ End detection ------------------
def find_range_end(cleaned_texts, start_idx, rule: dict,
                   all_range_start_pats=None,
                   self_start_pats=None,
                   pdf_path=None):
    """
    Returns (end_index, hit_ok)

    New options in rule["end"]:
      - stop_before_new_start: bool (default False)
        If True, end at the page before the next page that looks like
        a *different* range start (any start.any_cues not belonging to this rule).
      - near_bottom_frac: float in (0,1), require the end cue to appear in the
        last fraction of the page (e.g., 0.40 = bottom 40%).
      - max_pages: int > 0, cap search to at most start_idx + max_pages - 1.
      - mode: "signature_rules" | "next_table_page"
      - first_cue: list[regex] (compiled)
      - fallback_to_end: bool (default True)
    """
    n = len(cleaned_texts)
    e = rule.get("end", {})
    mode = e.get("mode")

    if mode == "signature_rules":
        end_idx, hit_ok = signature_end_index(cleaned_texts, start_idx)
        return end_idx, hit_ok, None

    if mode == "next_table_page":
        j = start_idx + 1
        if j < n and _looks_like_table(j):
            return j, True, None
        scan_upto = min(start_idx + 2, n - 1)
        for k in range(j + 1, scan_upto + 1):
            if _CANCELLED:
                break
            if _looks_like_table(k):
                return k, True, None
        if start_idx + 1 < n:
            return start_idx + 1, True, None
        return n - 1, False, None

    # -------- Normal end-by-cue with extras --------
    first_cue = e.get("first_cue", None)
    stop_before_new_start = bool(e.get("stop_before_new_start", False))
    near_bottom_frac = e.get("near_bottom_frac", None)
    max_pages = e.get("max_pages", None)

    # compute scan window
    scan_limit = n - 1
    if isinstance(max_pages, int) and max_pages > 0:
        scan_limit = min(scan_limit, start_idx + max_pages - 1)

    # if we're stopping before *other* starts, we need global start pats minus ours
    other_start_pats = []
    if stop_before_new_start and isinstance(all_range_start_pats, list):
        my = set(self_start_pats or [])
        other_start_pats = [p for p in all_range_start_pats if p not in my]

    # Debug logging for Dealer Application and MI SSA
    debug_rule = rule.get("name") in ["Dealer Application", "SSA MI"]
    if debug_rule:
        print(f"\n[EndCue Debug] Searching for '{rule.get('name')}' end cue from page {start_idx+2} to {scan_limit+1} (start page {start_idx+1})")
    
    # Start searching from the page AFTER the start page to avoid matching on the same page
    # But ensure we have at least one page to check
    search_start = start_idx + 1
    if search_start > scan_limit:
        # If we can't search beyond the start page, fall back to max_pages limit
        if e.get("fallback_to_end", True):
            return scan_limit, False, None
        return start_idx, False, None
    
    rule_name = rule.get("name")
    if rule_name in _PREBATCH_RULES:
        _prebatch_rule_pages(rule_name, cleaned_texts, start_idx, pdf_path)
    if rule_name:
        _maybe_save_template(rule_name, start_idx)
    self_start_pats = rule.get("start", {}).get("any_cues") or []

    is_dealer_app = rule.get("name") == "Dealer Application"
    for j in range(search_start, scan_limit + 1):
        if _CANCELLED:
            break
        # 1) early boundary: next page looks like a *different* start
        if stop_before_new_start and j > start_idx and other_start_pats:
            if _hits(cleaned_texts[j], other_start_pats) > 0:
                return j - 1, True, None

        # 2) Force OCR on potential end pages if they don't have end cues and text seems incomplete
        page_text = cleaned_texts[j]
        
        # For Dealer Application, force OCR on scanned pages regardless of _ALLOW_OCR
        # Check pages near the end (start_idx + 3 onwards) or any page with very little text
        should_check_ocr = False
        if first_cue and (is_dealer_app or _ALLOW_OCR):
            # For Dealer Application, check all pages in range if they have very little text
            # For other rules, only check pages near expected end
            if is_dealer_app:
                should_check_ocr = True  # Check all pages for scanned PDFs
            elif j >= start_idx + 4:
                should_check_ocr = True  # Only check near end for other rules
        
        if should_check_ocr:
            needs_ocr = False
            ocr_reason = ""
            
            # Check if page has very little text (likely scanned image)
            if len(page_text) < 500 and _hits(page_text, first_cue) == 0:
                needs_ocr = True
                ocr_reason = "very little text (likely scanned)"
            # Or if page has some text but no end cues, and it's likely the end page
            elif len(page_text) > 200 and len(page_text) < 2000 and _hits(page_text, first_cue) == 0:
                # Check if it looks like a signature page (has dates/times but missing form text)
                has_dates = re.search(r'\d{1,2}/\d{1,2}/\d{4}', page_text) or re.search(r'\d{1,2}/\d{2}/\d{4}', page_text)
                has_times = 'PM' in page_text or 'AM' in page_text or 'UTC' in page_text
                if has_dates and has_times and not any(kw in page_text for kw in ["BROKER", "SIGNATURE", "COMPLETION", "INDICATE", "INTERESTS", "APPLICANT", "CONSENT"]):
                    needs_ocr = True
                    ocr_reason = "has dates/times but missing form text"
            
            if needs_ocr:
                # For Dealer Application on scanned pages, OCR the full page for better results
                if is_dealer_app and len(page_text) < 500:
                    already_forced = (j, "full") in _FORCED_OCR_CACHE
                    if debug_rule and not already_forced:
                        print(f"[EndCue Debug] Forcing full-page OCR on page {j+1} ({ocr_reason})")
                    if not already_forced:
                        try:
                            _force_full_page_ocr(j, ocr_reason or "dealer end cue assist",
                                                 rule_name=rule_name, seed_text=page_text)
                        except Exception as e:
                            if debug_rule:
                                print(f"[EndCue Debug] OCR error on page {j+1}: {e}")
                else:
                    if debug_rule:
                        print(f"[EndCue Debug] Forcing OCR on page {j+1} ({ocr_reason})")
                    try:
                        _ocr_page_region_into_cache(j, region="bottom_strip", pct=0.6, dpi=300, binarize=True)
                    except Exception as e:
                        if debug_rule:
                            print(f"[EndCue Debug] OCR error on page {j+1}: {e}")
                
                # Re-extract cleaned text after OCR
                page_text = _page_cleaned(pdf_path, j)
                cleaned_texts[j] = page_text

        # 3) main end cue(s)
        if first_cue:
            hit = None
            matched_pattern = _pattern_first_match(rule, "end.first_cue", first_cue, j, cleaned_texts, pdf_path)
            if matched_pattern:
                hit = True
                if near_bottom_frac is not None:
                    frac = max(0.0, min(0.99, float(near_bottom_frac)))
                    mpos = _first_match_pos(page_text, [matched_pattern])
                    if mpos is None or mpos < int(len(page_text) * (1.0 - frac)):
                        hit = None
                        matched_pattern = None
            
            # Debug: show what's on each page
            if debug_rule:
                text_sample = page_text[:150] if len(page_text) > 150 else page_text
                has_keywords = any(kw in page_text for kw in ["BROKER", "SIGNATURE", "COMPLETION", "INDICATE", "INTERESTS", "APPLICANT", "CONSENT", "ADVISORY", "WARRANTIES"])
                print(f"[EndCue Debug] Page {j+1}: {len(page_text)} chars, has_keywords={has_keywords}, hit={hit}")
                if has_keywords or len(page_text) > 50:
                    print(f"  Text sample: {text_sample}...")

            if hit:
                # Store which pattern matched for debugging
                if matched_pattern:
                    _dbg(f"[EndCue] Page {j+1} matched pattern: {matched_pattern.pattern}")
                return j, True, matched_pattern

    # Fallbacks
    if e.get("fallback_to_end", True):
        return scan_limit, False, None
    return start_idx, False, None

# ------------------ Saving ------------------
INVALID_CHARS = r'\\/:*?"<>|'
def sanitize_filename(name):
    return "".join(("-" if ch in INVALID_CHARS else ch) for ch in name).rstrip(" .") or "document"

def ensure_pdf_ext(name: str) -> str:
    name = (name or "").strip()
    return name if name.lower().endswith(".pdf") else (name + ".pdf")

def _tag_if_missed(filename: str, missed: bool) -> str:
    if not missed: return filename
    base, ext = os.path.splitext(filename)
    return f"{base} - missed end cue{ext or ''}"

def unique_path(directory, filename):
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base} ({n}){ext}")
        n += 1
    return candidate

def ensure_split_folder(pdf_path):
    binder = os.path.splitext(os.path.basename(pdf_path))[0]
    folder = os.path.join(DEFAULT_OUTPUT_DIR, f"{binder}_split")
    os.makedirs(folder, exist_ok=True)
    return folder

def save_range(pdf_path, start_idx, end_idx, out_name):
    folder = ensure_split_folder(pdf_path)
    out_name = out_name.replace("YY", datetime.now().strftime("%y"))
    out_name = ensure_pdf_ext(out_name)
    out_path = unique_path(folder, out_name)
    new_doc = fitz.open()
    new_doc.insert_pdf(_DOC, from_page=start_idx, to_page=end_idx)
    new_doc.save(out_path, deflate=False, garbage=0, clean=False)
    new_doc.close()
    return out_path

def save_single(pdf_path, page_index, out_name):
    folder = ensure_split_folder(pdf_path)
    out_name = out_name.replace("YY", datetime.now().strftime("%y"))
    out_name = ensure_pdf_ext(out_name)
    out_path = unique_path(folder, out_name)
    new_doc = fitz.open()
    new_doc.insert_pdf(_DOC, from_page=page_index, to_page=page_index)
    new_doc.save(out_path, deflate=False, garbage=0, clean=False)
    new_doc.close()
    return out_path

def save_dealer_with_location(pdf_path, start_idx, end_idx, location_idx, out_name):
    folder = ensure_split_folder(pdf_path)
    out_name = out_name.replace("YY", datetime.now().strftime("%y"))
    out_name = ensure_pdf_ext(out_name)
    out_path = unique_path(folder, out_name)
    new_doc = fitz.open()
    first_end = min(start_idx + 3, end_idx)
    new_doc.insert_pdf(_DOC, from_page=start_idx, to_page=first_end)
    new_doc.insert_pdf(_DOC, from_page=location_idx, to_page=location_idx)
    tail_start = first_end + 1
    if tail_start <= end_idx:
        new_doc.insert_pdf(_DOC, from_page=tail_start, to_page=end_idx)
    new_doc.save(out_path, deflate=False, garbage=0, clean=False)
    new_doc.close()
    return out_path

def delete_paths_and_maybe_folder(pdf_path, paths):
    for p in list(paths):
        try:
            if os.path.isfile(p): os.remove(p)
        except Exception: pass
    try:
        binder = os.path.splitext(os.path.basename(pdf_path))[0]
        folder = os.path.join(DEFAULT_OUTPUT_DIR, f"{binder}_split")
        if os.path.isdir(folder) and not os.listdir(folder):
            os.rmdir(folder)
    except Exception: pass

# ------------------ Preview & Name ------------------
class PreviewFlow:
    """
    For items with prompt==true.
    kind="single" -> preview that page and save that page.
    kind="range"  -> preview 'preview_page' and save start..end (inclusive).
    """
    BASE_W, BASE_H = 900, 1150
    SCALE = 0.66

    def __init__(self, root_tk, pdf_path, queue):
        self.root = root_tk
        self.pdf_path = pdf_path
        self.queue = list(queue)
        self.index = 0
        self.saved_count = 0
        self._Image = Image
        self._ImageTk = ImageTk
        self._img_tk = None
        self._saved_paths = []
        self.cancelled = False

        self._owns_doc = False
        try:
            self._doc = _DOC
        except Exception:
            self._doc = None
        if self._doc is None:
            self._doc = fitz.open(self.pdf_path)
            self._owns_doc = True

        self.top = tk.Toplevel(self.root)
        self.top.title("Preview & Name")
        self.top.transient(self.root)
        self.top.grab_set()
        self.top.protocol("WM_DELETE_WINDOW", self._confirm_cancel)
        self._root_close_orig = self.root.protocol("WM_DELETE_WINDOW", self._on_root_close_during_preview)

        self.canvas = tk.Canvas(self.top, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)

        controls = ttk.Frame(self.top)
        controls.pack(side="bottom", fill="x", padx=10, pady=10)

        ttk.Label(controls, text="Filename:").pack(side="left")
        self.name_var = tk.StringVar()
        self.entry = ttk.Entry(controls, textvariable=self.name_var, width=68)
        self.entry.pack(side="left", padx=8)

        self.btn_fit = ttk.Button(controls, text="Fit", width=7, command=self.on_fit)
        self.btn_zoom_out = ttk.Button(controls, text="Zoom −", width=8, command=self.on_zoom_out)
        self.btn_zoom_in = ttk.Button(controls, text="Zoom +", width=8, command=self.on_zoom_in)
        self.btn_fit.pack(side="left", padx=(10,4))
        self.btn_zoom_out.pack(side="left", padx=4)
        self.btn_zoom_in.pack(side="left", padx=4)

        self.btn_save = ttk.Button(controls, text="Save & Next", command=self.on_save)
        self.btn_skip = ttk.Button(controls, text="Skip", command=self.on_skip)
        self.btn_cancel = ttk.Button(controls, text="Cancel", command=self._confirm_cancel)
        self.btn_save.pack(side="right", padx=4)
        self.btn_skip.pack(side="right", padx=4)
        self.btn_cancel.pack(side="right", padx=4)

        self.base_zoom = 2.0
        self.view_scale = 1.5
        self._last_render_size = (0,0)

        self.top.bind("<Control-plus>", lambda e: self.on_zoom_in())
        self.top.bind("<Control-minus>", lambda e: self.on_zoom_out())
        self.top.bind("<Control-equal>", lambda e: self.on_zoom_in())
        self.top.bind("<Control-0>", lambda e: self.on_fit())
        self.top.bind("<Return>", lambda e: self.on_save())
        self.top.bind("<Escape>", lambda e: self._confirm_cancel())
        self.top.bind("<Configure>", lambda e: self._maybe_rerender())
        self.top.bind("<Control-MouseWheel>", self.on_ctrl_scroll)
        self.top.bind("<Control-Button-4>", self.on_ctrl_scroll_linux)
        self.top.bind("<Control-Button-5>", self.on_ctrl_scroll_linux)

        scaled_w = int(self.BASE_W * self.SCALE * 1.25)
        scaled_h = int(self.BASE_H * self.SCALE)
        self._apply_fixed_geometry(scaled_w, scaled_h, 120, 100)

        self.show_current()

    def _apply_fixed_geometry(self, w=900, h=1150, x=80, y=80):
        try:
            self.top.update_idletasks()
            self.top.minsize(w, h)
            self.top.geometry(f"{w}x{h}+{x}+{y}")
            self.top.after(50, lambda: self.top.geometry(f"{w}x{h}+{x}+{y}"))
            self.top.after(60, self._maybe_rerender)
        except Exception:
            pass

    def _on_root_close_during_preview(self):
        if messagebox.askyesno("Exit without saving?", "A preview is open. Exit now and discard any files saved in this run?"):
            self.cancelled = True
            self._discard_saved_preview_files()
            try: self.top.grab_release()
            except Exception: pass
            self.top.destroy()
            try: self.root.protocol("WM_DELETE_WINDOW", self._root_close_orig)
            except Exception: pass
            if callable(self._root_close_orig):
                self._root_close_orig()
            else:
                self.root.destroy()
        else:
            return

    def _ensure_split_folder(self):
        binder = os.path.splitext(os.path.basename(self.pdf_path))[0]
        folder = os.path.join(DEFAULT_OUTPUT_DIR, f"{binder}_split")
        os.makedirs(folder, exist_ok=True)
        return folder

    def _render_page_image(self, page_index):
        page = self._doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(self.base_zoom, self.base_zoom), alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        cw, ch = max(1, self.top.winfo_width()-40), max(1, self.top.winfo_height()-170)
        max_w, max_h = int(cw * self.view_scale), int(ch * self.view_scale)
        w, h = img.size
        if w <= 0 or h <= 0 or max_w <= 0 or max_h <= 0:
            return None
        scale = min(max_w / w, max_h / h, 1.0)
        img = img.resize((max(1,int(w*scale)), max(1,int(h*scale))), Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _maybe_rerender(self):
        sz = (self.top.winfo_width(), self.top.winfo_height())
        if sz != self._last_render_size:
            self._last_render_size = sz
            self._draw_current_image()

    def show_current(self):
        if self.index >= len(self.queue):
            self.finish(cancelled=False)
            return
        item = self.queue[self.index]
        suggested = item["prefix"].replace("YY", datetime.now().strftime("%y"))
        self.name_var.set(sanitize_filename(suggested))
        self.entry.focus_set()
        self.entry.icursor(tk.END)
        self.btn_save.configure(text="Finish" if self.index == len(self.queue)-1 else "Save & Next")
        self._draw_current_image()

    def _draw_current_image(self):
        if self.index >= len(self.queue): return
        item = self.queue[self.index]
        page_idx = item["preview_page"] if item.get("kind") == "range" else item["page"]
        _dbg(f"[Preview] showing page {page_idx+1}")
        img = self._render_page_image(page_idx)
        if img is None: return
        self._img_tk = img
        self.canvas.delete("all")
        self.canvas.create_image(10, 10, image=self._img_tk, anchor="nw")

    def on_zoom_in(self):
        self.view_scale = min(self.view_scale * 1.15, 4.0)
        self._draw_current_image()

    def on_zoom_out(self):
        self.view_scale = max(self.view_scale / 1.15, 0.5)
        self._draw_current_image()

    def on_fit(self):
        self.view_scale = 1.0
        self._draw_current_image()

    def on_ctrl_scroll(self, event):
        if event.delta > 0: self.on_zoom_in()
        else: self.on_zoom_out()

    def on_ctrl_scroll_linux(self, event):
        if event.num == 4: self.on_zoom_in()
        elif event.num == 5: self.on_zoom_out()

    def on_save(self):
        item = self.queue[self.index]
        name = (self.name_var.get() or "").strip()
        if not name:
            messagebox.showerror("Filename required", "Please enter a filename.")
            return
        name = ensure_pdf_ext(name)
        out_path = unique_path(self._ensure_split_folder(), name)

        new_doc = fitz.open()
        try:
            if item.get("kind") == "range":
                new_doc.insert_pdf(self._doc, from_page=item["start"], to_page=item["end"])
            else:
                new_doc.insert_pdf(self._doc, from_page=item["page"], to_page=item["page"])
            new_doc.save(out_path, deflate=False, garbage=0, clean=False)
            self._saved_paths.append(out_path)
            self.saved_count += 1
        except Exception as e:
            messagebox.showerror("Save error", str(e))
        finally:
            try: new_doc.close()
            except Exception: pass

        self.index += 1
        self.show_current()

    def _confirm_cancel(self):
        if messagebox.askyesno("Exit without saving?", "Exit preview now and discard any files saved in this preview?"):
            self.cancelled = True
            self._discard_saved_preview_files()
            self.finish(cancelled=True)

    def _discard_saved_preview_files(self):
        delete_paths_and_maybe_folder(self.pdf_path, self._saved_paths)
        self._saved_paths.clear()

    def on_skip(self):
        self.index += 1
        self.show_current()

    def finish(self, cancelled: bool):
        try:
            if hasattr(self, "_root_close_orig"):
                self.root.protocol("WM_DELETE_WINDOW", self._root_close_orig)
        except Exception:
            pass
        try: self.top.grab_release()
        except Exception: pass
        self.top.destroy()
        if self._owns_doc and self._doc is not None:
            try: self._doc.close()
            except Exception: pass
        if cancelled:
            messagebox.showinfo("Preview", "Cancelled. No files were saved from this preview.")
        else:
            if self.saved_count > 0:
                try:
                    binder = os.path.splitext(os.path.basename(self.pdf_path))[0]
                    os.startfile(os.path.join(DEFAULT_OUTPUT_DIR, f"{binder}_split"))
                except Exception:
                    pass
            messagebox.showinfo("Preview", f"Finished. Saved {self.saved_count} file(s).")

# ------------------ Opportunistic OCR ------------------
def _ocr_page_into_cache(i: int, dpi: int = None):
    _ocr_page_region_into_cache(i, region="full", pct=0.9, dpi=dpi, binarize=True)

def _opportunistic_ocr_suspects(max_pages: int = 12, force_full: bool = False):
    suspects = _suspect_pages()
    done = 0
    for i in suspects:
        if _CANCELLED:
            break
        if len(_TEXT_CACHE_RAW.get(i, "")) < 10:
            if force_full:
                _force_full_page_ocr(i, "initial batch")
            else:
                _ocr_page_into_cache(i)
            done += 1
            if max_pages is not None and done >= max_pages:
                break

# ------------------ Dispatcher ------------------
def apply_rules_collect(pdf_path, rules, session_paths, pump=None, progress_callback=None):
    """
    Returns: (auto_saved_count, prompt_items, lines)
      prompt_items:
        kind="single" -> {"page": int, "prefix": str, "ext": ".pdf"}
        kind="range"  -> {"start": int, "end": int, "preview_page": int, "prefix": str, "ext": ".pdf"}
    progress_callback: Optional function(percent) to update progress (0-100)
    """
    n = len(_DOC)
    suspect_max = None if _ALLOW_OCR else 12
    _opportunistic_ocr_suspects(max_pages=suspect_max, force_full=_ALLOW_OCR)
    cleaned = [_page_cleaned(pdf_path, i) for i in range(n)]
    if progress_callback:
        progress_callback(10)  # Initial text extraction done
    taken = set()
    ignored, ignore_notes = _detect_nav_sav_junk(cleaned)
    taken.update(ignored)
    auto_saved = 0
    lines = list(ignore_notes)
    prompt_items = []
    dealer_matches = []
    location_matches = []

    match_stats = {"range": [], "single": []}
    
    # Estimate: 40% for range rules, 30% for single rules, 20% for saving
    range_rules = [r for r in rules if r.get("scope") == "range"]
    single_rules = [r for r in rules if r.get("scope") == "single_page"]
    total_rules = len(range_rules) + len(single_rules)

    # collect all range-start regexes (compiled)
    all_range_start_pats = _collect_all_range_start_pats(rules)

    # RANGE rules
    range_rule_idx = 0
    for rule in range_rules:
        if _CANCELLED:
            break
        start_time = perf_counter()
        i = 0
        matched_pages = 0
        base_progress = 10 + (40 * range_rule_idx // max(1, len(range_rules)))
        while i < n:
            if _CANCELLED:
                break
            if pump:
                pump()
            if progress_callback and i % max(1, n // 20) == 0:
                page_progress = (i / n) * (40 / max(1, len(range_rules)))
                progress_callback(base_progress + page_progress)
            if i in taken:
                i += 1
                continue
            if match_range_start(cleaned, i, rule, pdf_path):
                matched_pages += 1
                start = i
                start_cfg = rule.get("start", {})
                hint_key = (rule.get("name", ""), i)
                fallback_hint_used = False
                if _RANGE_LOOKBACK_HINTS.pop(hint_key, False) and start > 0:
                    start -= 1
                    fallback_hint_used = True
                if not fallback_hint_used and start_cfg.get("lookback_header") and start > 0:
                    any_cues = start_cfg.get("any_cues")
                    fallback_cues = start_cfg.get("fallback_cues")
                    fallback_hits_current = _hits(cleaned[start], fallback_cues) if fallback_cues else 0
                    prev_text = cleaned[start - 1]
                    prev_hits = _hits(prev_text, any_cues) if any_cues else 0

                    if prev_hits == 0 and rule.get("name") in FORCE_OCR_RANGE_RULES:
                        prev_seed = cleaned[start - 1] if start - 1 < len(cleaned) else ""
                        _force_full_page_ocr(start - 1, "range lookback header",
                                             rule_name=rule_name, seed_text=prev_seed)
                        cleaned[start - 1] = _page_cleaned(pdf_path, start - 1)
                        prev_text = cleaned[start - 1]
                        prev_hits = _hits(prev_text, any_cues) if any_cues else 0

                    lookback_forbid = start_cfg.get("lookback_prev_forbid")
                    if lookback_forbid and _hits(prev_text, lookback_forbid) > 0:
                        prev_hits = 0

                    fallback_prev_hits = 0
                    if prev_hits == 0 and start_cfg.get("fallback_to_previous") and fallback_cues and fallback_hits_current > 0:
                        fallback_prev_hits = _hits(prev_text, fallback_cues)
                        if fallback_prev_hits == 0 and rule.get("name") in FORCE_OCR_RANGE_RULES:
                            prev_seed = cleaned[start - 1] if start - 1 < len(cleaned) else ""
                            _force_full_page_ocr(start - 1, "range fallback header",
                                                 rule_name=rule_name, seed_text=prev_seed)
                            cleaned[start - 1] = _page_cleaned(pdf_path, start - 1)
                            prev_text = cleaned[start - 1]
                            fallback_prev_hits = _hits(prev_text, fallback_cues)
                        if lookback_forbid and _hits(prev_text, lookback_forbid) > 0:
                            fallback_prev_hits = 0

                    if prev_hits > 0 or fallback_prev_hits > 0:
                        start -= 1

                # pass our starts + all starts into end detection
                rule_name = rule.get("name")
                if rule_name in _PREBATCH_RULES:
                    _prebatch_rule_pages(rule_name, cleaned, start, pdf_path)
                if rule_name:
                    _maybe_save_template(rule_name, start)
                self_start_pats = rule.get("start", {}).get("any_cues") or []
                end_idx, hit_ok, matched_pattern = find_range_end(
                    cleaned, start, rule,
                    all_range_start_pats=all_range_start_pats,
                    self_start_pats=self_start_pats,
                    pdf_path=pdf_path
                )
                
                # Log which end cue matched
                if matched_pattern:
                    pattern_str = matched_pattern.pattern
                    # Extract a readable portion of the pattern for display
                    readable = pattern_str.replace("(?s)", "").replace("\\b", "").replace("\\s+", " ").replace(".*?", "...").replace("\\", "")[:80]
                    # Identify which type of cue it was
                    if "BROKER" in readable or "SIGNATURE" in readable:
                        cue_type = "Main signature cue"
                    elif "INDICATE" in readable or "INTERESTS" in readable:
                        cue_type = "Helper cue: INDICATE INTERESTS"
                    elif "APPLICANT" in readable or "CONSENT" in readable:
                        cue_type = "Helper cue: APPLICANT CONSENT"
                    else:
                        cue_type = "Other cue"
                    _dbg(f"[EndCue] '{rule.get('name')}' matched {cue_type}: {readable}")
                    print(f"[EndCue] '{rule.get('name')}' matched {cue_type}: {readable}")  # Always print for testing
                else:
                    # Debug: if no match and we're looking for Dealer Application, show what text was found
                    if rule.get("name") == "Dealer Application" and not hit_ok:
                        print(f"\n[EndCue Debug] '{rule.get('name')}' did not match any end cue on page {end_idx+1}")
                        if end_idx < len(cleaned):
                            full_text = cleaned[end_idx]
                            print(f"[EndCue Debug] Full page {end_idx+1} text ({len(full_text)} chars): {full_text}")
                            # Also check each page in the range
                            print(f"[EndCue Debug] Searching pages {start+1} to {end_idx+1}")
                            for page_num in range(start, min(end_idx + 1, len(cleaned))):
                                page_text = cleaned[page_num]
                                if any("BROKER" in page_text or "SIGNATURE" in page_text or "COMPLETION" in page_text or 
                                       "INDICATE" in page_text or "INTERESTS" in page_text or 
                                       "APPLICANT" in page_text or "CONSENT" in page_text for _ in [1]):
                                    print(f"[EndCue Debug] Page {page_num+1} contains relevant keywords: {page_text[:300] if len(page_text) > 300 else page_text}")

                base_name = rule["output"]["filename"]
                out_name = _tag_if_missed(base_name, missed=(not hit_ok))
                needs_prompt = bool(rule.get("output", {}).get("prompt"))

                rule_name = rule.get("name", "")
                if rule_name == "Dealer Application" and not needs_prompt:
                    dealer_matches.append({
                        "start": start,
                        "end": end_idx,
                        "prefix": out_name,
                        "hit_ok": hit_ok
                    })
                    taken.update(range(start, end_idx + 1))
                    i = end_idx + 1
                    continue

                # preview page selection
                rel_index = rule.get("output", {}).get("preview_index", None)
                if rel_index is not None:
                    try: rel_index = int(rel_index)
                    except Exception: rel_index = 0
                offset_val = rule.get("output", {}).get("preview_offset", 0)
                try: offset_val = int(offset_val)
                except Exception: offset_val = 0

                if needs_prompt:
                    if rel_index is not None:
                        preview_page = max(start, min(end_idx, start + max(0, rel_index)))
                    else:
                        preview_page = max(start, min(end_idx, start + max(0, offset_val)))

                    _dbg(f"[Collect] RANGE '{rule.get('name')}' start={start+1} end={end_idx+1} preview={preview_page+1} hit_ok={hit_ok}")

                    prompt_items.append({
                        "kind": "range",
                        "start": start,
                        "end": end_idx,
                        "preview_page": preview_page,
                        "prefix": out_name,
                        "ext": ".pdf"
                    })
                    taken.update(range(start, end_idx + 1))
                    lines.append(f"{rule['name']} {start+1}-{end_idx+1} (preview){'' if hit_ok else ' (missed end cue)'}")
                else:
                    saved_path = save_range(pdf_path, start, end_idx, out_name)
                    session_paths.append(saved_path)
                    taken.update(range(start, end_idx + 1))
                    auto_saved += 1
                    lines.append(f"{rule['name']} {start+1}-{end_idx+1}{'' if hit_ok else ' (missed end cue)'}")
                i = end_idx + 1
                continue
            i += 1
        match_stats["range"].append((rule.get("name", "?"), matched_pages, perf_counter() - start_time))
        range_rule_idx += 1
        if progress_callback:
            progress_callback(min(50, 10 + int(40 * range_rule_idx / max(1, len(range_rules)))))

    # SINGLE-page rules
    single_rule_idx = 0
    for rule in single_rules:
        if _CANCELLED:
            break
        start_time = perf_counter()
        matched_pages = 0
        needs_prompt = bool(rule.get("output", {}).get("prompt"))
        prefix = rule.get("output", {}).get("filename", "YY Document")
        base_progress = 50 + (30 * single_rule_idx // max(1, len(single_rules)))
        for i in range(n):
            if _CANCELLED:
                break
            if pump:
                pump()
            if progress_callback and i % max(1, n // 20) == 0:
                page_progress = (i / n) * (30 / max(1, len(single_rules)))
                progress_callback(base_progress + page_progress)
            if i in taken:
                continue
            if match_single_page_rule(cleaned, i, rule, pdf_path):
                matched_pages += 1
                rule_name = rule.get("name", "")
                if rule_name == "Location Page DA" and not needs_prompt:
                    location_matches.append({
                        "page": i,
                        "prefix": prefix
                    })
                    taken.add(i)
                    continue
                if needs_prompt:
                    _dbg(f"[Collect] SINGLE '{rule.get('name')}' page={i+1}")
                    prompt_items.append({"kind": "single", "page": i, "prefix": prefix, "ext": ".pdf"})
                    taken.add(i)
                    lines.append(f"{rule['name']} {i+1} (preview)")
                else:
                    saved_path = save_single(pdf_path, i, prefix)
                    session_paths.append(saved_path)
                    taken.add(i)
                    auto_saved += 1
                    lines.append(f"{rule['name']} {i+1}")
        match_stats["single"].append((rule.get("name", "?"), matched_pages, perf_counter() - start_time))
        single_rule_idx += 1
        if progress_callback:
            progress_callback(min(80, 50 + int(30 * single_rule_idx / max(1, len(single_rules)))))

    if progress_callback:
        progress_callback(85)  # Rule matching done, starting post-processing

    # Post-processing for Dealer Application and Location Page DA
    for match in dealer_matches:
        location_entry = location_matches.pop(0) if location_matches else None
        start = match["start"]
        end_idx = match["end"]
        prefix = match["prefix"]
        hit_ok = match["hit_ok"]
        if location_entry is not None:
            merged_path = save_dealer_with_location(pdf_path, start, end_idx, location_entry["page"], prefix)
            session_paths.append(merged_path)
            auto_saved += 1
            lines.append(f"Dealer Application {start+1}-{end_idx+1} (with Location page {location_entry['page']+1})")
        else:
            saved_path = save_range(pdf_path, start, end_idx, prefix)
            session_paths.append(saved_path)
            auto_saved += 1
            lines.append(f"Dealer Application {start+1}-{end_idx+1}{'' if hit_ok else ' (missed end cue)'}")

    for loc in location_matches:
        saved_path = save_single(pdf_path, loc["page"], loc["prefix"])
        session_paths.append(saved_path)
        auto_saved += 1
        lines.append(f"Location Page DA {loc['page']+1}")

    if progress_callback:
        progress_callback(95)  # Post-processing done

    return auto_saved, prompt_items, lines, match_stats

# ------------------ Orchestration ------------------
def process_pdf(path, status_lbl, progress, parent_window=None):
    global _CANCELLED
    _CANCELLED = False
    
    if not path.lower().endswith(".pdf"):
        messagebox.showerror("Error", "Please select a valid PDF file.")
        return

    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

    try:
        rules = load_rules(RULES_PATH)
    except Exception as e:
        messagebox.showerror("Rules error", f"Failed to load rules.json:\n{e}")
        return

    run_start = perf_counter()

    allow_ocr, skip_quick, scan_stats = assess_binder_scan_profile(path)
    suspect_ratio_low = scan_stats.get("low_ratio", 0.0)
    suspect_ratio_med = scan_stats.get("med_ratio", 0.0)
    skip_reason = scan_stats.get("skip_reason")

    if DEBUG:
        _dbg(
            "[ScanProfile] allow_ocr=%s skip_quick=%s reason=%s sample=%s low=%s med=%s high=%s"
            % (
                allow_ocr,
                skip_quick,
                skip_reason,
                scan_stats.get("sample_pages"),
                scan_stats.get("low_pages"),
                scan_stats.get("med_pages"),
                scan_stats.get("high_pages"),
            )
        )

    session_paths = []
    
    # Check if cancelled before starting
    if _CANCELLED:
        return

    if skip_quick:
        if skip_reason:
            _set_status(status_lbl, "Scanning (OCR)… (skipped fast scan)")
        else:
            _set_status(status_lbl, "Scanning (OCR)…")
        _start_progress(progress, 10)
        begin_text_session(path, allow_ocr=True)
        try:
            for i in _suspect_pages():
                _ = _page_cleaned(path, i)
            auto_saved, prompt_items, lines, match_stats = apply_rules_collect(
                path, rules, session_paths,
                pump=lambda: _pump_events(status_lbl),
                progress_callback=lambda pct: _update_progress(progress, pct)
            )
        finally:
            _stop_progress(progress)
            end_text_session()
    else:
        if allow_ocr:
            _set_status(status_lbl, "Scanning (with OCR)…")
        else:
            _set_status(status_lbl, "Scanning (fast)…")
        _start_progress(progress, 10)
        begin_text_session(path, allow_ocr=allow_ocr)
        try:
            if allow_ocr:
                for i in _suspect_pages():
                    if _CANCELLED:
                        break
                    _ = _page_cleaned(path, i)
            auto_saved, prompt_items, lines, match_stats = apply_rules_collect(
                path, rules, session_paths,
                pump=lambda: _pump_events(status_lbl),
                progress_callback=lambda pct: _update_progress(progress, pct)
            )
        finally:
            _stop_progress(progress)
            end_text_session()

        if auto_saved == 0 and len(prompt_items) == 0 and allow_ocr:
            _set_status(status_lbl, "Deep scan (targeted OCR)…")
            _start_progress(progress, 10)
            begin_text_session(path, allow_ocr=True)
            try:
                for i in _suspect_pages():
                    _ = _page_cleaned(path, i)
                auto_saved, prompt_items, lines, match_stats = apply_rules_collect(
                path, rules, session_paths,
                pump=lambda: _pump_events(status_lbl),
                progress_callback=lambda pct: _update_progress(progress, pct)
            )
            finally:
                _stop_progress(progress)
                end_text_session()
    
    # Check if cancelled
    if _CANCELLED:
        _set_status(status_lbl, "Cancelled. No files saved.")
        delete_paths_and_maybe_folder(path, session_paths)
        elapsed = perf_counter() - run_start
        messagebox.showinfo("Cancelled", f"Processing was cancelled.\nElapsed: {elapsed:.2f}s")
        return

    _set_status(status_lbl, f"Auto-saved {auto_saved} file(s).")

    if prompt_items:
        begin_text_session(path, allow_ocr=False)
        try:
            root = parent_window if parent_window is not None else status_lbl.winfo_toplevel()
            flow = PreviewFlow(root, path, prompt_items)
            root.wait_window(flow.top)
        finally:
            end_text_session()

        if getattr(flow, "cancelled", False):
            delete_paths_and_maybe_folder(path, session_paths)
            elapsed = perf_counter() - run_start
            _set_status(status_lbl, f"Cancelled after {elapsed:.2f}s. No files saved.")
            return
    else:
        if auto_saved > 0:
            try:
                binder = os.path.splitext(os.path.basename(path))[0]
                os.startfile(os.path.join(DEFAULT_OUTPUT_DIR, f"{binder}_split"))
            except Exception:
                pass

    if not lines:
        lines = ["No documents detected."]

    elapsed = perf_counter() - run_start
    _set_status(status_lbl, f"Completed in {elapsed:.2f}s. Auto-saved {auto_saved} file(s).")
    stats_lines = []
    if match_stats:
        stats_lines.append("\nRange rule timings:")
        for name, hits, duration in match_stats.get("range", []):
            stats_lines.append(f"  {name}: {hits} hit(s) in {duration:.2f}s")
        stats_lines.append("\nSingle-page rule timings:")
        for name, hits, duration in match_stats.get("single", []):
            stats_lines.append(f"  {name}: {hits} hit(s) in {duration:.2f}s")
    messagebox.showinfo("Done", "\n".join(lines) + f"\nAuto-saved: {auto_saved}\nNeeds review: {len(prompt_items)}\nElapsed: {elapsed:.2f}s" + ("\n" + "\n".join(stats_lines) if stats_lines else ""))

# ------------------ UI Tab ------------------
def build_tab(parent):
    settings = _load_ui_settings()
    size_key = settings.get("window_size", "Medium")
    outer = ttk.Frame(parent)
    ttk.Label(outer, text="Binder Splitter / Extractor", font=("Segoe UI", 12, "bold")).pack(pady=(10,2))
    ttk.Label(
        outer,
        text="• Drag or choose a PDF.\n• Fast scan first; targeted OCR only if needed.\n• Preview opens for prompt docs.\n• Cancel preview = no files saved."
    ).pack()

    box = tk.Text(outer, height=6, relief="solid", borderwidth=1)
    box.insert("1.0", "Drop PDF here")
    box.configure(state="disabled")
    box.pack(fill="both", padx=16, pady=10, expand=True)

    status = ttk.Label(outer, text="Idle")
    status.pack(pady=(0,4))

    size_frame = ttk.Frame(outer)
    size_frame.pack(fill="x", padx=16, pady=(0,6))
    ttk.Label(size_frame, text="Display size:").pack(side="left")
    size_var = tk.StringVar(value=size_key)
    size_combo = ttk.Combobox(size_frame, textvariable=size_var, values=list(_SIZE_PRESETS.keys()), state="readonly", width=8)
    size_combo.pack(side="left", padx=6)
    
    # SSA Settings button
    root = outer.winfo_toplevel()
    ttk.Button(size_frame, text="SSA Settings...", command=lambda: show_ssa_settings_dialog(root), width=14).pack(side="right", padx=6)

    style = ttk.Style(outer)
    for name, preset in _SIZE_PRESETS.items():
        style.configure(_progress_style_name(name), thickness=preset["progress_thickness"])

    prog = ttk.Progressbar(outer, mode="determinate", style=_progress_style_name(size_var.get()), maximum=100)
    prog.pack(fill=None, padx=16, pady=(0,6))
    prog.configure(length=165)

    def apply_selected_size():
        selected = size_var.get()
        _apply_window_size(root, prog, selected, style)
        settings["window_size"] = selected
        _save_ui_settings(settings)

    size_combo.bind("<<ComboboxSelected>>", lambda _=None: apply_selected_size())

    _processing_thread = None
    
    def run_process_in_thread(pdf_path):
        """Run process_pdf in a background thread."""
        nonlocal _processing_thread
        if _processing_thread and _processing_thread.is_alive():
            messagebox.showwarning("Already Processing", "Please wait for current processing to complete.")
            return
        _processing_thread = threading.Thread(target=process_pdf, args=(pdf_path, status, prog, outer.winfo_toplevel()), daemon=True)
        _processing_thread.start()

    def on_drop(e):
        p = (e.data or "").strip()
        if p.startswith("{") and p.endswith("}"): p = p[1:-1]
        p = p.strip('"').strip()
        if os.path.isfile(p) and p.lower().endswith(".pdf"):
            run_process_in_thread(p)
        else:
            messagebox.showerror("Invalid File", "Please drop a valid PDF.")

    def on_click(_=None):
        p = filedialog.askopenfilename(title="Select binder PDF", filetypes=[("PDF files","*.pdf")])
        if p:
            run_process_in_thread(p)

    try:
        outer.drop_target_register(DND_FILES); outer.dnd_bind("<<Drop>>", on_drop)
        box.drop_target_register(DND_FILES);   box.dnd_bind("<<Drop>>", on_drop)
    except Exception:
        pass

    box.bind("<Button-1>", on_click)
    ttk.Button(outer, text="Choose PDF and Extract", command=on_click).pack(pady=(0,8))

    apply_selected_size()

    return outer

def _set_status(status_lbl, text):
    if status_lbl is None:
        return
    try:
        status_lbl.config(text=text)
        status_lbl.update_idletasks()
    except Exception:
        pass

def _start_progress(progress, interval=10):
    if progress is None:
        return
    try:
        progress.config(mode="determinate", maximum=100)
        progress['value'] = 0
        progress.update_idletasks()
    except Exception:
        pass

def _update_progress(progress, value):
    """Update progress bar to a value between 0-100."""
    if progress is None:
        return
    try:
        progress['value'] = min(100, max(0, value))
        progress.update_idletasks()
    except Exception:
        pass

def _stop_progress(progress):
    if progress is None:
        return
    try:
        _update_progress(progress, 100)
        progress.update_idletasks()
    except Exception:
        pass

def _pump_events(widget):
    if widget is None:
        return
    try:
        widget.update_idletasks()
        widget.update()
    except Exception:
        pass


def _apply_window_size(root, prog, size_key, style):
    preset = _SIZE_PRESETS.get(size_key, _SIZE_PRESETS["Medium"])
    w, h = preset["geometry"]
    style_name = _progress_style_name(size_key)
    try:
        style.configure(style_name, thickness=preset["progress_thickness"])
    except Exception:
        pass
    try:
        prog.configure(style=style_name)
    except Exception:
        pass
    try:
        root.geometry(f"{w}x{h}")
        root.minsize(w, h)
        root.update_idletasks()
    except Exception:
        pass


def _maybe_save_template(rule_name: str, page_idx: int):
    if not rule_name:
        return
    clean = _TEXT_CACHE_CLEAN.get(page_idx)
    if not clean:
        return
    raw = _TEXT_CACHE_RAW.get(page_idx, "")
    key = (page_idx, "full")
    entry = {
        "raw": raw or clean,
        "clean": clean,
        "dpi": int(_OCR_PAGE_DPI.get(key, 0) or 0),
        "avg_conf": _OCR_PAGE_CONF.get(key),
        "length": len(clean),
        "image_sig": _OCR_PAGE_SIG.get(key),
    }
    _template_save(rule_name, entry, clean)


def _load_ui_settings():
    try:
        with open(_UI_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {**_DEFAULT_UI_SETTINGS, **data}
    except Exception:
        pass
    return dict(_DEFAULT_UI_SETTINGS)


def _save_ui_settings(settings):
    try:
        with open(_UI_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def _get_all_ssa_rule_names():
    """Extract all SSA rule names from rules.json, sorted alphabetically."""
    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            rules = json.load(f)
        ssa_names = sorted([r.get("name", "") for r in rules if r.get("name", "").startswith("SSA ")])
        return ssa_names
    except Exception:
        return []


def _load_ssa_settings():
    """Load enabled SSA rules. Returns set of enabled SSA rule names. Default: all enabled."""
    try:
        with open(_SSA_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "enabled_ssas" in data:
                enabled = set(data.get("enabled_ssas", []))
                # Validate: only include SSAs that actually exist
                all_ssas = set(_get_all_ssa_rule_names())
                return enabled & all_ssas  # Intersection: only valid SSAs
    except Exception:
        pass
    # Default: all SSAs enabled
    return set(_get_all_ssa_rule_names())


def _save_ssa_settings(enabled_ssas):
    """Save enabled SSA rules. enabled_ssas should be a list of rule names."""
    try:
        _ensure_dir(_CACHE_ROOT)
        data = {"enabled_ssas": sorted(list(enabled_ssas))}
        with open(_SSA_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _progress_style_name(size_key: str) -> str:
    return f"Size{size_key.title()}.Horizontal.TProgressbar"


def show_ssa_settings_dialog(parent_window=None):
    """Open a dialog to select which SSA rules are enabled."""
    try:
        all_ssas = _get_all_ssa_rule_names()
        if not all_ssas:
            messagebox.showwarning("No SSAs", "No SSA rules found in rules.json.")
            return

        enabled_ssas = _load_ssa_settings()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load SSA settings: {e}")
        return

    # Create dialog window
    dialog = tk.Toplevel(parent_window if parent_window else None)
    dialog.title("SSA Rule Selection")
    dialog.geometry("420x600")
    dialog.transient(parent_window if parent_window else None)
    dialog.grab_set()
    dialog.resizable(False, False)

    # Main frame with padding
    main_frame = ttk.Frame(dialog, padding="10")
    main_frame.pack(fill="both", expand=True)

    # Title and instructions
    ttk.Label(main_frame, text="Select SSA Rules to Include", font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
    ttk.Label(main_frame, text="Unchecked rules will be excluded from extraction.", font=("Segoe UI", 9)).pack(pady=(0, 10))

    # Search box
    search_frame = ttk.Frame(main_frame)
    search_frame.pack(fill="x", pady=(0, 10))
    ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=25)
    search_entry.pack(side="left", fill="x", expand=True)

    # Checkboxes frame with scrollbar
    canvas_frame = ttk.Frame(main_frame)
    canvas_frame.pack(fill="both", expand=True, pady=(0, 10))

    scrollbar = ttk.Scrollbar(canvas_frame)
    scrollbar.pack(side="right", fill="y")

    canvas = tk.Canvas(canvas_frame, yscrollcommand=scrollbar.set, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=canvas.yview)

    checkbox_frame = ttk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=checkbox_frame, anchor="nw")

    # Store checkboxes
    checkbox_vars = {}
    checkbox_widgets = {}
    for ssa in all_ssas:
        var = tk.BooleanVar(value=(ssa in enabled_ssas))
        checkbox_vars[ssa] = var
        cb = ttk.Checkbutton(checkbox_frame, text=ssa, variable=var)
        cb.pack(anchor="w", padx=5, pady=2)
        checkbox_widgets[ssa] = cb

    def update_canvas_scroll_region(event=None):
        canvas.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        canvas_width = canvas.winfo_width()
        if canvas_width > 1:
            canvas.itemconfig(canvas_window, width=canvas_width)

    def filter_checkboxes(event=None):
        search_term = search_var.get().lower()
        visible_count = 0
        for ssa, cb in checkbox_widgets.items():
            if search_term in ssa.lower():
                cb.pack(anchor="w", padx=5, pady=2)
                visible_count += 1
            else:
                cb.pack_forget()
        update_canvas_scroll_region()

    search_var.trace("w", lambda *args: filter_checkboxes())
    checkbox_frame.bind("<Configure>", update_canvas_scroll_region)
    canvas.bind("<Configure>", lambda e: update_canvas_scroll_region())
    update_canvas_scroll_region()

    # Select All / Deselect All buttons
    select_frame = ttk.Frame(main_frame)
    select_frame.pack(fill="x", pady=(0, 10))
    ttk.Button(select_frame, text="Select All", command=lambda: [v.set(True) for v in checkbox_vars.values()]).pack(side="left", padx=5)
    ttk.Button(select_frame, text="Deselect All", command=lambda: [v.set(False) for v in checkbox_vars.values()]).pack(side="left", padx=5)
    selected_count = ttk.Label(select_frame, text=f"({len([v for v in checkbox_vars.values() if v.get()])} selected)")
    selected_count.pack(side="right", padx=5)

    def update_selected_count():
        count = len([v for v in checkbox_vars.values() if v.get()])
        selected_count.config(text=f"({count} selected)")

    for var in checkbox_vars.values():
        var.trace("w", lambda *args: update_selected_count())
    update_selected_count()

    # Buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill="x")

    def save_and_close():
        enabled = [ssa for ssa, var in checkbox_vars.items() if var.get()]
        _save_ssa_settings(enabled)
        dialog.destroy()
        messagebox.showinfo("Saved", f"SSA settings saved. {len(enabled)} SSA rule(s) enabled.")

    def cancel():
        dialog.destroy()

    ttk.Button(button_frame, text="Save", command=save_and_close, width=12).pack(side="right", padx=5)
    ttk.Button(button_frame, text="Cancel", command=cancel, width=12).pack(side="right")

    # Focus search box
    search_entry.focus()

    # Handle Enter key in search box
    def on_enter(event):
        save_and_close()

    search_entry.bind("<Return>", on_enter)

    dialog.wait_window()


def _detect_nav_sav_junk(cleaned_texts):
    ignored = set()
    notes = []
    if not cleaned_texts:
        return ignored, notes
    first_page = cleaned_texts[0]
    if "NAV SAV" in first_page and "COMMERCIAL INSURANCE PROPOSAL" in first_page:
        span = min(20, len(cleaned_texts))
        ignored.update(range(span))
        notes.append(f"Skipped Nav Sav intro pages 1-{span}")
        if len(cleaned_texts) > 20 and "BROKER FEE AGREEMENT" in cleaned_texts[20]:
            ignored.add(20)
            notes.append("Skipped Nav Sav Broker Fee Agreement page 21")
    return ignored, notes
