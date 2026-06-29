#!/usr/bin/env python3
"""
Compare two eCLM netCDF parameter files.

Output sections:
  1. Variables only in file A
  2. Variables only in file B
  3. Variables present in both but with differing values
     (index, value-in-A, value-in-B for each differing element)

Usage:
    compare_params.py FILE_A.nc FILE_B.nc
"""

import sys
import numpy as np
import netCDF4 as nc


def compare(path_a: str, path_b: str) -> None:
    ds_a = nc.Dataset(path_a)
    ds_b = nc.Dataset(path_b)

    vars_a = set(ds_a.variables)
    vars_b = set(ds_b.variables)

    label_a = path_a
    label_b = path_b

    # ------------------------------------------------------------------
    # 1. Variables only in one file
    # ------------------------------------------------------------------
    only_a = sorted(vars_a - vars_b)
    only_b = sorted(vars_b - vars_a)

    if only_a:
        print(f"\nOnly in {label_a}  ({len(only_a)}):")
        for v in only_a:
            print(f"  {v}")
    else:
        print(f"\nNo variables only in {label_a}")

    if only_b:
        print(f"\nOnly in {label_b}  ({len(only_b)}):")
        for v in only_b:
            print(f"  {v}")
    else:
        print(f"\nNo variables only in {label_b}")

    # ------------------------------------------------------------------
    # 2. Variables in both — find differences
    # ------------------------------------------------------------------
    diffs = {}   # var -> list of (index_tuple, val_a, val_b)

    for v in sorted(vars_a & vars_b):
        raw_a = ds_a[v][:]
        raw_b = ds_b[v][:]

        # --- char arrays (e.g. pftname) ---
        if raw_a.dtype.kind in ("S", "U") or raw_a.dtype == object:
            rows = []
            for i in range(len(raw_a)):
                sa = bytes(raw_a[i]).rstrip(b" \x00").decode("utf-8", errors="replace")
                sb = bytes(raw_b[i]).rstrip(b" \x00").decode("utf-8", errors="replace")
                if sa != sb:
                    rows.append(((i,), sa, sb))
            if rows:
                diffs[v] = rows
            continue

        # --- numeric arrays ---
        try:
            fa = np.ma.filled(raw_a.astype(float), np.nan)
            fb = np.ma.filled(raw_b.astype(float), np.nan)
        except Exception:
            continue

        both_nan = np.isnan(fa) & np.isnan(fb)
        different = ~both_nan & ~np.isclose(fa, fb, equal_nan=True)

        if not different.any():
            continue

        rows = []
        for idx in zip(*np.where(different)):
            va = fa[idx] if fa.ndim > 1 else fa[idx[0]]
            vb = fb[idx] if fb.ndim > 1 else fb[idx[0]]
            rows.append((idx, va, vb))
        diffs[v] = rows

    # ------------------------------------------------------------------
    # 3. Report differences
    # ------------------------------------------------------------------
    if not diffs:
        print("\nAll shared variables are identical.")
    else:
        print(f"\nDifferences in shared variables  ({len(diffs)} variable(s)):")
        for v, rows in diffs.items():
            print(f"\n  {v}  ({len(rows)} element(s))")
            for idx, va, vb in rows:
                idx_str = ",".join(str(i) for i in idx)
                if isinstance(va, str):
                    print(f"    [{idx_str}]  '{va}'  →  '{vb}'")
                else:
                    print(f"    [{idx_str}]  {va:.8g}  →  {vb:.8g}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\nSummary: {len(only_a)} only-in-A  |  {len(only_b)} only-in-B"
          f"  |  {len(diffs)} variables with value differences")


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} FILE_A.nc FILE_B.nc", file=sys.stderr)
        sys.exit(1)
    compare(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
