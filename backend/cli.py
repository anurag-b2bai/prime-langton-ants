"""
Unified CLI Entrypoint for Headless 2D Prime-Number Traversal Engine.
Supports dataset generation, bulk SQLite ingestion, simulation execution, and state reporting.
"""

import sys
import argparse
from generate_sample_primes import generate_n_primes
from ingest_primes import ingest_primes_file
from traversal_engine import HeadlessAntEngine
from db_manager import get_all_chunks, fetch_prime_by_index


DEFAULT_DB_PATH = "backend/primes_partitioned.db"


def main():
    parser = argparse.ArgumentParser(description="Headless 2D Prime Traversal Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: generate-primes
    cmd_gen = subparsers.add_parser("generate-primes", help="Generate prime dataset file")
    cmd_gen.add_argument("--count", type=int, default=1_000_000, help="Number of primes to generate")
    cmd_gen.add_argument("--output", type=str, default="backend/primes_sample.txt", help="Output text file path")

    # Command: ingest
    cmd_ingest = subparsers.add_parser("ingest", help="Ingest prime dataset file into Partitioned SQLite")
    cmd_ingest.add_argument("--input", type=str, default="backend/primes_sample.txt", help="Input prime text file")
    cmd_ingest.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="SQLite database output path")
    cmd_ingest.add_argument("--chunk-size", type=int, default=10_000_000, help="Primes per partition table")

    # Command: run
    cmd_run = subparsers.add_parser("run", help="Run Headless Traversal Engine")
    cmd_run.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="SQLite database path")
    cmd_run.add_argument("--steps", type=int, default=None, help="Target step count limit (optional)")
    cmd_run.add_argument("--checkpoint-path", type=str, default="backend/checkpoint.json", help="State checkpoint path")
    cmd_run.add_argument("--checkpoint-freq", type=int, default=500_000, help="Checkpoint frequency in prime steps")
    cmd_run.add_argument("--source", type=str, default="db", choices=["db", "file"], help="Data source: 'db' (SQLite) or 'file' (direct text file, faster)")
    cmd_run.add_argument("--source-file", type=str, default="backend/primes_899m.txt", help="Prime text file path (used when --source=file)")

    # Command: status
    cmd_status = subparsers.add_parser("status", help="Show database & partition status")
    cmd_status.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="SQLite database path")

    args = parser.parse_args()

    if args.command == "generate-primes":
        generate_n_primes(args.count, args.output)

    elif args.command == "ingest":
        ingest_primes_file(args.input, args.db, chunk_size=args.chunk_size)

    elif args.command == "run":
        engine = HeadlessAntEngine(
            db_path=args.db,
            checkpoint_path=args.checkpoint_path,
            checkpoint_freq=args.checkpoint_freq,
            source_mode=args.source,
            source_file_path=args.source_file
        )
        engine.run(max_steps=args.steps)

    elif args.command == "status":
        chunks = get_all_chunks(args.db)
        if not chunks:
            print(f"[!] Database at '{args.db}' contains no registered partition chunks.")
        else:
            print(f"\n================ PARTITIONED DATABASE STATUS ================")
            print(f" Database Path     : {args.db}")
            print(f" Partition Chunks  : {len(chunks)}")
            total_primes = sum(c['prime_count'] for c in chunks)
            print(f" Total Primes      : {total_primes:,}")
            print("-------------------------------------------------------------")
            for c in chunks:
                print(f"  [{c['table_name']}] Indexes: #{c['min_index']:,} -> #{c['max_index']:,} | Primes: {c['min_prime']:,} -> {c['max_prime']:,} ({c['prime_count']:,} items)")
            print("=============================================================\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
