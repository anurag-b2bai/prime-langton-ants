#include <iostream>
#include <vector>
#include <chrono>
#include <cstdint>
#include <cstring>

using namespace std;

const int64_t DX[4] = {0, 1, 0, -1};
const int64_t DY[4] = {-1, 0, 1, 0};

// Packed coordinate helper: x, y in range [-2,000,000, +2,000,000]
inline uint64_t pack_coord(int64_t x, int64_t y) {
    uint64_t ux = (uint64_t)(x + 2000000);
    uint64_t uy = (uint64_t)(y + 2000000);
    return (ux << 32) | uy;
}

inline pair<int64_t, int64_t> unpack_coord(uint64_t val) {
    int64_t x = (int64_t)(val >> 32) - 2000000;
    int64_t y = (int64_t)(val & 0xFFFFFFFFULL) - 2000000;
    return {x, y};
}

// Flat Open-Addressing Hash Set for minimal RAM usage
struct FlatHashSet {
    size_t mask;
    size_t num_elements;
    vector<uint64_t> keys;

    FlatHashSet(size_t pow2_size = 67108864) { // 67M slots = 512MB RAM
        mask = pow2_size - 1;
        num_elements = 0;
        keys.assign(pow2_size, 0);
    }

    inline size_t hash_fn(uint64_t k) const {
        k ^= k >> 33;
        k *= 0xff51afd7ed558ccdULL;
        k ^= k >> 33;
        k *= 0xc4ceb9fe1a85ec53ULL;
        k ^= k >> 33;
        return (size_t)k;
    }

    // Toggle cell: if present -> erase; if not present -> insert
    inline void toggle(uint64_t key) {
        size_t idx = hash_fn(key) & mask;
        while (keys[idx] != 0 && keys[idx] != 1ULL) {
            if (keys[idx] == key) {
                // Found: Erase item (odd visit -> even visit -> turned OFF)
                keys[idx] = 1ULL; // Tombstone 1
                num_elements--;
                return;
            }
            idx = (idx + 1) & mask;
        }

        // Not found: Insert item (odd visit -> turned ON)
        keys[idx] = key;
        num_elements++;
    }

    inline bool contains(uint64_t key) const {
        size_t idx = hash_fn(key) & mask;
        while (keys[idx] != 0) {
            if (keys[idx] == key) return true;
            idx = (idx + 1) & mask;
        }
        return false;
    }

    size_t size() const {
        return num_elements;
    }
};

int main() {
    int64_t target_step = 342000001LL;
    cout << "Testing Flat Open-Addressing Hash Set up to Step #" << target_step << "..." << endl;

    auto t0 = chrono::high_resolution_clock::now();

    // Sieve up to target_step
    int64_t sieve_size = target_step + 10;
    vector<uint64_t> is_composite((sieve_size / 2 + 63) / 64, 0);

    auto is_prime = [&](int64_t n) -> bool {
        if (n < 2) return false;
        if (n == 2) return true;
        if ((n & 1) == 0) return false;
        int64_t idx = n / 2;
        return !(is_composite[idx / 64] & (1ULL << (idx % 64)));
    };

    auto set_composite = [&](int64_t n) {
        int64_t idx = n / 2;
        is_composite[idx / 64] |= (1ULL << (idx % 64));
    };

    for (int64_t i = 3; i * i <= sieve_size; i += 2) {
        if (is_prime(i)) {
            for (int64_t j = i * i; j <= sieve_size; j += 2 * i) {
                set_composite(j);
            }
        }
    }

    auto t1 = chrono::high_resolution_clock::now();
    cout << "Sieve generated in " << chrono::duration<double>(t1 - t0).count() << " seconds." << endl;

    FlatHashSet grid(67108864); // 67M slots = 512 MB RAM total!

    int64_t ant_x = 0, ant_y = 0;
    int ant_dir = 0; // 0 = UP (dx=0, dy=-1)

    for (int64_t N = 1; N <= target_step; N++) {
        if (!is_prime(N)) {
            // Composite step
            ant_x += DX[ant_dir];
            ant_y += DY[ant_dir];
        } else {
            // Prime step: flip cell
            uint64_t pk = pack_coord(ant_x, ant_y);
            grid.toggle(pk);

            if (is_prime(N - 2)) {
                ant_dir = (ant_dir + 3) & 3; // LEFT
            } else {
                ant_dir = (ant_dir + 1) & 3; // RIGHT
            }

            ant_x += DX[ant_dir];
            ant_y += DY[ant_dir];
        }
    }

    auto t2 = chrono::high_resolution_clock::now();
    cout << "Flat Hash Simulation completed in " << chrono::duration<double>(t2 - t1).count() << " seconds!" << endl;
    cout << "Final Step: " << target_step << " | Ant Pos: (" << ant_x << ", " << ant_y << ") | Dir: " << ant_dir 
         << " | Active Cells: " << grid.size() << endl;

    if (ant_x == 112894 && ant_y == 48653) {
        cout << "SUCCESS! VERIFICATION TARGET MATCHED EXACTLY! (112894, 48653)" << endl;
    } else {
        cout << "MISMATCH! Expected (112894, 48653), got (" << ant_x << ", " << ant_y << ")" << endl;
    }

    return 0;
}
