#!/usr/bin/env bash
#
# Extract a geographic subgrid from eCLM domain and surface data files using CDO.
#
# Both files share the same curvilinear grid (rotated-pole EUR-CORDEX). CDO's
# sellonlatbox identifies the enclosing rectangular index block automatically
# by scanning the 2D coordinate arrays.
#
# The domain file uses CF-standard coordinate variable names (xc, yc), which
# CDO recognises directly. The surface data file uses non-standard names
# (LONGXY, LATIXY), so we borrow the grid description from the domain file
# via -setgrid, giving CDO the coordinate information it needs.
#
# Dependencies
# ------------
#   CDO (Climate Data Operators)
#
# Usage
# -----
#   subset_cdo.sh \
#       --domain    domain.lnd.EUR-0275.nc \
#       --surfdata  surfdata_EUR-0275.nc \
#       --out-domain    domain.lnd.ALP-0275.nc \
#       --out-surfdata  surfdata_ALP-0275.nc \
#       --lon-min 2 --lon-max 17 --lat-min 43 --lat-max 48
#
# Notes
# -----
#   - Longitudes must be given in degrees east in the same convention as the
#     input files (0–360 if the files were post-processed with xc+360).
#   - The output bounding box may be slightly larger than requested because the
#     curvilinear grid is axis-aligned in rotated-pole space, not in geographic
#     space. Cells outside the box retain their original mask/frac values.

set -euo pipefail

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

usage() {
    cat <<EOF
Usage: $(basename "$0") OPTIONS

Required options:
  --domain        Input domain file (NetCDF)
  --surfdata      Input surface data file (NetCDF)
  --out-domain    Output domain file
  --out-surfdata  Output surface data file
  --lon-min       West longitude bound (degrees east)
  --lon-max       East longitude bound (degrees east)
  --lat-min       South latitude bound (degrees north)
  --lat-max       North latitude bound (degrees north)
EOF
    exit 1
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

DOMAIN="" SURFDATA="" OUT_DOMAIN="" OUT_SURFDATA=""
LON_MIN="" LON_MAX="" LAT_MIN="" LAT_MAX=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain)       DOMAIN="$2";       shift 2 ;;
        --surfdata)     SURFDATA="$2";     shift 2 ;;
        --out-domain)   OUT_DOMAIN="$2";   shift 2 ;;
        --out-surfdata) OUT_SURFDATA="$2"; shift 2 ;;
        --lon-min)      LON_MIN="$2";      shift 2 ;;
        --lon-max)      LON_MAX="$2";      shift 2 ;;
        --lat-min)      LAT_MIN="$2";      shift 2 ;;
        --lat-max)      LAT_MAX="$2";      shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$DOMAIN"    || -z "$SURFDATA"     ]] && usage
[[ -z "$OUT_DOMAIN"|| -z "$OUT_SURFDATA" ]] && usage
[[ -z "$LON_MIN"   || -z "$LON_MAX"     ]] && usage
[[ -z "$LAT_MIN"   || -z "$LAT_MAX"     ]] && usage

# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

BBOX="${LON_MIN},${LON_MAX},${LAT_MIN},${LAT_MAX}"

echo ""
echo "Extracting subgrid for lon=[${LON_MIN},${LON_MAX}], lat=[${LAT_MIN},${LAT_MAX}] ..."

# Domain file: CDO recognises the CF-standard xc/yc coordinate variables
# and uses them to locate the enclosing rectangular grid block.
echo ""
echo "Extracting domain file ..."
cdo sellonlatbox,"${BBOX}" "${DOMAIN}" "${OUT_DOMAIN}"

# Surface data file: LONGXY/LATIXY are non-standard names that CDO does not
# recognise automatically. We assign the curvilinear grid from the full-domain
# domain file (-setgrid) so CDO has the coordinate information to apply the
# same geographic selection. Both files share identical grid dimensions.
echo ""
echo "Extracting surface data file ..."
cdo -sellonlatbox,"${BBOX}" \
    -setgrid,"${DOMAIN}" \
    "${SURFDATA}" "${OUT_SURFDATA}"

echo ""
echo "Done."
echo "  Domain  : ${OUT_DOMAIN}"
echo "  Surfdata: ${OUT_SURFDATA}"
