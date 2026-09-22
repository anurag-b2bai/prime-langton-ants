#include <iostream>
#include <fstream>
#include <vector>
#include <unordered_map>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>

using namespace std;

struct CoordHash {
    size_t operator()(const pair<int64_t, int64_t>& p) const {
        uint64_t ux = (uint64_t)p.first;
        uint64_t uy = (uint64_t)p.second;
        return (ux * 0x9e3779b97f4a7c15ULL) ^ (uy * 0xbf58476d1ce4e5b9ULL);
    }
};

// Fast inline integer to string formatter
inline int fast_itoa(char* out, int64_t val) {
    if (val == 0) { *out = '0'; return 1; }
    char buf[24];
    int i = 0;
    bool neg = false;
    if (val < 0) { neg = true; val = -val; }
    while (val > 0) {
        buf[i++] = (char)('0' + (val % 10));
        val /= 10;
    }
    int len = 0;
    if (neg) out[len++] = '-';
    while (i > 0) {
        out[len++] = buf[--i];
    }
    return len;
}

int main() {
    cout << "Testing ultra-fast chunked JSON buffer writer for 50 Million grid items..." << endl;

    size_t N = 50000000;
    unordered_map<pair<int64_t, int64_t>, int32_t, CoordHash> grid;
    grid.reserve(N);

    // Create 50M dummy entries
    for (size_t i = 0; i < N; i++) {
        grid[{(int64_t)(i % 50000), (int64_t)(i / 50000)}] = 1;
    }

    cout << "Created 50 Million grid entries in RAM. Now testing fast disk write..." << endl;

    auto t0 = chrono::high_resolution_clock::now();

    FILE* f = fopen("test_50m.json", "wb");
    if (!f) return 1;

    const size_t BUF_SIZE = 16 * 1024 * 1024; // 16MB buffer chunk
    vector<char> buffer(BUF_SIZE);
    size_t buf_pos = 0;

    auto flush_buf = [&]() {
        if (buf_pos > 0) {
            fwrite(buffer.data(), 1, buf_pos, f);
            buf_pos = 0;
        }
    };

    auto write_str = [&](const char* str, size_t len) {
        if (buf_pos + len >= BUF_SIZE) {
            flush_buf();
        }
        memcpy(buffer.data() + buf_pos, str, len);
        buf_pos += len;
    };

    const char* header = "{\n  \"grid\": [\n";
    write_str(header, strlen(header));

    size_t c = 0;
    size_t total_c = grid.size();

    char line_buf[128];
    for (auto& kv : grid) {
        // Build:    ["x,y", val],
        line_buf[0] = ' '; line_buf[1] = ' '; line_buf[2] = ' '; line_buf[3] = ' ';
        line_buf[4] = '['; line_buf[5] = '"';
        int p = 6;
        p += fast_itoa(line_buf + p, kv.first.first);
        line_buf[p++] = ',';
        p += fast_itoa(line_buf + p, kv.first.second);
        line_buf[p++] = '"'; line_buf[p++] = ','; line_buf[p++] = ' ';
        p += fast_itoa(line_buf + p, kv.second);
        line_buf[p++] = ']';
        if (++c < total_c) line_buf[p++] = ',';
        line_buf[p++] = '\n';

        if (buf_pos + p >= BUF_SIZE) {
            flush_buf();
        }
        memcpy(buffer.data() + buf_pos, line_buf, p);
        buf_pos += p;
    }

    const char* footer = "  ]\n}\n";
    write_str(footer, strlen(footer));
    flush_buf();
    fclose(f);

    auto t1 = chrono::high_resolution_clock::now();
    double write_time = chrono::duration<double>(t1 - t0).count();
    cout << "50 Million Grid JSON write finished in " << write_time << " seconds!" << endl;

    remove("test_50m.json");
    return 0;
}
