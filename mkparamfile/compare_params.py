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
    compare_params.py FILE_A.nc FILE_B.nc --pft 43
    compare_params.py FILE_A.nc FILE_B.nc --verbose
    compare_params.py FILE_A.nc FILE_B.nc --summary
"""

import argparse
import numpy as np
import netCDF4 as nc

# ---------------------------------------------------------------------------
# PFT name catalogue
# Sources (official CLM5 documentation):
#   NATPFT (Table 2.2.1):
#     https://escomp.github.io/CTSM/release-clm5.0/tech_note/Ecosystem/CLM50_Tech_Note_Ecosystem.html#id15
#   CFT (Table 2.26.1):
#     https://escomp.github.io/CTSM/release-clm5.0/tech_note/Crop_Irrigation/CLM50_Tech_Note_Crop_Irrigation.html#id20
# Fetched at import time (3 s timeout); falls back to hardcoded values offline.
# ---------------------------------------------------------------------------

def _fetch_pft_names_from_docs():
    import urllib.request
    from html.parser import HTMLParser

    class _TableParser(HTMLParser):
        def __init__(self, table_id):
            super().__init__()
            self._target = table_id
            self._active = False
            self._in_cell = False
            self._cur_row = []
            self._cur_text = ""
            self.rows = []

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            if tag == "table" and d.get("id") == self._target:
                self._active = True
            if self._active:
                if tag == "tr":
                    self._cur_row = []
                elif tag in ("td", "th"):
                    self._in_cell = True
                    self._cur_text = ""

        def handle_endtag(self, tag):
            if not self._active:
                return
            if tag == "table":
                self._active = False
            elif tag == "tr":
                if self._cur_row:
                    self.rows.append(self._cur_row)
                self._cur_row = []
            elif tag in ("td", "th"):
                self._cur_row.append(self._cur_text.strip())
                self._in_cell = False

        def handle_data(self, data):
            if self._in_cell:
                self._cur_text += data

    def _parse(url, table_id):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None
        parser = _TableParser(table_id)
        parser.feed(html)
        result = {}
        for row in parser.rows:
            if len(row) < 2:
                continue
            try:
                result[int(row[0])] = row[1]
            except ValueError:
                pass
        return result if result else None

    natpft = _parse(
        "https://escomp.github.io/CTSM/release-clm5.0/tech_note/"
        "Ecosystem/CLM50_Tech_Note_Ecosystem.html",
        table_id="id15",
    )
    cft = _parse(
        "https://escomp.github.io/CTSM/release-clm5.0/tech_note/"
        "Crop_Irrigation/CLM50_Tech_Note_Crop_Irrigation.html",
        table_id="id20",
    )
    return natpft, cft


_NATPFT_FALLBACK = {
    0:  "Bare Ground",
    1:  "Needleleaf evergreen tree – temperate",
    2:  "Needleleaf evergreen tree – boreal",
    3:  "Needleleaf deciduous tree – boreal",
    4:  "Broadleaf evergreen tree – tropical",
    5:  "Broadleaf evergreen tree – temperate",
    6:  "Broadleaf deciduous tree – tropical",
    7:  "Broadleaf deciduous tree – temperate",
    8:  "Broadleaf deciduous tree – boreal",
    9:  "Broadleaf evergreen shrub – temperate",
    10: "Broadleaf deciduous shrub – temperate",
    11: "Broadleaf deciduous shrub – boreal",
    12: "C3 arctic grass",
    13: "C3 grass",
    14: "C4 grass",
}

_CFT_FALLBACK = {
    15: "C3 unmanaged rainfed crop",       16: "C3 unmanaged irrigated crop",
    17: "Temperate corn rainfed",           18: "Temperate corn irrigated",
    19: "Spring wheat rainfed",             20: "Spring wheat irrigated",
    21: "Winter wheat rainfed",             22: "Winter wheat irrigated",
    23: "Temperate soybean rainfed",        24: "Temperate soybean irrigated",
    25: "Barley rainfed",                   26: "Barley irrigated",
    27: "Winter barley rainfed",            28: "Winter barley irrigated",
    29: "Rye rainfed",                      30: "Rye irrigated",
    31: "Winter rye rainfed",               32: "Winter rye irrigated",
    33: "Cassava rainfed",                  34: "Cassava irrigated",
    35: "Citrus rainfed",                   36: "Citrus irrigated",
    37: "Cocoa rainfed",                    38: "Cocoa irrigated",
    39: "Coffee rainfed",                   40: "Coffee irrigated",
    41: "Cotton rainfed",                   42: "Cotton irrigated",
    43: "Datepalm rainfed",                 44: "Datepalm irrigated",
    45: "Foddergrass rainfed",              46: "Foddergrass irrigated",
    47: "Grapes rainfed",                   48: "Grapes irrigated",
    49: "Groundnuts rainfed",               50: "Groundnuts irrigated",
    51: "Millet rainfed",                   52: "Millet irrigated",
    53: "Oilpalm rainfed",                  54: "Oilpalm irrigated",
    55: "Potatoes rainfed",                 56: "Potatoes irrigated",
    57: "Pulses rainfed",                   58: "Pulses irrigated",
    59: "Rapeseed rainfed",                 60: "Rapeseed irrigated",
    61: "Rice rainfed",                     62: "Rice irrigated",
    63: "Sorghum rainfed",                  64: "Sorghum irrigated",
    65: "Sugarbeet rainfed",                66: "Sugarbeet irrigated",
    67: "Sugarcane rainfed",                68: "Sugarcane irrigated",
    69: "Sunflower rainfed",                70: "Sunflower irrigated",
    71: "Miscanthus rainfed",               72: "Miscanthus irrigated",
    73: "Switchgrass rainfed",              74: "Switchgrass irrigated",
    75: "Tropical corn rainfed",            76: "Tropical corn irrigated",
    77: "Tropical soybean rainfed",         78: "Tropical soybean irrigated",
}

_fetched_natpft, _fetched_cft = _fetch_pft_names_from_docs()
NATPFT_NAMES = _fetched_natpft if _fetched_natpft is not None else _NATPFT_FALLBACK
CFT_NAMES    = _fetched_cft    if _fetched_cft    is not None else _CFT_FALLBACK

N_NAT = 15  # natural PFT indices 0–14


def pft_name(i: int) -> str:
    """Return the human-readable name for PFT index i."""
    return NATPFT_NAMES.get(i) or CFT_NAMES.get(i) or f"PFT {i}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def var_label(ds, v: str) -> str:
    """Return 'varname  [long_name: ..., units: ..., coordinates: ...]'."""
    var = ds.variables[v]
    parts = []
    for attr in ("long_name", "units", "coordinates"):
        val = getattr(var, attr, None)
        if val is not None:
            parts.append(f"{attr}: {val}")
    if parts:
        return f"{v}  [{', '.join(parts)}]"
    return v


def pft_axis(ds, v: str):
    """Return the axis index of the 'pft' dimension, or None."""
    dims = ds.variables[v].dimensions
    return dims.index("pft") if "pft" in dims else None


def idx_label(idx: tuple, ax) -> str:
    """Format an index tuple, appending the PFT name when applicable."""
    idx_str = ",".join(str(i) for i in idx)
    if ax is not None:
        return f"{idx_str} | {pft_name(idx[ax])}"
    return idx_str


def print_var_values(ds, v: str, pft_filter=None) -> None:
    """Print all (filtered) element values of variable v in ds."""
    raw = ds[v][:]
    ax = pft_axis(ds, v)

    # --- char arrays ---
    if raw.dtype.kind in ("S", "U") or raw.dtype == object:
        for i in range(len(raw)):
            if pft_filter is not None and i != pft_filter:
                continue
            s = bytes(raw[i]).rstrip(b" \x00").decode("utf-8", errors="replace")
            print(f"    [{idx_label((i,), ax)}]  '{s}'")
        return

    # --- numeric arrays ---
    try:
        fa = np.ma.filled(raw.astype(float), np.nan)
    except Exception:
        return
    for idx in np.ndindex(fa.shape):
        if pft_filter is not None and ax is not None and idx[ax] != pft_filter:
            continue
        val = fa[idx]
        print(f"    [{idx_label(idx, ax)}]  {val:.8g}")


# ---------------------------------------------------------------------------
# Core comparison
# ---------------------------------------------------------------------------

def compare(path_a: str, path_b: str, pft_filter=None,
            verbose: bool = False, summary: bool = False) -> None:
    ds_a = nc.Dataset(path_a)
    ds_b = nc.Dataset(path_b)

    vars_a = set(ds_a.variables)
    vars_b = set(ds_b.variables)

    if pft_filter is not None:
        print(f"(Filtering to PFT index {pft_filter}: {pft_name(pft_filter)})")

    # ------------------------------------------------------------------
    # 1. Variables only in one file
    # ------------------------------------------------------------------
    only_a = sorted(vars_a - vars_b)
    only_b = sorted(vars_b - vars_a)

    if only_a:
        print(f"\nOnly in {path_a}  ({len(only_a)}):")
        for v in only_a:
            print(f"  {var_label(ds_a, v)}")
            if verbose:
                print_var_values(ds_a, v, pft_filter)
    else:
        print(f"\nNo variables only in {path_a}")

    if only_b:
        print(f"\nOnly in {path_b}  ({len(only_b)}):")
        for v in only_b:
            print(f"  {var_label(ds_b, v)}")
            if verbose:
                print_var_values(ds_b, v, pft_filter)
    else:
        print(f"\nNo variables only in {path_b}")

    # ------------------------------------------------------------------
    # 2. Variables in both — find differences
    # ------------------------------------------------------------------
    diffs = {}   # var -> list of (index_tuple, val_a, val_b)

    for v in sorted(vars_a & vars_b):
        raw_a = ds_a[v][:]
        raw_b = ds_b[v][:]

        ax = pft_axis(ds_a, v)

        # --- char arrays (e.g. pftname) ---
        if raw_a.dtype.kind in ("S", "U") or raw_a.dtype == object:
            rows = []
            for i in range(len(raw_a)):
                if pft_filter is not None and i != pft_filter:
                    continue
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
            if pft_filter is not None and ax is not None and idx[ax] != pft_filter:
                continue
            va = fa[idx] if fa.ndim > 1 else fa[idx[0]]
            vb = fb[idx] if fb.ndim > 1 else fb[idx[0]]
            rows.append((idx, va, vb))
        if rows:
            diffs[v] = rows

    # ------------------------------------------------------------------
    # 3. Report differences
    # ------------------------------------------------------------------
    if not diffs:
        print("\nAll shared variables are identical.")
    else:
        print(f"\nDifferences in shared variables  ({len(diffs)} variable(s)):")
        for v, rows in diffs.items():
            ax = pft_axis(ds_a, v)
            print(f"\n  {var_label(ds_a, v)}  ({len(rows)} element(s))")
            if not summary:
                for idx, va, vb in rows:
                    label = idx_label(idx, ax)
                    if isinstance(va, str):
                        print(f"    [{label}]  '{va}'  →  '{vb}'")
                    else:
                        print(f"    [{label}]  {va:.8g}  →  {vb:.8g}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\nSummary: {len(only_a)} only-in-A  |  {len(only_b)} only-in-B"
          f"  |  {len(diffs)} variables with value differences")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file_a", metavar="FILE_A.nc")
    parser.add_argument("file_b", metavar="FILE_B.nc")
    parser.add_argument("--pft", type=int, metavar="N",
                        help="Only show differences for PFT index N (0-based)")
    parser.add_argument("--verbose", action="store_true",
                        help="Also print element values for variables only in one file")
    parser.add_argument("--summary", action="store_true",
                        help="Print variable headers and counts but suppress element rows "
                             "in the differences section")
    args = parser.parse_args()
    compare(args.file_a, args.file_b, pft_filter=args.pft,
            verbose=args.verbose, summary=args.summary)


if __name__ == "__main__":
    main()
