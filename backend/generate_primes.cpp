// High-Performance Segmented Sieve of Eratosthenes in C++
// Generates N prime numbers with pre-classified prime_type and gap_to_next.
// Output format per line: prime_val,prime_type,gap_to_next

#include <iostream>
#include <vector>
#include <cmath>
#include <fstream>
#include <chrono>

using namespace std;

void generate_primes(uint64_t target_count, const string& output_filename) {
    auto start_time = chrono::high_resolution_clock::now();
    cout << "[*] Starting C++ Prime Sieve & Pre-Classification for " << target_count << " primes..." << endl;

    // Estimate upper bound for Nth prime
    double n_dbl = static_cast<double>(target_count + 100);
    double log_n = log(n_dbl);
    double log_log_n = log(log_n);
    uint64_t limit = static_cast<uint64_t>(n_dbl * (log_n + log_log_n)) + 2000;
    uint64_t sqrt_limit = static_cast<uint64_t>(sqrt(limit)) + 100;

    // Step 1: Find simple primes up to sqrt(limit)
    vector<bool> is_simple_prime(sqrt_limit + 1, true);
    is_simple_prime[0] = is_simple_prime[1] = false;
    for (uint64_t i = 2; i * i <= sqrt_limit; ++i) {
        if (is_simple_prime[i]) {
            for (uint64_t j = i * i; j <= sqrt_limit; j += i) {
                is_simple_prime[j] = false;
            }
        }
    }

    vector<uint64_t> simple_primes;
    for (uint64_t i = 2; i <= sqrt_limit; ++i) {
        if (is_simple_prime[i]) {
            simple_primes.push_back(i);
        }
    }

    // Step 2: Segmented Sieve - Collect all target_count + 1 primes in a buffer or stream
    const uint64_t SEGMENT_SIZE = 524288; // 512 KB cache block
    vector<bool> segment(SEGMENT_SIZE);

    vector<uint64_t> primes;
    primes.reserve(target_count + 5);

    uint64_t low = 2;
    while (primes.size() <= target_count && low <= limit) {
        uint64_t high = min(low + SEGMENT_SIZE - 1, limit);
        fill(segment.begin(), segment.end(), true);

        for (uint64_t p : simple_primes) {
            if (p * p > high) break;
            uint64_t start_idx = (low + p - 1) / p * p;
            if (start_idx < p * p) start_idx = p * p;
            for (uint64_t j = start_idx; j <= high; j += p) {
                segment[j - low] = false;
            }
        }

        for (uint64_t n = low; n <= high; ++n) {
            if (segment[n - low]) {
                primes.push_back(n);
                if (primes.size() > target_count + 1) break;
            }
        }
        low += SEGMENT_SIZE;
    }

    ofstream out(output_filename, ios::out | ios::binary);
    if (!out.is_open()) {
        cerr << "[!] Failed to open output file: " << output_filename << endl;
        return;
    }

    // Step 3: Classify & Output Primes (prime_val, prime_type, gap_to_next)
    uint64_t N = min(static_cast<uint64_t>(primes.size()) - 1, target_count);
    for (uint64_t i = 0; i < N; ++i) {
        uint64_t cur_p = primes[i];
        uint64_t next_p = (i + 1 < primes.size()) ? primes[i + 1] : (cur_p + 2);
        uint64_t prev_p = (i > 0) ? primes[i - 1] : 0;
        uint64_t gap_to_next = next_p - cur_p;

        int prime_type = 0; // 0 = ISOLATED
        if (i > 0 && (cur_p - prev_p == 2)) {
            prime_type = 2; // TWIN_SECOND (Turn LEFT)
        } else if (i + 1 < primes.size() && (next_p - cur_p == 2)) {
            prime_type = 1; // TWIN_FIRST (Turn RIGHT)
        }

        out << cur_p << "," << prime_type << "," << gap_to_next << "\n";
    }

    out.close();
    auto end_time = chrono::high_resolution_clock::now();
    double duration = chrono::duration<double>(end_time - start_time).count();
    cout << "[+] Completed! Pre-classified " << N << " primes in " << duration << " seconds (" << output_filename << ")." << endl;
}

int main(int argc, char* argv[]) {
    uint64_t count = 899377374; // Default 3 * 299792458
    string output_file = "backend/primes_899m.txt";

    if (argc > 1) {
        count = stoull(argv[1]);
    }
    if (argc > 2) {
        output_file = argv[2];
    }

    generate_primes(count, output_file);
    return 0;
}
