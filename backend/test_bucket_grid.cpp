#include <iostream>
#include <vector>
#include <chrono>
#include <cstdint>
#include <algorithm>

using namespace std;

const int64_t DX[4] = {0, 1, 0, -1};
const int64_t DY[4] = {-1, 0, 1, 0};

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

// Dynamic 256-Bucket Open Addressing Hash Set
struct BucketHashSet {
    static const size_t NUM_BUCKETS = 256;
    struct Bucket {
        size_t mask;
        size_t count;
        vector<uint64_t> keys;

        Bucket() : mask(1023), count(0), keys(1024, 0) {}

        inline size_t hash_fn(uint64_t k) const {
            k ^= k >> 33;
            k *= 0xff51afd7ed558ccdULL;
            k ^= k >> 33;
            return (size_t)k;
        }

        void rehash() {
            size_t new_cap = keys.size() * 2;
            vector<uint64_t> old_keys = move(keys);
            keys.assign(new_cap, 0);
            mask = new_cap - 1;
            count = 0;

            for (uint64_t k : old_keys) {
                if (k != 0 && k != 1ULL) {
                    size_t idx = hash_fn(k) & mask;
                    while (keys[idx] != 0 && keys[idx] != 1ULL) {
                        idx = (idx + 1) & mask;
                    }
                    keys[idx] = k;
                    count++;
                }
            }
        }

        inline void toggle(uint64_t key) {
            if (count * 2 >= keys.size()) {
                rehash();
            }

            size_t idx = hash_fn(key) & mask;
            while (keys[idx] != 0 && keys[idx] != 1ULL) {
                if (keys[idx] == key) {
                    keys[idx] = 1ULL; // Erase
                    count--;
                    return;
                }
                idx = (idx + 1) & mask;
            }
            keys[idx] = key;
            count++;
        }
    };

    Bucket buckets[NUM_BUCKETS];

    inline void toggle(uint64_t key) {
        size_t b_idx = (key ^ (key >> 16)) & 255;
        buckets[b_idx].toggle(key);
    }

    size_t size() const {
        size_t total = 0;
        for (size_t i = 0; i < NUM_BUCKETS; i++) {
            total += buckets[i].count;
        }
        return total;
    }
};

int main() {
    int64_t target_step = 342000001LL;
    cout << "Testing Dynamic Bucket Hash Set up to Step #" << target_step << "..." << endl;

    auto t0 = chrono::high_resolution_clock::now();

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

    BucketHashSet grid;

    int64_t ant_x = 0, ant_y = 0;
    int ant_dir = 0; // 0 = UP (dx=0, dy=-1)

    for (int64_t N = 1; N <= target_step; N++) {
        if (!is_prime(N)) {
            ant_x += DX[ant_dir];
            ant_y += DY[ant_dir];
        } else {
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
    cout << "Dynamic Bucket Grid Simulation completed in " << chrono::duration<double>(t2 - t1).count() << " seconds!" << endl;
    cout << "Final Step: " << target_step << " | Ant Pos: (" << ant_x << ", " << ant_y << ") | Dir: " << ant_dir 
         << " | Active Cells: " << grid.size() << endl;

    if (ant_x == 112894 && ant_y == 48653) {
        cout << "SUCCESS! VERIFICATION TARGET MATCHED EXACTLY! (112894, 48653)" << endl;
    } else {
        cout << "MISMATCH! Expected (112894, 48653), got (" << ant_x << ", " << ant_y << ")" << endl;
    }

    return 0;
}
