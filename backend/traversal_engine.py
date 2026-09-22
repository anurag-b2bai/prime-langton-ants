"""
Headless & Memory-Safe 2D Prime-Number Traversal Engine (Langton's Ant Variant).
Supports two prime data sources:
  - 'db'   : SQLite range-partitioned DB (primes_partitioned.db) via db_manager.py
  - 'file' : Direct text-file streaming via file_stream.py (faster for sequential runs)
Supports periodic state checkpointing and strict RAM garbage collection.
"""

import os
import gc
import json
import time
from typing import Dict, Optional, Tuple, Any
from db_manager import stream_primes, fetch_prime_by_index
try:
    from file_stream import stream_from_file, get_prime_at_index as file_get_prime
except ImportError:
    stream_from_file = None
    file_get_prime = None


# Direction vectors: 0 = UP, 1 = RIGHT, 2 = DOWN, 3 = LEFT
DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]
DIR_SYMBOLS = ['↑ UP', '→ RIGHT', '↓ DOWN', '← LEFT']


class HeadlessAntEngine:
    def __init__(
        self,
        db_path: str,
        checkpoint_path: str = "checkpoint.json",
        checkpoint_freq: int = 500_000,
        gc_freq: int = 100_000,
        source_mode: str = "db",          # 'db' or 'file'
        source_file_path: Optional[str] = None  # required when source_mode='file'
    ):
        self.db_path = db_path
        self.checkpoint_path = checkpoint_path
        self.checkpoint_freq = checkpoint_freq
        self.gc_freq = gc_freq
        self.source_mode = source_mode
        self.source_file_path = source_file_path

        # Simulation state
        self.step_count: int = 1
        self.ant_x: int = 0
        self.ant_y: int = 0
        self.ant_dir: int = 0  # Start UP
        self.prime_index: int = 1  # 1-indexed prime sequence

        # Research & Statistics
        self.last_prime_step: Optional[int] = None
        self.min_prime_gap: float = float('inf')
        self.max_prime_gap: int = 0
        self.sum_prime_gaps: int = 0
        self.gap_count: int = 0

        self.total_right_turns: int = 0
        self.total_left_turns: int = 0
        self.total_cell_visits: int = 0
        self.peak_active_cells: int = 0
        self.peak_active_step: int = 1

        # Axis crossings
        self.x_axis_crossings: int = 0
        self.y_axis_crossings: int = 0
        self.last_cross_step_x: Optional[int] = None
        self.last_cross_step_y: Optional[int] = None

        # Bounding box
        self.min_x: int = 0
        self.max_x: int = 0
        self.min_y: int = 0
        self.max_y: int = 0

        # Grid state: mapping (x, y) -> {"visits": V, "flips_white": W, "flips_black": B}
        self.grid: Dict[Tuple[int, int], Dict[str, int]] = {}

    def track_bounds(self, x: int, y: int) -> None:
        """Update bounding box coordinates."""
        if x < self.min_x: self.min_x = x
        if x > self.max_x: self.max_x = x
        if y < self.min_y: self.min_y = y
        if y > self.max_y: self.max_y = y

    def track_axis_crossings(self, start_x: int, start_y: int, direction: int, dist: int) -> None:
        """Track X and Y axis crossings along a straight line segment."""
        end_x = start_x + DX[direction] * dist
        end_y = start_y + DY[direction] * dist

        if (start_y < 0 and end_y >= 0) or (start_y > 0 and end_y <= 0) or (start_y != 0 and end_y == 0):
            self.x_axis_crossings += 1
            self.last_cross_step_x = self.step_count

        if (start_x < 0 and end_x >= 0) or (start_x > 0 and end_x <= 0) or (start_x != 0 and end_x == 0):
            self.y_axis_crossings += 1
            self.last_cross_step_y = self.step_count

    def save_checkpoint(self) -> None:
        """State Checkpointing: Save simulation state to disk safely via temporary file write."""
        grid_serialized = {}
        for (x, y), cell_info in self.grid.items():
            grid_serialized[f"{x},{y}"] = cell_info

        state_data = {
            "step_count": self.step_count,
            "ant_x": self.ant_x,
            "ant_y": self.ant_y,
            "ant_dir": self.ant_dir,
            "prime_index": self.prime_index,
            "last_prime_step": self.last_prime_step,
            "min_prime_gap": None if self.min_prime_gap == float('inf') else self.min_prime_gap,
            "max_prime_gap": self.max_prime_gap,
            "sum_prime_gaps": self.sum_prime_gaps,
            "gap_count": self.gap_count,
            "total_right_turns": self.total_right_turns,
            "total_left_turns": self.total_left_turns,
            "total_cell_visits": self.total_cell_visits,
            "peak_active_cells": self.peak_active_cells,
            "peak_active_step": self.peak_active_step,
            "x_axis_crossings": self.x_axis_crossings,
            "y_axis_crossings": self.y_axis_crossings,
            "last_cross_step_x": self.last_cross_step_x,
            "last_cross_step_y": self.last_cross_step_y,
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
            "grid": grid_serialized
        }

        temp_path = self.checkpoint_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
        os.replace(temp_path, self.checkpoint_path)
        print(f"[Checkpoint] State saved at Step #{self.step_count:,} (Prime Index #{self.prime_index:,}) | Active Cells: {len(self.grid):,}")

    def load_checkpoint(self) -> bool:
        """State Checkpointing: Restore state from checkpoint file if present."""
        if not os.path.exists(self.checkpoint_path):
            return False

        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.step_count = data["step_count"]
            self.ant_x = data["ant_x"]
            self.ant_y = data["ant_y"]
            self.ant_dir = data["ant_dir"]
            self.prime_index = data["prime_index"]
            self.last_prime_step = data["last_prime_step"]
            self.min_prime_gap = float('inf') if data["min_prime_gap"] is None else data["min_prime_gap"]
            self.max_prime_gap = data["max_prime_gap"]
            self.sum_prime_gaps = data["sum_prime_gaps"]
            self.gap_count = data["gap_count"]
            self.total_right_turns = data["total_right_turns"]
            self.total_left_turns = data["total_left_turns"]
            self.total_cell_visits = data["total_cell_visits"]
            self.peak_active_cells = data["peak_active_cells"]
            self.peak_active_step = data.get("peak_active_step", 1)
            self.x_axis_crossings = data.get("x_axis_crossings", 0)
            self.y_axis_crossings = data.get("y_axis_crossings", 0)
            self.last_cross_step_x = data.get("last_cross_step_x")
            self.last_cross_step_y = data.get("last_cross_step_y")
            self.min_x = data.get("min_x", 0)
            self.max_x = data.get("max_x", 0)
            self.min_y = data.get("min_y", 0)
            self.max_y = data.get("max_y", 0)

            self.grid = {}
            for k, v in data["grid"].items():
                parts = k.split(",")
                coord = (int(parts[0]), int(parts[1]))
                if isinstance(v, int):
                    # Migration from old schema integer visit count
                    self.grid[coord] = {
                        "visits": v,
                        "flips_white": (v + 1) // 2,
                        "flips_black": v // 2
                    }
                else:
                    self.grid[coord] = v

            print(f"[Checkpoint] Successfully resumed simulation from Step #{self.step_count:,} (Prime Index #{self.prime_index:,})!")
            return True
        except Exception as e:
            print(f"[!] Warning: Failed to load checkpoint ({e}). Starting fresh.")
            return False

    def run(self, max_steps: Optional[int] = None) -> None:
        """
        Headless Traversal Engine Execution Loop.
        Supports two data sources:
          - source_mode='db'  : SQLite partitioned DB (random access capable)
          - source_mode='file': Direct text-file stream (faster sequential throughput)
        """
        self.load_checkpoint()

        start_time = time.time()
        last_log_time = start_time
        processed_prime_count = 0

        print(f"[*] Starting Headless Prime Traversal Engine (source={self.source_mode})...")
        print(f"    Initial State: Step={self.step_count:,}, Pos=({self.ant_x}, {self.ant_y}), Dir={DIR_SYMBOLS[self.ant_dir]}")

        # === Select Data Source ===
        if self.source_mode == "file":
            if stream_from_file is None:
                raise ImportError("file_stream.py not found. Cannot use source_mode='file'.")
            if not self.source_file_path:
                raise ValueError("source_file_path must be set when source_mode='file'.")
            print(f"    [FileStream] Using direct file: {self.source_file_path}")
            prime_stream = stream_from_file(self.source_file_path, start_prime_index=self.prime_index)
        else:
            print(f"    [DBStream] Using SQLite DB: {self.db_path}")
            prime_stream = stream_primes(self.db_path, start_index=self.prime_index)

        prev_prime_val: Optional[int] = None

        if self.prime_index > 1:
            # Fetch previous prime value for gap tracking
            if self.source_mode == "file" and file_get_prime:
                prev_row = file_get_prime(self.source_file_path, self.prime_index - 1)
                if prev_row:
                    prev_prime_val = prev_row[1]
            else:
                prev_row = fetch_prime_by_index(self.db_path, self.prime_index - 1)
                if prev_row:
                    prev_prime_val = prev_row[1]

        for row in prime_stream:
            if max_steps and self.step_count >= max_steps:
                print(f"[*] Reached target step count limit ({max_steps:,}). Stopping simulation.")
                break

            p_idx = row[0]
            cur_p = row[1]
            p_type = row[2] if len(row) > 2 else None

            self.prime_index = p_idx

            # 1. Composite steps skip: Move ant straight to cur_p position
            dist = cur_p - self.step_count
            if dist > 0:
                self.track_axis_crossings(self.ant_x, self.ant_y, self.ant_dir, dist)
                self.ant_x += DX[self.ant_dir] * dist
                self.ant_y += DY[self.ant_dir] * dist
                self.track_bounds(self.ant_x, self.ant_y)
                self.step_count = cur_p

            # 2. Determine Prime Type & Turning Angle
            if p_type is None:
                is_twin_second = (prev_prime_val is not None) and (cur_p - prev_prime_val == 2)
            else:
                is_twin_second = (p_type == 2)

            # 3. Grid Visit & Detailed Flip Statistics (Z-axis height = total visits)
            cell_key = (self.ant_x, self.ant_y)
            if cell_key not in self.grid:
                self.grid[cell_key] = {"visits": 0, "flips_white": 0, "flips_black": 0}

            cell_info = self.grid[cell_key]
            cell_info["visits"] += 1
            new_visit = cell_info["visits"]

            if new_visit % 2 == 1:
                cell_info["flips_white"] += 1  # Black -> White flip (Odd visit)
            else:
                cell_info["flips_black"] += 1  # White -> Black flip (Even visit)

            # Track peak active cells (cells currently lit / odd visits)
            cur_active = len(self.grid)
            if cur_active > self.peak_active_cells:
                self.peak_active_cells = cur_active
                self.peak_active_step = cur_p

            # 4. Turn Ant Direction
            if is_twin_second:
                self.ant_dir = (self.ant_dir + 3) % 4  # Turn LEFT (-90°)
                self.total_left_turns += 1
            else:
                self.ant_dir = (self.ant_dir + 1) % 4  # Turn RIGHT (+90°)
                self.total_right_turns += 1

            # 5. Move 1 step forward in new direction
            self.ant_x += DX[self.ant_dir]
            self.ant_y += DY[self.ant_dir]
            self.track_bounds(self.ant_x, self.ant_y)
            self.step_count = cur_p + 1

            # 6. Research Statistics
            if self.last_prime_step is not None:
                gap = cur_p - self.last_prime_step
                if gap < self.min_prime_gap: self.min_prime_gap = gap
                if gap > self.max_prime_gap: self.max_prime_gap = gap
                self.sum_prime_gaps += gap
                self.gap_count += 1

            self.last_prime_step = cur_p
            self.total_cell_visits += 1
            prev_prime_val = cur_p
            processed_prime_count += 1

            if processed_prime_count % self.checkpoint_freq == 0:
                self.save_checkpoint()

            if processed_prime_count % self.gc_freq == 0:
                gc.collect()

            now = time.time()
            if now - last_log_time >= 2.5:
                elapsed = now - start_time
                step_speed = self.step_count / elapsed if elapsed > 0 else 0
                prime_speed = processed_prime_count / elapsed if elapsed > 0 else 0
                print(f"  -> Step #{self.step_count:,} | Primes: {processed_prime_count:,} | Pos: ({self.ant_x}, {self.ant_y}) | Speed: {step_speed:,.0f} steps/s ({prime_speed:,.0f} primes/s) | Active Cells: {len(self.grid):,}")
                last_log_time = now

        self.save_checkpoint()
        elapsed = time.time() - start_time
        print(f"[+] Engine Execution Finished! Total Primes Processed: {processed_prime_count:,} | Runtime: {elapsed:.2f}s")
        self.print_summary()

    def print_summary(self) -> None:
        """Print detailed summary report."""
        total_turns = self.total_right_turns + self.total_left_turns
        turn_ratio = (self.total_right_turns / self.total_left_turns) if self.total_left_turns > 0 else float('inf')
        avg_gap = (self.sum_prime_gaps / self.gap_count) if self.gap_count > 0 else 0

        print("\n=================== TRAVERSAL ENGINE SUMMARY ===================")
        print(f" Total Steps Reached    : {self.step_count:,}")
        print(f" Total Primes Processed : {self.prime_index:,}")
        print(f" Final Ant Position     : ({self.ant_x}, {self.ant_y}) [{DIR_SYMBOLS[self.ant_dir]}]")
        print(f" Total Visited Cells    : {len(self.grid):,}")
        print(f" Peak Active Cells      : {self.peak_active_cells:,} (at Step #{self.peak_active_step:,})")
        print(f" Bounding Box           : X=[{self.min_x}, {self.max_x}], Y=[{self.min_y}, {self.max_y}]")
        print(f" Total Right Turns      : {self.total_right_turns:,}")
        print(f" Total Left Turns       : {self.total_left_turns:,}")
        print(f" Right/Left Turn Ratio  : {turn_ratio:.5f}")
        print(f" Prime Gap Stats        : Min={self.min_prime_gap}, Max={self.max_prime_gap}, Avg={avg_gap:.2f}")
        print(f" Axis Crossings         : X-Axis={self.x_axis_crossings:,}, Y-Axis={self.y_axis_crossings:,}")
        print("=================================================================\n")
