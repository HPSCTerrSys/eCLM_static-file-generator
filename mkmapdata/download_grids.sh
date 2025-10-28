#!/bin/bash -l

### URL base for the grids
SVNBASE="https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/lnd/clm2/mappingdata/grids"

### Local directory 
myraw="$PWD/download_grids"
mkdir -p "$myraw"

### List of files to download
files=(
  SCRIPgrid_0.5x0.5_AVHRR_c110228.nc
  SCRIPgrid_0.25x0.25_MODIS_c170321.nc
  SCRIPgrid_3minx3min_LandScan2004_c120517.nc
  SCRIPgrid_3minx3min_MODISv2_c190503.nc
  SCRIPgrid_3minx3min_MODISwcspsea_c151020.nc
  SCRIPgrid_3x3_USGS_c120912.nc
  SCRIPgrid_5x5min_nomask_c110530.nc
  SCRIPgrid_5x5min_IGBP-GSDP_c110228.nc
  SCRIPgrid_5x5min_ISRIC-WISE_c111114.nc
  SCRIPgrid_5x5min_ORNL-Soil_c170630.nc
  SCRIPgrid_10x10min_nomask_c110228.nc
  SCRIPgrid_10x10min_IGBPmergeICESatGIS_c110818.nc
  SCRIPgrid_3minx3min_GLOBE-Gardner_c120922.nc
  SCRIPgrid_3minx3min_GLOBE-Gardner-mergeGIS_c120922.nc
  SCRIPgrid_0.9x1.25_GRDC_c130307.nc
  SCRIPgrid_360x720_cruncep_c120830.nc
  UGRID_1km-merge-10min_HYDRO1K-merge-nomask_c130402.nc
)

echo "Downloading grid files to $myraw ..."
for file in "${files[@]}"; do
  localf="${myraw}/${file}"
  url="${SVNBASE}/${file}"
  if [ ! -f "$localf" ]; then
    echo "Downloading $file ..."
    # wget -O "$localf" "$url" || { echo "ERROR downloading $url"; exit 1; }
    svn export "$url" "$localf" || { echo "ERROR exporting $url"; exit 1; }
  else
    echo "File $file already exists — skipping download."
  fi
done
