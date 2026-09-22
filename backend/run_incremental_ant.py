#!/usr/bin/env python3
"""
Zero-Hang Master Runner for Prime Langton's Ant Simulation
Advances in small, safe 5 Crore step (50,000,000 step = 0.05 Arab) slices.
Keeps RAM strictly at ~1.1 GB and CPU load at ~25%.
Updates http://localhost:6969/ live after every single slice.
"""

import os
import sys
import json
import time
import subprocess

TARGET_FINAL_STEP = 18000000000  # 18.0 Arab steps (1,800 Crore steps)
SLICE_SIZE = 50000000           # 5 Crore steps (0.05 Arab) per slice
PAUSE_BETWEEN_SLICES_SEC = 1.0  # 1.0 second cooling pause between slices

def get_current_checkpoint_step():
    if os.path.exists("checkpoint.json"):
        try:
            with open("checkpoint.json", "r") as f:
                data = json.load(f)
                return data.get("stepCount", 8500000000)
        except Exception:
            pass
    return 8500000000

def find_highest_bin_snapshot(current_step):
    highest = 0
    if os.path.exists("dataset"):
        for fname in os.listdir("dataset"):
            if fname.startswith("snapshot_step_") and fname.endswith(".bin"):
                try:
                    step = int(fname.replace("snapshot_step_", "").replace(".bin", ""))
                    if step <= current_step and step > highest:
                        highest = step
                except ValueError:
                    pass
    if highest > 0:
        return highest
    return 6000000000

def main():
    print("==========================================================")
    print("  ZERO-HANG INCREMENTAL PRIME LANGTON'S ANT RUNNER")
    print(f"  TARGET FINAL STEP: {TARGET_FINAL_STEP / 1e9:.2f} ARAB ({TARGET_FINAL_STEP})")
    print(f"  SLICE SIZE       : {SLICE_SIZE / 1e7:.1f} CRORE STEPS ({SLICE_SIZE})")
    print("==========================================================")

    while True:
        curr_step = get_current_checkpoint_step()
        if curr_step >= TARGET_FINAL_STEP:
            print(f"\n🎉 REACHED FINAL TARGET OF {TARGET_FINAL_STEP / 1e9:.2f} ARAB STEPS!")
            break

        start_step = find_highest_bin_snapshot(curr_step)
        target_step = min(curr_step + SLICE_SIZE, TARGET_FINAL_STEP)

        print(f"\n🚀 Running Slice: Current #{curr_step} -> Target #{target_step} ({target_step / 1e9:.2f} Arab) | Base Bin: #{start_step}")
        cmd = ["./fast_ant_engine", str(target_step), str(start_step)]
        
        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elapsed = time.time() - t0

        if res.returncode != 0:
            print(f"❌ Error in slice execution:\n{res.stderr}")
            time.sleep(3)
            continue

        print(f"✅ Slice Completed in {elapsed:.2f}s | Updated checkpoint.json & prime_ant_map.bmp!")
        time.sleep(PAUSE_BETWEEN_SLICES_SEC)

if __name__ == "__main__":
    main()
