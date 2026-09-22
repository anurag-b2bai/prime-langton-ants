"""
High-Performance File-Based Prime Stream Reader.

Streams (prime_index, prime_val, prime_type, gap_to_next) tuples directly
from a pre-computed text file using buffered I/O — bypasses SQLite completely.

File Format supported:
  - 3-column: "<prime_val> <prime_type> <gap_to_next>"
  - 1-column: "<prime_val>"  (assumes type=ISOLATED, gap=2)
  - Comma or space separated.

This is the fastest streaming path when the file already exists on disk,
as it benefits from OS sequential read + page-cache without SQLite locking overhead.
"""

import os
import io
from typing import Iterator, Tuple, Optional

# Prime type constants (matches DB schema)
ISOLATED = 0
TWIN_FIRST = 1
TWIN_SECOND = 2


def classify_from_context(prev, cur, nxt):
    """
    Classify a prime using neighbor values.
    Returns (prime_type, gap_to_next).
    """
    is_twin_second = (prev is not None) and (cur - prev == 2)
    is_twin_first  = (nxt is not None)  and (nxt - cur == 2)

    if is_twin_second:
        p_type = TWIN_SECOND
    elif is_twin_first:
        p_type = TWIN_FIRST
    else:
        p_type = ISOLATED

    gap = (nxt - cur) if nxt is not None else 2
    return p_type, gap


def stream_from_file(file_path, start_prime_index=1, buf_size=8*1024*1024):
    """
    Memory-efficient prime stream generator from text file.

    Yields: (prime_index, prime_val, prime_type, gap_to_next)

    - 3-column file: uses stored prime_type and gap_to_next directly (FAST PATH).
    - 1-column file: reclassifies on-the-fly with 2-element lookahead window.
    - Uses .idx seek index (if available) to jump directly to target line.

    Args:
        file_path: Path to the prime text file.
        start_prime_index: 1-indexed position to start yielding from.
        buf_size: Read buffer size in bytes (default 8MB).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prime file not found: {file_path}")

    file_size = os.path.getsize(file_path)
    print(f"[FileStream] {file_path} ({file_size/1e9:.2f} GB) | start_index={start_prime_index:,}")

    # Load seek index for O(1) skip
    try:
        from prime_index import load_index, seek_to_index, index_exists
        idx_interval, idx_offsets = load_index(file_path)
    except ImportError:
        idx_interval, idx_offsets = None, None

    current_index = 0

    with io.open(file_path, "rb", buffering=buf_size) as fb:
        # Detect column format from first non-comment line
        col_count = 1
        for raw in fb:
            line = raw.strip().decode("utf-8", errors="ignore")
            if not line or line.startswith("#"):
                continue
            col_count = len(line.replace(",", " ").split())
            break
        fb.seek(0)

        if col_count >= 3:
            # === FAST PATH: pre-classified 3-column file ===
            # Seek to nearest index bookmark
            if idx_interval and idx_offsets and start_prime_index > 1:
                current_index = seek_to_index(fb, start_prime_index, idx_interval, idx_offsets) - 1
                print(f"[FileStream] Seeked to byte={fb.tell():,} | resuming from prime_index={current_index+1:,}")

            for raw in fb:
                line = raw.strip().decode("utf-8", errors="ignore")
                if not line or line.startswith("#"):
                    continue
                parts = line.replace(",", " ").split()
                try:
                    prime_val  = int(parts[0])
                    prime_type = int(parts[1])
                    gap        = int(parts[2])
                except (ValueError, IndexError):
                    continue
                current_index += 1
                if current_index < start_prime_index:
                    continue
                yield (current_index, prime_val, prime_type, gap)

        else:
            # === LOOKAHEAD PATH: 1-column file, classify on-the-fly ===
            # Buffer: ring of 3 (prev_val, cur_val, nxt_val)
            prev_val = None
            cur_val  = None

            for raw in fb:
                line = raw.strip().decode("utf-8", errors="ignore")
                if not line or line.startswith("#"):
                    continue
                try:
                    nxt_val = int(line.replace(",", " ").split()[0])
                except (ValueError, IndexError):
                    continue

                if cur_val is None:
                    # Seeding
                    cur_val = nxt_val
                    current_index += 1
                    continue

                # Now we have (prev_val, cur_val, nxt_val) — classify cur_val
                p_type, gap = classify_from_context(prev_val, cur_val, nxt_val)
                current_index += 1
                if current_index >= start_prime_index:
                    yield (current_index, cur_val, p_type, gap)

                prev_val = cur_val
                cur_val  = nxt_val

            # Flush last prime
            if cur_val is not None:
                p_type, gap = classify_from_context(prev_val, cur_val, None)
                current_index += 1
                if current_index >= start_prime_index:
                    yield (current_index, cur_val, p_type, gap)


def estimate_line_count(file_path, sample_bytes=1024*1024):
    """
    Estimate total prime count by sampling the first MB.
    Used for progress display without scanning the whole file.
    """
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        sample = f.read(sample_bytes)
    sample_lines = sample.count(b"\n")
    if sample_lines == 0:
        return 0
    avg_line_len = sample_bytes / sample_lines
    return int(file_size / avg_line_len)


def get_prime_at_index(file_path, target_index):
    """
    Return (prime_index, prime_val, prime_type, gap_to_next) for a given index.
    Uses linear scan — suitable for sequential resumption; prefer DB for random access.
    """
    for row in stream_from_file(file_path, start_prime_index=target_index):
        return row
    return None
