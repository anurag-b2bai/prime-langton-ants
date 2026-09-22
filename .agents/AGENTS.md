# Prime Langton's Ant Rules & Architecture Standard

## CRITICAL SIMULATION RULE (DO NOT ALTER):

1. **Initial Ant State**:
   - Initial Position: `ant.x = 0, ant.y = 0`
   - Initial Heading Direction: `ant.dir = 0` (**UP**)
   - Direction Vectors:
     - `0 = UP`   (`dx = 0,  dy = -1`)
     - `1 = RIGHT` (`dx = 1,  dy = 0`)
     - `2 = DOWN`  (`dx = 0,  dy = 1`)
     - `3 = LEFT`  (`dx = -1, dy = 0`)

2. **Step Number Primality Check**:
   - The simulation operates on step numbers $N = 1, 2, 3, 4, 5, \dots$
   - At step number $N$:
     - Check if **$N$ itself** is a prime number.
     - If $N$ is **composite**: Move ant 1 unit straight in current direction (`ant.x += dx[dir]; ant.y += dy[dir]`). Cell state does NOT change.
     - If $N$ is **prime**:
       - Flip cell at `(ant.x, ant.y)` (Visit count + 1; odd visits = lit white cell; even visits = off/deleted cell).
       - If $N-2$ is also prime (`TWIN_SECOND` prime): Turn **LEFT** (-90°): `dir = (dir + 3) % 4`.
       - If $N-2$ is not prime (`TWIN_FIRST_OR_ISOLATED` prime): Turn **RIGHT** (+90°): `dir = (dir + 1) % 4`.
       - Move ant 1 unit forward in new direction (`ant.x += dx[dir]; ant.y += dy[dir]`).
       - Set `stepCount = N + 1`.

3. **Performance Standard**:
   - Do NOT stream prime values from a prime lookup text file for the simulation step count.
   - Use a fast C++ bitset Eratosthenes Sieve for $O(1)$ step primality lookup up to target $N$.
   - 342,000,001 steps executes in ~11 seconds in C++.
   - Exact Verification Target: At step 342,000,001, ant position MUST be `(112894, 48653)`.

4. **Web UI & Image Output Endpoints**:
   - Server runs on Port 6969: `python3 server.py`
   - Live Web Visualizer: `http://localhost:6969/` (syncs live state from C++ `/api/checkpoint`).
   - 4K High-Res BMP Image: `http://localhost:6969/prime_ant_map.bmp` (Dark `#020617` background, bright white cells, green origin `(0,0)`, yellow ant head).
