#!/usr/bin/env bash
#
# Extract a geographic subgrid from an eCLM atmospheric forcing file using CDO.
#
# Forcing files share the same curvilinear rotated-pole grid as the domain and
# surface data files (rlon=1592, rlat=1544 for EUR-0275). CDO's sellonlatbox
# identifies the enclosing rectangular index block automatically.
#
# Unlike the domain/surfdata case, no workarounds are needed here:
#   - The geographic coordinate variables are named lon and lat (CF-standard),
#     so CDO recognises them without a -setgrid step.
#   - All data variables have shape (time, rlat, rlon), which fits CDO's data
#     model, so no variables are dropped.
#
# All time steps are preserved; only the spatial dimensions are subsetted.
#
# Dependencies
# ------------
#   CDO (Climate Data Operators)
#
# Usage
# -----
#   subset_forcing_cdo.sh \
#       --input  2022-01.nc \
#       --output 2022-01_ALP-0275.nc \
#       --lon-min 2 --lon-max 17 --lat-min 43 --lat-max 48
#
# Notes
# -----
#   - Longitudes must be given in degrees east in the same convention as the
#     input file.
#   - The output bounding box may be slightly larger than requested because the
#     curvilinear grid is axis-aligned in rotated-pole space, not in geographic
#     space. Out-of-box cells retain their original fill values.
#   - The 1D rotated-pole axes rlon(rlon) and rlat(rlat) and the rotated_pole
#     scalar grid-mapping variable are preserved automatically by CDO.

set -euo pipefail

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

usage() {
    cat <<EOF
Usage: $(basename "$0") OPTIONS

Required options:
  --input     Input forcing file (NetCDF)
  --output    Output forcing file
  --lon-min   West longitude bound (degrees east)
  --lon-max   East longitude bound (degrees east)
  --lat-min   South latitude bound (degrees north)
  --lat-max   North latitude bound (degrees north)
EOF
    exit 1
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

INPUT="" OUTPUT=""
LON_MIN="" LON_MAX="" LAT_MIN="" LAT_MAX=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input)    INPUT="$2";    shift 2 ;;
        --output)   OUTPUT="$2";   shift 2 ;;
        --lon-min)  LON_MIN="$2";  shift 2 ;;
        --lon-max)  LON_MAX="$2";  shift 2 ;;
        --lat-min)  LAT_MIN="$2";  shift 2 ;;
        --lat-max)  LAT_MAX="$2";  shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$INPUT"   || -z "$OUTPUT"  ]] && usage
[[ -z "$LON_MIN" || -z "$LON_MAX" ]] && usage
[[ -z "$LAT_MIN" || -z "$LAT_MAX" ]] && usage

# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

BBOX="${LON_MIN},${LON_MAX},${LAT_MIN},${LAT_MAX}"

echo ""
echo "Extracting subgrid for lon=[${LON_MIN},${LON_MAX}], lat=[${LAT_MIN},${LAT_MAX}] ..."
echo ""

# CDO recognises lon/lat as CF-standard coordinate variables and uses them to
# locate the enclosing rectangular grid block. The rotated-pole grid mapping
# (rotated_pole scalar variable) is preserved in the output.
cdo sellonlatbox,"${BBOX}" "${INPUT}" "${OUTPUT}"

echo ""
echo "Done."
echo "  Output: ${OUTPUT}"
