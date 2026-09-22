"""
SQLite Range Partitioning Database Manager for Large-Scale Prime Data.
Supports pre-classified prime_type and gap_to_next for zero-math fast simulation.
"""

import sqlite3
from typing import Dict, List, Optional, Tuple, Iterator, Any

CHUNK_METADATA_TABLE = "chunk_metadata"
DEFAULT_CHUNK_SIZE = 10_000_000  # Default 10M primes per partition table


def get_connection(db_path: str) -> sqlite3.Connection:
    """Connect to SQLite database with optimized performance pragmas and lock timeouts."""
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn


def init_db(db_path: str) -> None:
    """Initialize master chunk metadata table if not exists."""
    with get_connection(db_path) as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {CHUNK_METADATA_TABLE} (
                chunk_id INTEGER PRIMARY KEY,
                min_index INTEGER NOT NULL,
                max_index INTEGER NOT NULL,
                min_prime INTEGER NOT NULL,
                max_prime INTEGER NOT NULL,
                table_name TEXT NOT NULL UNIQUE,
                prime_count INTEGER NOT NULL
            );
        """)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_meta_range ON {CHUNK_METADATA_TABLE} (min_index, max_index);")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_meta_prime ON {CHUNK_METADATA_TABLE} (min_prime, max_prime);")
        conn.commit()


def get_chunk_table_name(chunk_id: int) -> str:
    """Return formatted table name for a chunk ID."""
    return f"primes_chunk_{chunk_id}"


def create_chunk_table(conn: sqlite3.Connection, chunk_id: int) -> str:
    """Create a new chunk table with prime_type and gap_to_next columns, or migrate existing tables."""
    table_name = get_chunk_table_name(chunk_id)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            prime_index INTEGER PRIMARY KEY,
            prime_val INTEGER NOT NULL,
            prime_type INTEGER NOT NULL DEFAULT 0,
            gap_to_next INTEGER NOT NULL DEFAULT 2
        );
    """)

    # Column Migration check for legacy tables
    cursor = conn.execute(f"PRAGMA table_info({table_name});")
    existing_cols = {row[1] for row in cursor.fetchall()}

    if "prime_type" not in existing_cols:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN prime_type INTEGER NOT NULL DEFAULT 0;")
    if "gap_to_next" not in existing_cols:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN gap_to_next INTEGER NOT NULL DEFAULT 2;")

    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_val ON {table_name} (prime_val);")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_type ON {table_name} (prime_type);")
    return table_name


def register_chunk(
    conn: sqlite3.Connection,
    chunk_id: int,
    min_index: int,
    max_index: int,
    min_prime: int,
    max_prime: int,
    prime_count: int
) -> None:
    """Insert or replace metadata for a chunk partition."""
    table_name = get_chunk_table_name(chunk_id)
    conn.execute(f"""
        INSERT OR REPLACE INTO {CHUNK_METADATA_TABLE}
        (chunk_id, min_index, max_index, min_prime, max_prime, table_name, prime_count)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (chunk_id, min_index, max_index, min_prime, max_prime, table_name, prime_count))


def get_all_chunks(db_path: str) -> List[Dict[str, Any]]:
    """Return list of all registered chunk partition metadata ordered by chunk_id."""
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(f"SELECT * FROM {CHUNK_METADATA_TABLE} ORDER BY chunk_id ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_chunk_for_index(db_path: str, prime_index: int) -> Optional[Dict[str, Any]]:
    """
    Dynamic Table Router (by Index):
    Locates the specific chunk partition containing prime_index using O(1)/O(log N) metadata query.
    """
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            f"SELECT * FROM {CHUNK_METADATA_TABLE} WHERE min_index <= ? AND max_index >= ? LIMIT 1;",
            (prime_index, prime_index)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_prime_by_index(db_path: str, prime_index: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Fetch single prime row (prime_index, prime_val, prime_type, gap_to_next) using Dynamic Table Routing.
    Handles both legacy 2-column and 4-column chunk tables.
    """
    chunk = get_chunk_for_index(db_path, prime_index)
    if not chunk:
        return None
    
    table_name = chunk["table_name"]
    with get_connection(db_path) as conn:
        try:
            cursor = conn.execute(
                f"SELECT prime_index, prime_val, prime_type, gap_to_next FROM {table_name} WHERE prime_index = ?;",
                (prime_index,)
            )
            return cursor.fetchone()
        except sqlite3.OperationalError:
            cursor = conn.execute(
                f"SELECT prime_index, prime_val, 0 AS prime_type, 2 AS gap_to_next FROM {table_name} WHERE prime_index = ?;",
                (prime_index,)
            )
            return cursor.fetchone()


def stream_primes(
    db_path: str,
    start_index: int = 1,
    end_index: Optional[int] = None,
    batch_size: int = 50_000
) -> Iterator[Tuple[int, int, int, int]]:
    """
    Memory-Safe Prime Stream Generator.
    Yields (prime_index, prime_val, prime_type, gap_to_next) tuples.
    Falls back gracefully for legacy 2-column tables.
    """
    chunks = get_all_chunks(db_path)
    if not chunks:
        return

    curr_idx = start_index

    for chunk in chunks:
        if end_index and curr_idx > end_index:
            break

        if chunk["max_index"] < curr_idx:
            continue

        table_name = chunk["table_name"]
        chunk_end = chunk["max_index"] if end_index is None else min(chunk["max_index"], end_index)

        with get_connection(db_path) as conn:
            try:
                cursor = conn.execute(
                    f"SELECT prime_index, prime_val, prime_type, gap_to_next FROM {table_name} WHERE prime_index >= ? AND prime_index <= ? ORDER BY prime_index ASC;",
                    (curr_idx, chunk_end)
                )
            except sqlite3.OperationalError:
                cursor = conn.execute(
                    f"SELECT prime_index, prime_val, 0 AS prime_type, 2 AS gap_to_next FROM {table_name} WHERE prime_index >= ? AND prime_index <= ? ORDER BY prime_index ASC;",
                    (curr_idx, chunk_end)
                )

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                for row in rows:
                    yield (row[0], row[1], row[2], row[3])
                    curr_idx = row[0] + 1
                if curr_idx > chunk_end:
                    break
