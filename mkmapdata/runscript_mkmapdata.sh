#!/bin/bash -x
#SBATCH --account=slts
#SBATCH --nodes=1
#SBATCH --ntasks=48
#SBATCH --ntasks-per-node=48
#SBATCH --output=mpi-out.%j
#SBATCH --error=mpi-err.%j
#SBATCH --time=00:30:00
#SBATCH --partition=mem192


# load enviroment

module load Stages/2024 Intel/2023.2.1 ParaStationMPI/5.9.2-1 ESMF/8.5.0
module load netCDF
module load netCDF-Fortran

#export ESMFBIN_PATH="/p/software/$SYSTEMNAME/stages/2022/software/ESMF/8.2.0-gpsmkl-2021b/bin/"
export ESMFBIN_PATH="${EBROOTESMF}/bin/"

### adjust your gridfile here
export GRIDNAME=EUR-11
export CDATE=`date +%y%m%d`
export GRIDFILE="../mkmapgrids/SCRIP_EUR11.nc"
###

### Path to the raw files downloaded for the clm website
rawpath="/p/scratch/cslts/poll1/data/rawdata/clm5/mkmapdata/"
###

OUTPUT="$PWD"

### loop over all input files
for file in SCRIPgrid_0.5x0.5_AVHRR_c110228.nc SCRIPgrid_0.25x0.25_MODIS_c170321.nc SCRIPgrid_3minx3min_LandScan2004_c120517.nc SCRIPgrid_3minx3min_MODISv2_c190503.nc SCRIPgrid_3minx3min_MODISwcspsea_c151020.nc SCRIPgrid_3x3_USGS_c120912.nc SCRIPgrid_5x5min_nomask_c110530.nc SCRIPgrid_5x5min_IGBP-GSDP_c110228.nc SCRIPgrid_5x5min_ISRIC-WISE_c111114.nc SCRIPgrid_5x5min_ORNL-Soil_c170630.nc SCRIPgrid_10x10min_nomask_c110228.nc SCRIPgrid_10x10min_IGBPmergeICESatGIS_c110818.nc SCRIPgrid_3minx3min_GLOBE-Gardner_c120922.nc SCRIPgrid_3minx3min_GLOBE-Gardner-mergeGIS_c120922.nc SCRIPgrid_0.9x1.25_GRDC_c130307.nc SCRIPgrid_360x720_cruncep_c120830.nc UGRID_1km-merge-10min_HYDRO1K-merge-nomask_c130402.nc
do

OUTFILE=map_${file}_to_${GRIDNAME}_nomask_aave_da_c$CDATE.nc

srun $ESMFBIN_PATH/./ESMF_RegridWeightGen --ignore_unmapped -s ${rawpath}/${file} -d  $GRIDFILE -m conserve -w ${OUTPUT}/${OUTFILE} --dst_regional --netcdf4

done

### rename output
mv map_SCRIPgrid_3minx3min_GLOBE-Gardner_c120922.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_3x3min_GLOBE-Gardner_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_3minx3min_LandScan2004_c120517.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_3x3min_LandScan2004_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_3minx3min_MODISv2_c190503.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_3x3min_MODISv2_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_3minx3min_MODISwcspsea_c151020.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_3x3min_MODIS-wCsp_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_3x3_USGS_c120912.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_3x3min_USGS_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_3minx3min_GLOBE-Gardner-mergeGIS_c120922.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_3x3min_GLOBE-Gardner-mergeGIS_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_0.5x0.5_AVHRR_c110228.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_0.5x0.5_AVHRR_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_0.25x0.25_MODIS_c170321.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_0.25x0.25_MODIS_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_5x5min_nomask_c110530.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_5x5min_nomask_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_5x5min_IGBP-GSDP_c110228.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_5x5min_IGBP-GSDP_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_5x5min_ISRIC-WISE_c111114.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_5x5min_ISRIC-WISE_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_5x5min_ORNL-Soil_c170630.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_5x5min_ORNL-Soil_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_10x10min_nomask_c110228.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_10x10min_nomask_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_10x10min_IGBPmergeICESatGIS_c110818.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_10x10min_IGBPmergeICESatGIS_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_0.9x1.25_GRDC_c130307.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_0.9x1.25_GRDC_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_SCRIPgrid_360x720_cruncep_c120830.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_360x720_cruncep_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc

mv map_UGRID_1km-merge-10min_HYDRO1K-merge-nomask_c130402.nc_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc map_1km-merge-10min_HYDRO1K-merge-nomask_to_${GRIDNAME}_nomask_aave_da_c${CDATE}.nc





