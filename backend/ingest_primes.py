"""
Bulk Data Ingestion Pipeline for Pre-Computed & Pre-Classified Prime Numbers.
Ingests (prime_val, prime_type, gap_to_next) records into Range-Partitioned SQLite chunk tables.
"""

import os
import time
import sqlite3
from typing import Iterator, List, Tuple, Optional
from db_manager import (
    init_db,
    get_connection,
    create_chunk_table,
    register_chunk,
    get_all_chunks,
    DEFAULT_CHUNK_SIZE
)


def stream_primes_from_file(file_path: str, skip_lines: int = 0) -> Iterator[Tuple[int, int, int]]:
    """
    Generator streaming (prime_val, prime_type, gap_to_next) tuples from file.
    Expects comma-separated or space-separated lines.

    Args:
        file_path: Path to the prime text file.
        skip_lines: Number of lines to skip at the start (for fast resumption after restart).
                    Pass the number of primes already ingested so we don't re-read them.
    """
    skipped = 0
    with open(file_path, "r", encoding="utf-8", buffering=8*1024*1024) as f:
        for line in f:
            # Fast skip phase — no parsing, just count newlines
            if skipped < skip_lines:
                skipped += 1
                continue

            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").split()
            if len(parts) >= 3:
                try:
                    val = int(parts[0])
                    p_type = int(parts[1])
                    gap = int(parts[2])
                    yield (val, p_type, gap)
                except ValueError:
                    continue
            elif len(parts) == 1:
                try:
                    val = int(parts[0])
                    yield (val, 0, 2)
                except ValueError:
                    continue


def get_current_max_prime_index(db_path: str) -> int:
    """Return the highest prime_index currently stored in the database."""
    chunks = get_all_chunks(db_path)
    if not chunks:
        return 0
    return max(chunk["max_index"] for chunk in chunks)


def ingest_primes_file(
    file_path: str,
    db_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    batch_size: int = 100_000
) -> Tuple[int, int]:
    """
    Ingest pre-computed & pre-classified primes from file into partitioned SQLite tables.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prime file not found: {file_path}")

    init_db(db_path)
    start_index = get_current_max_prime_index(db_path) + 1
    current_index = start_index

    chunks = get_all_chunks(db_path)
    if chunks:
        last_chunk = chunks[-1]
        chunk_id = last_chunk["chunk_id"]
        if last_chunk["prime_count"] >= chunk_size:
            chunk_id += 1
            chunk_min_index = current_index
            chunk_min_prime = None
            chunk_max_prime = None
            chunk_count = 0
        else:
            chunk_min_index = last_chunk["min_index"]
            chunk_min_prime = last_chunk["min_prime"]
            chunk_max_prime = last_chunk["max_prime"]
            chunk_count = last_chunk["prime_count"]
    else:
        chunk_id = 0
        chunk_min_index = current_index
        chunk_min_prime = None
        chunk_max_prime = None
        chunk_count = 0

    conn = get_connection(db_path)
    table_name = create_chunk_table(conn, chunk_id)

    buffer: List[Tuple[int, int, int, int]] = []
    total_ingested = 0
    chunks_created = 1 if not chunks else 0

    start_time = time.time()
    last_log_time = start_time

    print(f"[*] Starting Bulk Ingestion from {file_path} (Starting prime index #{start_index})...")

    try:
        conn.execute("BEGIN TRANSACTION;")
        lines_to_skip = start_index - 1  # Skip lines already ingested
        if lines_to_skip > 0:
            print(f"  [Resume] Skipping {lines_to_skip:,} already-ingested lines in file...")

        for prime_val, prime_type, gap_to_next in stream_primes_from_file(file_path, skip_lines=lines_to_skip):
            if chunk_min_prime is None:
                chunk_min_prime = prime_val
            chunk_max_prime = prime_val

            buffer.append((current_index, prime_val, prime_type, gap_to_next))
            chunk_count += 1
            current_index += 1
            total_ingested += 1

            if len(buffer) >= batch_size:
                conn.executemany(
                    f"INSERT OR IGNORE INTO {table_name} (prime_index, prime_val, prime_type, gap_to_next) VALUES (?, ?, ?, ?);",
                    buffer
                )
                buffer.clear()

            if chunk_count >= chunk_size:
                if buffer:
                    conn.executemany(
                        f"INSERT OR IGNORE INTO {table_name} (prime_index, prime_val, prime_type, gap_to_next) VALUES (?, ?, ?, ?);",
                        buffer
                    )
                    buffer.clear()

                chunk_max_index = current_index - 1
                register_chunk(
                    conn,
                    chunk_id,
                    chunk_min_index,
                    chunk_max_index,
                    chunk_min_prime,
                    chunk_max_prime,
                    chunk_count
                )
                conn.commit()

                chunk_id += 1
                chunks_created += 1
                table_name = create_chunk_table(conn, chunk_id)
                chunk_min_index = current_index
                chunk_min_prime = None
                chunk_max_prime = None
                chunk_count = 0

                conn.execute("BEGIN TRANSACTION;")

            now = time.time()
            if total_ingested % 500_000 == 0 or (now - last_log_time) >= 2.5:
                elapsed = now - start_time
                rate = total_ingested / elapsed if elapsed > 0 else 0
                print(f"  -> Ingested {total_ingested:,} primes | Speed: {rate:,.0f} primes/sec | Chunk: {table_name}")
                last_log_time = now

        if buffer:
            conn.executemany(
                f"INSERT OR IGNORE INTO {table_name} (prime_index, prime_val, prime_type, gap_to_next) VALUES (?, ?, ?, ?);",
                buffer
            )
            buffer.clear()

        if chunk_count > 0:
            chunk_max_index = current_index - 1
            register_chunk(
                conn,
                chunk_id,
                chunk_min_index,
                chunk_max_index,
                chunk_min_prime,
                chunk_max_prime,
                chunk_count
            )
            conn.commit()

    finally:
        conn.close()

    elapsed = time.time() - start_time
    avg_speed = total_ingested / elapsed if elapsed > 0 else 0
    print(f"[+] Ingestion Completed! Total Primes: {total_ingested:,} | Time: {elapsed:.2f}s | Avg Speed: {avg_speed:,.0f} primes/sec")

    return total_ingested, chunks_created
