#!/usr/bin/env bash
set -euo pipefail

BASEDIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
    cat <<EOF
Usage: $0 --grid NAME --account ACCOUNT --partition PARTITION [OPTIONS]

Create all eCLM static files for a given grid in one go.

Required arguments:
  --grid        Grid name (used in output filenames)
  --account     SLURM account/project
  --partition   SLURM partition (e.g. mem192)

Grid type (default: rect):
  --grid-type   Grid type: rect, curv, or icos

For --grid-type rect (rectilinear, default):
  --slat        South latitude  [-90, 90]
  --nlat        North latitude  [-90, 90]
  --elon        East longitude  [0, 360)
  --wlon        West longitude  [0, 360)
  --nx          Number of grid points along longitude
  --ny          Number of grid points along latitude
  --imask       Mask type (default: 1; 1=nomask, 0=noocean)

For --grid-type curv (curvilinear):
  --gridfile    Path to input netCDF file with 2D lat/lon
  --latvar      Name of latitude variable (default: lat)
  --lonvar      Name of longitude variable (default: lon)
  Requires a Conda environment named NCL_environment with NCL installed.

For --grid-type icos (icosahedral/triangular):
  --gridfile    Path to input ICON grid file (netCDF)

Environment variables:
  CSMDATA    Path to CLM raw data (required)
EOF
    exit 1
}

# --- Parse arguments ---
GRIDNAME="" GRID_TYPE="rect"
S_LAT="" N_LAT="" E_LON="" W_LON="" NX="" NY="" IMASK=1
GRIDFILE="" LATVAR="lat" LONVAR="lon"
ACCOUNT="" PARTITION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --grid)       GRIDNAME="$2";   shift 2 ;;
        --grid-type)  GRID_TYPE="$2";  shift 2 ;;
        --slat)       S_LAT="$2";      shift 2 ;;
        --nlat)       N_LAT="$2";      shift 2 ;;
        --elon)       E_LON="$2";      shift 2 ;;
        --wlon)       W_LON="$2";      shift 2 ;;
        --nx)         NX="$2";         shift 2 ;;
        --ny)         NY="$2";         shift 2 ;;
        --imask)      IMASK="$2";      shift 2 ;;
        --gridfile)   GRIDFILE="$2";   shift 2 ;;
        --latvar)     LATVAR="$2";     shift 2 ;;
        --lonvar)     LONVAR="$2";     shift 2 ;;
        --account)    ACCOUNT="$2";    shift 2 ;;
        --partition)  PARTITION="$2";  shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown argument: $1"; usage ;;
    esac
done

# --- Validate common required arguments ---
for var in GRIDNAME ACCOUNT PARTITION; do
    if [[ -z "${!var}" ]]; then
        echo "Error: --$(echo "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-') is required"
        usage
    fi
done

if [[ -z "${CSMDATA:-}" ]]; then
    echo "Error: CSMDATA environment variable must be set"
    exit 1
fi

# --- Validate grid-type-specific arguments ---
case "$GRID_TYPE" in
    rect)
        for var in S_LAT N_LAT E_LON W_LON NX NY; do
            if [[ -z "${!var}" ]]; then
                echo "Error: --$(echo "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-') is required for --grid-type rect"
                usage
            fi
        done
        ;;
    curv|icos)
        if [[ -z "$GRIDFILE" ]]; then
            echo "Error: --gridfile is required for --grid-type $GRID_TYPE"
            usage
        fi
        if [[ ! -f "$GRIDFILE" ]]; then
            echo "Error: gridfile not found: $GRIDFILE"
            exit 1
        fi
        ;;
    *)
        echo "Error: unknown --grid-type '$GRID_TYPE' (must be rect, curv, or icos)"
        usage
        ;;
esac

CDATE="$(date +%y%m%d)"

echo "=== eCLM static file generation ==="
echo "Grid: $GRIDNAME  (type: $GRID_TYPE)"

# ============================================================
# Step 1: Create grid file
# ============================================================
echo ""
echo "=== Step 1: Creating SCRIP grid file ==="

if [[ "$IMASK" -eq 0 ]]; then
    GRIDFILE_SUFFIX="noocean"
elif [[ "$IMASK" -eq 1 ]]; then
    GRIDFILE_SUFFIX="nomask"
else
    GRIDFILE_SUFFIX="mask"
fi
SCRIP_OUTFILE="SCRIPgrid_${GRIDNAME}_${GRIDFILE_SUFFIX}_c${CDATE}.nc"
SCRIP_OUTPATH="$BASEDIR/mkmapgrids/$SCRIP_OUTFILE"

case "$GRID_TYPE" in
    rect)
        echo "Grid: ${NX}x${NY}, lat ${S_LAT}..${N_LAT}, lon ${W_LON}..${E_LON}"
        (
            cd "$BASEDIR/mkmapgrids"
            PTNAME="$GRIDNAME" S_LAT="$S_LAT" N_LAT="$N_LAT" E_LON="$E_LON" W_LON="$W_LON" \
            NX="$NX" NY="$NY" IMASK="$IMASK" PRINT="TRUE" \
            python mkscripgrid.py
r        )
        ;;
    curv)
        echo "Curvilinear grid from: $GRIDFILE"
        (
            cd "$BASEDIR/mkmapgrids"
            GRIDFILE_ABS="$(realpath "$GRIDFILE")"
            conda run -n NCL_environment ncl \
                "ifile=\"${GRIDFILE_ABS}\"" \
                "ofile=\"${SCRIP_OUTPATH}\"" \
                "latvar=\"${LATVAR}\"" \
                "lonvar=\"${LONVAR}\"" \
                mkscrip_curv.ncl
        )
        ;;
    icos)
        echo "Icosahedral grid from: $GRIDFILE"
        (
            cd "$BASEDIR/mkmapgrids"
            python mkscrip_icos.py \
                --ifile "$GRIDFILE" \
                --ofile "$SCRIP_OUTPATH" \
                --overwrite
        )
        ;;
esac

if [[ ! -f "$SCRIP_OUTPATH" ]]; then
    echo "Error: Expected grid file not found: $SCRIP_OUTPATH"
    exit 1
fi
echo "Step 1 complete: $SCRIP_OUTPATH"

# ============================================================
# Step 2: Create mapping files
# ============================================================
echo ""
echo "=== Step 2: Creating mapping files (SLURM job) ==="

TMPSCRIPT="$(mktemp "$BASEDIR/mkmapdata/runscript_mkmapdata_tmp_XXXX.sh")"
sed -e "s|^export GRIDNAME=.*|export GRIDNAME=\"${GRIDNAME}\"|" \
    -e "s|^export GRIDFILE=.*|export GRIDFILE=\"${SCRIP_OUTPATH}\"|" \
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
echo "Grid file:    $SCRIP_OUTPATH"
echo "Domain file:  $DOMAIN_LND"
echo "Surface file: $SURFFILE"
