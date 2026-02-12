#!/usr/bin/env bash
set -euo pipefail

BASEDIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
    cat <<EOF
Usage: $0 --ptname NAME --slat S_LAT --nlat N_LAT --elon E_LON --wlon W_LON --nx NX --ny NY --account ACCOUNT --partition PARTITION [--imask IMASK]

Create all eCLM static files for a rectilinear grid in one go.

Required arguments (passed to mkscripgrid.py):
  --ptname      Grid name
  --slat        South latitude  [-90, 90]
  --nlat        North latitude  [-90, 90]
  --elon        East longitude  [0, 360)
  --wlon        West longitude  [0, 360)
  --nx          Number of grid points along longitude
  --ny          Number of grid points along latitude

Required SLURM arguments (for mapping file creation):
  --account     SLURM account/project
  --partition   SLURM partition (e.g. mem192)

Optional:
  --imask       Mask type (default: 1, 1=nomask, 0=noocean)

Environment variables:
  CSMDATA    Path to CLM raw data (required)
EOF
    exit 1
}

# --- Parse arguments ---
PTNAME="" S_LAT="" N_LAT="" E_LON="" W_LON="" NX="" NY="" IMASK=1
ACCOUNT="" PARTITION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ptname) PTNAME="$2"; shift 2 ;;
        --slat)   S_LAT="$2";  shift 2 ;;
        --nlat)   N_LAT="$2";  shift 2 ;;
        --elon)   E_LON="$2";  shift 2 ;;
        --wlon)   W_LON="$2";  shift 2 ;;
        --nx)     NX="$2";     shift 2 ;;
        --ny)     NY="$2";     shift 2 ;;
        --imask)     IMASK="$2";     shift 2 ;;
        --account)   ACCOUNT="$2";   shift 2 ;;
        --partition) PARTITION="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown argument: $1"; usage ;;
    esac
done

for var in PTNAME S_LAT N_LAT E_LON W_LON NX NY ACCOUNT PARTITION; do
    if [[ -z "${!var}" ]]; then
        echo "Error: --$(echo $var | tr '[:upper:]' '[:lower:]' | tr '_' '-') is required"
        usage
    fi
done

if [[ -z "${CSMDATA:-}" ]]; then
    echo "Error: CSMDATA environment variable must be set"
    exit 1
fi

GRIDNAME="$PTNAME"
CDATE="$(date +%y%m%d)"

echo "=== eCLM static file generation ==="
echo "Grid: $GRIDNAME  (${NX}x${NY}, lat ${S_LAT}..${N_LAT}, lon ${W_LON}..${E_LON})"

# ============================================================
# Step 1: Create grid file
# ============================================================
echo ""
echo "=== Step 1: Creating SCRIP grid file ==="

GRIDFILE="SCRIPgrid_${GRIDNAME}_nomask_c${CDATE}.nc"
if [[ "$IMASK" -eq 0 ]]; then
    GRIDFILE="SCRIPgrid_${GRIDNAME}_noocean_c${CDATE}.nc"
elif [[ "$IMASK" -ne 1 ]]; then
    GRIDFILE="SCRIPgrid_${GRIDNAME}_mask_c${CDATE}.nc"
fi

(
    cd "$BASEDIR/mkmapgrids"
    PTNAME="$PTNAME" S_LAT="$S_LAT" N_LAT="$N_LAT" E_LON="$E_LON" W_LON="$W_LON" \
    NX="$NX" NY="$NY" IMASK="$IMASK" PRINT="TRUE" \
    python mkscripgrid.py
)

GRIDFILE_PATH="$BASEDIR/mkmapgrids/$GRIDFILE"
if [[ ! -f "$GRIDFILE_PATH" ]]; then
    echo "Error: Expected grid file not found: $GRIDFILE_PATH"
    exit 1
fi
echo "Step 1 complete: $GRIDFILE_PATH"

# ============================================================
# Step 2: Create mapping files
# ============================================================
echo ""
echo "=== Step 2: Creating mapping files (SLURM job) ==="

TMPSCRIPT="$(mktemp "$BASEDIR/mkmapdata/runscript_mkmapdata_tmp_XXXX.sh")"
sed -e "s|^export GRIDNAME=.*|export GRIDNAME=\"${GRIDNAME}\"|" \
    -e "s|^export GRIDFILE=.*|export GRIDFILE=\"${GRIDFILE_PATH}\"|" \
    -e "s|^#SBATCH --account=.*|#SBATCH --account=${ACCOUNT}|" \
    -e "s|^#SBATCH --partition=.*|#SBATCH --partition=${PARTITION}|" \
    "$BASEDIR/mkmapdata/runscript_mkmapdata.sh" > "$TMPSCRIPT"

(cd "$BASEDIR/mkmapdata" && sbatch --wait "$TMPSCRIPT") || {
    rm -f "$TMPSCRIPT"
    echo "Error: SLURM job for mapping files failed"
    exit 1
}
rm -f "$TMPSCRIPT"

