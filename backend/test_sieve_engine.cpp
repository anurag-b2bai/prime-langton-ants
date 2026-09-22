#include <iostream>
#include <vector>
#include <unordered_map>
#include <chrono>
#include <cstdint>

using namespace std;

const int64_t DX[4] = {0, 1, 0, -1};
const int64_t DY[4] = {-1, 0, 1, 0};

struct CoordHash {
    size_t operator()(const pair<int64_t, int64_t>& p) const {
        uint64_t ux = (uint64_t)p.first;
        uint64_t uy = (uint64_t)p.second;
        return (ux * 0x9e3779b97f4a7c15ULL) ^ (uy * 0xbf58476d1ce4e5b9ULL);
    }
};

int main() {
    int64_t target_step = 342000001LL;
    cout << "Testing Hop Sieve Ant Simulation up to Step #" << target_step << "..." << endl;

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

    // Collect all primes up to target_step
    vector<int64_t> primes;
    primes.reserve(20000000);
    primes.push_back(2);
    for (int64_t i = 3; i <= sieve_size; i += 2) {
        if (is_prime(i)) primes.push_back(i);
    }

    auto t1 = chrono::high_resolution_clock::now();
    cout << "Sieve + Prime collection generated " << primes.size() << " primes in " << chrono::duration<double>(t1 - t0).count() << " seconds." << endl;

    unordered_map<pair<int64_t, int64_t>, int32_t, CoordHash> grid;
    grid.reserve(5000000);

    int64_t ant_x = 0, ant_y = 0;
    int ant_dir = 0; // 0 = UP (dx=0, dy=-1)
    int64_t cur_step = 1;

    for (size_t i = 0; i < primes.size(); i++) {
        int64_t P = primes[i];
        if (P > target_step) break;

        // Composite steps before P
        int64_t comp_dist = P - cur_step;
        if (comp_dist > 0) {
            ant_x += DX[ant_dir] * comp_dist;
            ant_y += DY[ant_dir] * comp_dist;
            cur_step = P;
        }

        // Prime flip
        pair<int64_t, int64_t> pos = {ant_x, ant_y};
        auto it = grid.find(pos);
        if (it == grid.end()) {
            grid[pos] = 1;
        } else {
            it->second++;
            if (it->second % 2 == 0) grid.erase(it);
        }

        // Turn
        if (is_prime(P - 2)) {
            ant_dir = (ant_dir + 3) & 3; // LEFT
        } else {
            ant_dir = (ant_dir + 1) & 3; // RIGHT
        }

        // Move 1 unit forward
        ant_x += DX[ant_dir];
        ant_y += DY[ant_dir];
        cur_step = P + 1;
    }

    // Remaining composite steps up to target_step
    if (cur_step <= target_step) {
        int64_t rem = target_step - cur_step + 1;
        ant_x += DX[ant_dir] * rem;
        ant_y += DY[ant_dir] * rem;
        cur_step = target_step + 1;
    }

    auto t2 = chrono::high_resolution_clock::now();
    cout << "Hop simulation completed in " << chrono::duration<double>(t2 - t1).count() << " seconds!" << endl;
    cout << "Final Step: " << target_step << " | Ant Pos: (" << ant_x << ", " << ant_y << ") | Dir: " << ant_dir 
         << " | Active Cells: " << grid.size() << endl;

    if (ant_x == 112894 && ant_y == 48653) {
        cout << "SUCCESS! VERIFICATION TARGET MATCHED EXACTLY! (112894, 48653)" << endl;
    } else {
        cout << "MISMATCH! Expected (112894, 48653), got (" << ant_x << ", " << ant_y << ")" << endl;
    }

    return 0;
}
