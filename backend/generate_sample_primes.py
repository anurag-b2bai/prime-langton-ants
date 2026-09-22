"""
Utility to generate prime number datasets (using Sieve of Eratosthenes)
for testing the bulk ingestion pipeline and headless traversal engine.
"""

import time
import argparse


def generate_primes_sieve(limit: int) -> list:
    """Generate primes up to limit using Sieve of Eratosthenes."""
    if limit < 2:
        return []
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    return [i for i, is_p in enumerate(sieve) if is_p]


def generate_n_primes(count: int, output_file: str) -> None:
    """Generate first `count` prime numbers and save to text file."""
    start_time = time.time()
    print(f"[*] Generating first {count:,} primes...")

    # Estimate limit using Prime Number Theorem: p_n ≈ n * (ln(n) + ln(ln(n)))
    if count < 6:
        limit = 15
    else:
        import math
        ln_n = math.log(count)
        limit = int(count * (ln_n + math.log(ln_n))) + 100

    primes = generate_primes_sieve(limit)

    while len(primes) < count:
        limit = int(limit * 1.3)
        primes = generate_primes_sieve(limit)

    primes = primes[:count]

    with open(output_file, "w", encoding="utf-8") as f:
        for p in primes:
            f.write(f"{p}\n")

    elapsed = time.time() - start_time
    print(f"[+] Successfully generated {len(primes):,} primes to '{output_file}' in {elapsed:.2f}s!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate prime datasets")
    parser.add_argument("--count", type=int, default=1_000_000, help="Number of primes to generate")
    parser.add_argument("--output", type=str, default="primes_sample.txt", help="Output file path")
    args = parser.parse_args()
    generate_n_primes(args.count, args.output)
