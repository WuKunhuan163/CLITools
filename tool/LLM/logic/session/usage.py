"""API usage monitoring with SQLite persistence.

Logs every LLM API call to a per-provider SQLite database with timestamp,
model, token counts, success/failure, latency, and masked API key.

Storage: providers/<vendor>/data/usage.db (one DB per provider)
"""
import time
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

_PROVIDERS_DIR = Path(__file__).resolve().parent.parent / "providers"
_LOCK = threading.Lock()
_CONNECTIONS: Dict[str, sqlite3.Connection] = {}


def _mask_key(key: str) -> str:
    """Return a partially masked API key (first 6 + last 4)."""
    if not key or len(key) < 12:
        return "***" if key else ""
    return key[:6] + "..." + key[-4:]


def _provider_db_path(provider: str) -> Path:
    """Resolve vendor name from provider string (e.g. 'zhipu-glm-4-flash' → 'zhipu')."""
    vendor = provider.split("-")[0] if "-" in provider else provider
    return _PROVIDERS_DIR / vendor / "data" / "usage.db"


def _get_conn(provider: str = "") -> sqlite3.Connection:
    """Get a SQLite connection for a provider (thread-safe via lock)."""
    db_path = _provider_db_path(provider) if provider else _PROVIDERS_DIR.parent.parent.parent / "data" / "usage.db"
    key = str(db_path)
    if key not in _CONNECTIONS:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _init_schema(conn)
        _CONNECTIONS[key] = conn
    return _CONNECTIONS[key]


DEFAULT_RECORD_LIMIT = 1024
DEFAULT_CLEANUP_BATCH = 512
MAX_LIMIT = 1048576


def _init_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '',
            ok INTEGER NOT NULL DEFAULT 0,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            latency_s REAL NOT NULL DEFAULT 0.0,
            error TEXT NOT NULL DEFAULT '',
            error_code INTEGER NOT NULL DEFAULT 0,
            estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
            api_key_masked TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS provider_settings (
            provider TEXT PRIMARY KEY,
            record_limit INTEGER NOT NULL DEFAULT 1024,
            cleanup_batch INTEGER NOT NULL DEFAULT 512
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_provider
        ON usage (provider)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_timestamp
        ON usage (timestamp)
    """)
    conn.commit()


@dataclass
class UsageRecord:
    """Single API call record."""
    id: int = 0
    timestamp: float = 0.0
    provider: str = ""
    model: str = ""
    ok: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_s: float = 0.0
    error: str = ""
    error_code: int = 0
    estimated_cost_usd: float = 0.0
    api_key_masked: str = ""


def record_usage(provider: str, model: str, result: Dict[str, Any],
                 latency_s: float = 0.0, api_key: str = ""):
    """Insert a usage record into the database.

    Called after every provider.send() call. Thread-safe.
    Writes in a background thread to avoid stalling the caller.
    """
    usage = result.get("usage", {})
    rec = UsageRecord(
        timestamp=time.time(),
        provider=provider,
        model=model,
        ok=result.get("ok", False),
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        latency_s=round(latency_s, 3),
        error=str(result.get("error", ""))[:200] if not result.get("ok") else "",
        error_code=result.get("error_code", 0),
        estimated_cost_usd=result.get("estimated_cost_usd", 0.0),
        api_key_masked=_mask_key(api_key),
    )

    def _write():
        with _LOCK:
            try:
                conn = _get_conn(rec.provider)
                conn.execute("""
                    INSERT INTO usage (
                        timestamp, provider, model, ok,
                        prompt_tokens, completion_tokens, total_tokens,
                        latency_s, error, error_code,
                        estimated_cost_usd, api_key_masked
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec.timestamp, rec.provider, rec.model, int(rec.ok),
                    rec.prompt_tokens, rec.completion_tokens, rec.total_tokens,
                    rec.latency_s, rec.error, rec.error_code,
                    rec.estimated_cost_usd, rec.api_key_masked,
                ))
                conn.commit()
            except Exception:
                pass

        try:
            enforce_provider_limit(rec.provider)
        except Exception:
            pass

    threading.Thread(target=_write, daemon=True).start()


