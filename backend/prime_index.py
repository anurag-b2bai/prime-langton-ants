"""
Fast seek index for primes_899m.txt.

Builds a sparse byte-offset index: every INDEX_INTERVAL primes, stores the
byte offset so we can f.seek() directly instead of scanning from line 0.

Index file: primes_899m.idx  (sits next to primes_899m.txt)
Format: binary little-endian, each entry = 8 bytes (int64 byte_offset)
Entry i  →  byte offset of prime #(i * INDEX_INTERVAL + 1)
"""

import os
import struct

INDEX_INTERVAL = 100_000   # one bookmark every 100k primes

def index_path(file_path):
    return file_path + ".idx"

def build_index(file_path, buf_size=8*1024*1024):
    """
    Scan primes_899m.txt once and write a .idx file.
    Takes ~3-4 minutes for 60M primes — only needed once.
    """
    idx_path = index_path(file_path)
    print(f"[Index] Building seek index for {file_path} ...")
    offsets = []  # byte offset of prime #1, #100001, #200001, ...

    with open(file_path, "rb", buffering=buf_size) as f:
        current_index = 0
        pos = 0

        while True:
            line_start = f.tell()
            raw = f.readline()
            if not raw:
                break
            line = raw.strip()
            if not line or line.startswith(b"#"):
                continue
            current_index += 1
            # Record offset at every INDEX_INTERVAL boundary
            if (current_index - 1) % INDEX_INTERVAL == 0:
                offsets.append(line_start)

    # Write index
    with open(idx_path, "wb") as idxf:
        idxf.write(struct.pack("<Q", INDEX_INTERVAL))   # header: interval
        for off in offsets:
            idxf.write(struct.pack("<q", off))

    print(f"[Index] Done. {len(offsets)} bookmarks written to {idx_path}")
    return idx_path


def load_index(file_path):
    """
    Load the .idx file.
    Returns (interval, offsets_list) or (None, None) if not found.
    """
    idx_path = index_path(file_path)
    if not os.path.exists(idx_path):
        return None, None
    try:
        with open(idx_path, "rb") as f:
            interval = struct.unpack("<Q", f.read(8))[0]
            data = f.read()
        n = len(data) // 8
        offsets = [struct.unpack("<q", data[i*8:(i+1)*8])[0] for i in range(n)]
        print(f"[Index] Loaded {len(offsets)} bookmarks (interval={interval:,})")
        return interval, offsets
    except Exception as e:
        print(f"[Index] Failed to load index: {e}")
        return None, None


def seek_to_index(f, target_index, interval, offsets):
    """
    Seek file `f` to the nearest bookmark before target_index,
    return the prime_index at that position (to continue scanning from).
    """
    if interval is None or not offsets:
        f.seek(0)
        return 1

    # Which bookmark bucket does target_index fall in?
    bucket = (target_index - 1) // interval
    if bucket >= len(offsets):
        bucket = len(offsets) - 1

    byte_off = offsets[bucket]
    f.seek(byte_off)
    return bucket * interval + 1   # prime_index at this position


def index_exists(file_path):
    return os.path.exists(index_path(file_path))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 prime_index.py <primes_file>")
        sys.exit(1)
    build_index(sys.argv[1])