MAPCOUNT=$(find "$BASEDIR/mkmapdata" -maxdepth 1 -name "map_*_to_${GRIDNAME}_*_c${CDATE}.nc" | wc -l)
if [[ "$MAPCOUNT" -eq 0 ]]; then
    echo "Error: No mapping files produced in mkmapdata/"
    exit 1
fi
echo "Step 2 complete: $MAPCOUNT mapping files created"

# ============================================================
# Step 3: Create domain file
# ============================================================
echo ""
echo "=== Step 3: Creating domain files ==="

GEN_DOMAIN="$BASEDIR/gen_domain_files/gen_domain"
if [[ ! -x "$GEN_DOMAIN" ]]; then
    echo "Compiling gen_domain..."
    gfortran -o "$GEN_DOMAIN" "$BASEDIR/gen_domain_files/src/gen_domain.F90" \
        -I"${INC_NETCDF}" -lnetcdff -lnetcdf
fi

MAPFILE="$(find "$BASEDIR/mkmapdata" -maxdepth 1 -name "map_0.5x0.5_AVHRR_to_${GRIDNAME}_*_c${CDATE}.nc" | head -1)"
if [[ -z "$MAPFILE" ]]; then
    MAPFILE="$(find "$BASEDIR/mkmapdata" -maxdepth 1 -name "map_*_to_${GRIDNAME}_*_c${CDATE}.nc" | head -1)"
fi
MAPFILE="$(realpath "$MAPFILE")"

(
    cd "$BASEDIR/gen_domain_files"
    ./gen_domain -m "$MAPFILE" -o "$GRIDNAME" -l "$GRIDNAME" -u "$USER"
)

DOMAIN_LND="$(find "$BASEDIR/gen_domain_files" -maxdepth 1 -name "domain.lnd.${GRIDNAME}_${GRIDNAME}.*.nc" -newer "$MAPFILE" | head -1)"
DOMAIN_OCN="$(find "$BASEDIR/gen_domain_files" -maxdepth 1 -name "domain.ocn.${GRIDNAME}_${GRIDNAME}.*.nc" -newer "$MAPFILE" | head -1)"

if [[ -z "$DOMAIN_LND" || -z "$DOMAIN_OCN" ]]; then
    echo "Error: Domain files not created"
    exit 1
fi

# Swap lnd and ocn (gen_domain uses ocean convention: 0=land, 1=ocean)
mv "$DOMAIN_LND" "$DOMAIN_LND.tmp"
mv "$DOMAIN_OCN" "$DOMAIN_LND"
mv "$DOMAIN_LND.tmp" "$DOMAIN_OCN"

echo "Step 3 complete: domain files created and swapped"

# ============================================================
# Step 4: Create surface file
# ============================================================
echo ""
echo "=== Step 4: Creating surface file ==="

MKSURFDATA_MAP="$BASEDIR/mksurfdata/mksurfdata_map"
if [[ ! -x "$MKSURFDATA_MAP" ]]; then
    echo "Compiling mksurfdata_map..."
    (cd "$BASEDIR/mksurfdata/src" && gmake)
fi

(
    cd "$BASEDIR/mksurfdata"
    ./mksurfdata.pl -r usrspec -usr_gname "$GRIDNAME" -usr_gdate "$CDATE" \
        -l "$CSMDATA" -allownofile -y 2005 -hirespft
        # -usr_mapdir "../mkmapdata/" -no-crop \
        # -pft_idx 13 -pft_frc 100 -soil_cly 60 -soil_col 10 -soil_fmx 0.5 -soil_snd 40
)

SURFFILE="$(find "$BASEDIR/mksurfdata" -maxdepth 1 -name "surfdata_${GRIDNAME}_*_c${CDATE}.nc" | head -1)"
if [[ -z "$SURFFILE" ]]; then
    echo "Error: Surface data file not created"
    exit 1
fi
echo "Step 4 complete: $SURFFILE"

# # ============================================================
# # Step 5: Fix negative longitudes
# # ============================================================
# echo ""
# echo "=== Step 5: Fixing longitudes ==="

# # Surface file
# ncap2 -O -s 'where(LONGXY<0) LONGXY=LONGXY+360' "$SURFFILE" "$SURFFILE.tmp"
# mv "$SURFFILE.tmp" "$SURFFILE"

# # Domain file
# ncap2 -O -s 'where(xc<0) xc=xc+360' "$DOMAIN_LND" "$DOMAIN_LND.tmp"
# ncap2 -O -s 'where(xv<0) xv=xv+360' "$DOMAIN_LND.tmp" "$DOMAIN_LND"
# rm -f "$DOMAIN_LND.tmp"

# echo "Step 5 complete"

# ============================================================
echo ""
echo "=== All done ==="
echo "Grid file:    $GRIDFILE_PATH"
echo "Domain file:  $DOMAIN_LND"
echo "Surface file: $SURFFILE"