def _rows_to_records(rows) -> List[UsageRecord]:
    return [
        UsageRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            provider=row["provider"],
            model=row["model"],
            ok=bool(row["ok"]),
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            total_tokens=row["total_tokens"],
            latency_s=row["latency_s"],
            error=row["error"],
            error_code=row["error_code"],
            estimated_cost_usd=row["estimated_cost_usd"],
            api_key_masked=row["api_key_masked"],
        )
        for row in rows
    ]


def load_records(since: float = 0, provider: str = "",
                 limit: int = 10000) -> List[UsageRecord]:
    """Load usage records from a specific provider's DB, or all providers."""
    with _LOCK:
        if provider:
            return _load_from_db(_get_conn(provider), since, provider, limit)

        all_records = []
        if _PROVIDERS_DIR.is_dir():
            for d in _PROVIDERS_DIR.iterdir():
                if d.is_dir() and (d / "data" / "usage.db").exists():
                    try:
                        conn = _get_conn(d.name)
                        all_records.extend(_load_from_db(conn, since, "", limit))
                    except Exception:
                        pass
        all_records.sort(key=lambda r: r.timestamp)
        return all_records[:limit]


def _load_from_db(conn, since, provider, limit):
    sql = "SELECT * FROM usage WHERE 1=1"
    params: list = []
    if since:
        sql += " AND timestamp >= ?"
        params.append(since)
    if provider:
        sql += " AND provider = ?"
        params.append(provider)
    sql += " ORDER BY timestamp ASC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return _rows_to_records(rows)


def get_summary(since: float = 0, provider: str = "") -> Dict[str, Any]:
    """Aggregate usage statistics."""
    records = load_records(since=since, provider=provider)
    if not records:
        return {
            "total_calls": 0, "successful": 0, "failed": 0,
            "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
            "avg_latency_s": 0, "providers": {},
        }

    successful = [r for r in records if r.ok]
    failed = [r for r in records if not r.ok]

    by_provider: Dict[str, Dict[str, int]] = {}
    for r in records:
        if r.provider not in by_provider:
            by_provider[r.provider] = {"calls": 0, "tokens": 0, "errors": 0}
        by_provider[r.provider]["calls"] += 1
        by_provider[r.provider]["tokens"] += r.total_tokens
        if not r.ok:
            by_provider[r.provider]["errors"] += 1

    avg_lat = (sum(r.latency_s for r in successful) / len(successful)
               if successful else 0)

    return {
        "total_calls": len(records),
        "successful": len(successful),
        "failed": len(failed),
        "total_tokens": sum(r.total_tokens for r in records),
        "prompt_tokens": sum(r.prompt_tokens for r in records),
        "completion_tokens": sum(r.completion_tokens for r in records),
        "avg_latency_s": round(avg_lat, 2),
        "providers": by_provider,
        "period_start": records[0].timestamp if records else 0,
        "period_end": records[-1].timestamp if records else 0,
    }


def get_daily_summary(provider: str = "") -> Dict[str, Any]:
    """Get usage summary for the current day (since midnight)."""
    import datetime
    today_start = time.mktime(datetime.date.today().timetuple())
    return get_summary(since=today_start, provider=provider)


def rotate_usage(provider: str, max_records: int = 10000):
    """Keep only the newest max_records entries for a provider."""
    with _LOCK:
        conn = _get_conn(provider)
        count = conn.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
        if count < max_records:
            return 0
        to_delete = count // 2
        conn.execute("""
            DELETE FROM usage WHERE id IN (
                SELECT id FROM usage ORDER BY timestamp ASC LIMIT ?
            )
        """, (to_delete,))
        conn.commit()
        return to_delete


