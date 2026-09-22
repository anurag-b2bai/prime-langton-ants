# 🐜 Prime Langton's Ant Engine & Live 4K Visualizer

An ultra-fast, zero-hang C++ simulation engine and live Python/HTML visualizer for **Prime-Based Langton's Ant**.

---

## 🎯 1. Mathematical Simulation Rules

The simulation operates on integer step numbers $N = 1, 2, 3, 4, 5, \dots$

### 🔹 Initial Ant State:
- **Initial Position**: `ant.x = 0, ant.y = 0`
- **Initial Direction**: `ant.dir = 0` (**UP**, $dx=0, dy=-1$)
- **Direction Mapping**:
  - `0 = UP`    ($dx = 0,  dy = -1$)
  - `1 = RIGHT` ($dx = 1,  dy = 0$)
  - `2 = DOWN`  ($dx = 0,  dy = 1$)
  - `3 = LEFT`  ($dx = -1, dy = 0$)

### 🔹 Step Primality & Cell State Rules:
At step number $N$:
1. Check if **$N$ itself** is a prime number.
2. If $N$ is **composite**:
   - Move ant 1 unit straight in current direction (`ant.x += dx[dir]`, `ant.y += dy[dir]`).
   - Cell state does **NOT** change.
3. If $N$ is **prime**:
   - Flip cell at `(ant.x, ant.y)` (Visit count + 1; odd visits = lit white cell; even visits = off/deleted cell).
   - If $N-2$ is prime (**`TWIN_SECOND`** prime): Turn **LEFT** (-90°): `dir = (dir + 3) % 4`.
   - If $N-2$ is composite (**`TWIN_FIRST_OR_ISOLATED`** prime): Turn **RIGHT** (+90°): `dir = (dir + 1) % 4`.
   - Move ant 1 unit forward in new direction (`ant.x += dx[dir]`, `ant.y += dy[dir]`).

---

## 🔬 2. Verified Mathematical Benchmarks

| Milestone Step $N$ | Ant Position $(X, Y)$ | Heading | Active Lit Cells | Description / Verification |
|---|---|---|---|---|
| **#342,000,001** | `(112894, 48653)` | 1 (RIGHT) | - | **Exact Verification Standard Target** |
| **6.0 Arab** ($6 \times 10^9$) | `(-282807, 364925)` | 3 (LEFT) | 247,587,098 | 600 Crore Benchmark |
| **8.6 Arab** ($8.6 \times 10^9$) | `(-261143, 354641)` | 1 (RIGHT) | 161,446,781 | **Current Active Checkpoint** |
| **10.0 Arab** ($10 \times 10^9$) | `(56509, -79535)` | 1 (RIGHT) | 402,033,939 | 1,000 Crore Benchmark |

---

## ⚡ 3. High-Performance Architecture

- **Segmented Sieve Primality Engine**: Memory footprint reduced by **99.5%** (down to 6.25 MB RAM).
- **Dynamic 256-Bucket Open-Addressing Hash Grid**: Manages 400,000,000+ active lit cells efficiently in 1.6 GB RAM.
- **Micro-Pacing Thermal Control**: `usleep(40)` caps CPU load at ~18% (zero thermal throttling, zero system freezes).
- **POSIX_FADV_DONTNEED & sync()**: Flushes OS page cache instantly to prevent Linux kernel OOM reboots.
- **Live Web Visualizer**: REST API & Interactive UI on Port 6969 (`http://localhost:6969/`).
- **4K High-Res Map Generation**: Generates 4K dark-mode BMP visualization maps showing active cells, origin beacon 🟢, and ant head 🟡 (`http://localhost:6969/prime_ant_map.bmp`).

---

## 🚀 4. How to Run & Resume Research

### 🔹 Step 1: Start Web Server & UI
```bash
cd backend
python3 server.py
```
Open **`http://localhost:6969/`** in your browser to view the live interactive graph and status.

### 🔹 Step 2: Compile C++ Engine
```bash
cd backend
g++ -O3 fast_ant_engine.cpp -o fast_ant_engine
```

### 🔹 Step 3: Run Engine or Incremental Master Runner
To run towards a target step (e.g. 18.0 Arab steps):
```bash
# Run continuous engine from 6.0 Arab to 18.0 Arab:
./fast_ant_engine 18000000000 6000000000

# OR run incremental runner script:
python3 run_incremental_ant.py
```

---

## 📁 5. Directory Structure

```
├── README.md                      # Comprehensive Architecture & Research Guide
├── RESEARCH_GUIDE.md              # Research & Mathematical Deep Dive
├── checkpoint.json                # Active simulation state (JSON)
├── prime_langton_ant.html         # Web UI visualizer
└── backend/
    ├── fast_ant_engine.cpp        # Zero-hang Segmented Sieve C++ engine
    ├── server.py                  # Python REST API server (Port 6969)
    ├── run_incremental_ant.py     # Master incremental slice runner
    └── checkpoint.json            # Active backend checkpoint
```

---

## 📄 License
MIT License