def clear_all(provider: str = ""):
    """Delete all usage records for a provider, or all providers."""
    with _LOCK:
        if provider:
            conn = _get_conn(provider)
            conn.execute("DELETE FROM usage")
            conn.commit()
        elif _PROVIDERS_DIR.is_dir():
            for d in _PROVIDERS_DIR.iterdir():
                if d.is_dir() and (d / "data" / "usage.db").exists():
                    try:
                        conn = _get_conn(d.name)
                        conn.execute("DELETE FROM usage")
                        conn.commit()
                    except Exception:
                        pass


def get_record_count(provider: str = "") -> int:
    """Get total number of usage records."""
    with _LOCK:
        if provider:
            conn = _get_conn(provider)
            return conn.execute("SELECT COUNT(*) FROM usage").fetchone()[0]

        total = 0
        if _PROVIDERS_DIR.is_dir():
            for d in _PROVIDERS_DIR.iterdir():
                if d.is_dir() and (d / "data" / "usage.db").exists():
                    try:
                        conn = _get_conn(d.name)
                        total += conn.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
                    except Exception:
                        pass
        return total


def get_provider_limits(provider: str) -> Dict[str, int]:
    """Get record_limit and cleanup_batch for a provider."""
    with _LOCK:
        conn = _get_conn(provider)
        row = conn.execute(
            "SELECT record_limit, cleanup_batch FROM provider_settings WHERE provider = ?",
            (provider,)
        ).fetchone()
        if row:
            return {"record_limit": row["record_limit"], "cleanup_batch": row["cleanup_batch"]}
        return {"record_limit": DEFAULT_RECORD_LIMIT, "cleanup_batch": DEFAULT_CLEANUP_BATCH}


def set_provider_limits(provider: str, record_limit: int, cleanup_batch: int) -> str:
    """Set record_limit and cleanup_batch for a provider."""
    if record_limit < 1 or record_limit > MAX_LIMIT:
        return f"record_limit must be between 1 and {MAX_LIMIT}"
    if cleanup_batch < 1:
        return "cleanup_batch must be at least 1"
    if cleanup_batch > record_limit:
        return f"cleanup_batch ({cleanup_batch}) cannot exceed record_limit ({record_limit})"

    with _LOCK:
        conn = _get_conn(provider)
        conn.execute("""
            INSERT INTO provider_settings (provider, record_limit, cleanup_batch)
            VALUES (?, ?, ?)
            ON CONFLICT(provider) DO UPDATE SET
                record_limit = excluded.record_limit,
                cleanup_batch = excluded.cleanup_batch
        """, (provider, record_limit, cleanup_batch))
        conn.commit()
    return ""


def get_all_provider_limits() -> Dict[str, Dict[str, int]]:
    """Get limits for all providers that have custom settings."""
    result = {}
    with _LOCK:
        if _PROVIDERS_DIR.is_dir():
            for d in _PROVIDERS_DIR.iterdir():
                if d.is_dir() and (d / "data" / "usage.db").exists():
                    try:
                        conn = _get_conn(d.name)
                        rows = conn.execute("SELECT * FROM provider_settings").fetchall()
                        for row in rows:
                            result[row["provider"]] = {
                                "record_limit": row["record_limit"],
                                "cleanup_batch": row["cleanup_batch"],
                            }
                    except Exception:
                        pass
    return result


def enforce_provider_limit(provider: str):
    """Check if a provider exceeds its record limit and clean up if needed."""
    limits = get_provider_limits(provider)
    record_limit = limits["record_limit"]
    cleanup_batch = limits["cleanup_batch"]

    with _LOCK:
        conn = _get_conn(provider)
        count = conn.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
        if count <= record_limit:
            return 0
        conn.execute("""
            DELETE FROM usage WHERE id IN (
                SELECT id FROM usage ORDER BY timestamp ASC LIMIT ?
            )
        """, (cleanup_batch,))
        conn.commit()
        return cleanup_batch
