#!/usr/bin/env bash
set -eo pipefail

# default values of parameters
lrmp=true
lmerge=true
lclm3=false
ompthd=1
# TSMP2/eclm
pathdata=./
wgtcaf=/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_wfe_eur-11u/dta/rmp_gridwgts/wgtdis_era5caf_to_eur11u-189976.nc
wgtmeteo=/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_wfe_eur-11u/dta/rmp_gridwgts/wgtdis_era5meteo_to_eur11u-189976.nc
griddesfile=/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_wfe_eur-11u/dta/rmp_gridwgts/griddes_eur-11u_189976.txt
clm3grid=""
# TSMP1/clm3.5
#pathdata=/p/project/detectlulcc/ferro1/eclm_static_file_workflow/mkforcing/
#wgtcaf=/p/project/detectlulcc/poll1/data/script_remap/wgtdis_era5caf_to_eur11-444x432.nc
#wgtmeteo=/p/project/detectlulcc/poll1/data/script_remap/wgtdis_era5meteo_to_eur11-444x432.nc
#griddesfile=/p/largedata2/detectdata/CentralDB/projects/z04/detect_grid_specs/web_pep_tmp/EUR-11_TSMP_FZJ-IBG3_444x432_webPEP_sub.txt
#clm3grid=/p/scratch/cslts/poll1/sim/EUR-11_ECMWF-ERA5_evaluation_r1i1p1_FZJ-COSMO5-01-CLM3-5-0-ParFlow3-12-0_vEXP/geo/TSMP_EUR-11/static/clm/griddata_CLM_EUR-11_TSMP_FZJ-IBG3_CLMPFLDomain_444x432.nc
iyear=2017
imonth=07
tmpdir=tmpdir
wrkdir=""
author="Stefan POLL"
email="s.poll@fz-juelich.de"

# Function to parse input
parse_arguments() {
    for arg in "$@"; do
        key="${arg%%=*}"
        value="${arg#*=}"

        case "$key" in
            lrmp) lrmp="$value" ;;
            lmerge) lmerge="$value" ;;
            lclm3) lclm3="$value" ;;
            ompthd) ompthd="$value" ;;
            pathdata) pathdata="$value" ;;
            wgtcaf) wgtcaf="$value" ;;
            wgtmeteo) wgtmeteo="$value" ;;
            griddesfile) griddesfile="$value" ;;
            clm3grid) clm3grid="$value" ;;
            tmpdir) tmpdir="$value" ;;
            wrkdir) wrkdir="$value" ;;
            imonth) imonth="$value" ;;
            iyear) iyear="$value" ;;
            author) author="$value" ;;
            email) email="$value" ;;
            *) echo "Warning: Unknown parameter: $key" ;;
        esac
    done
}

# Call the function to parse the input arguments
# Users needs to make sure for consistent input
parse_arguments "$@"

#
#cd $wrkdir
#mkdir -pv $tmpdir

#
for year in ${iyear}
do
for month in ${imonth}
do

  # Go into working directory and create temporary directory
  if [ -z ${wrkdir} ];then
    wrkdir=${iyear}-${imonth}
  fi
  cd $wrkdir
  mkdir -pv $tmpdir

  if $lrmp; then
    unzip ${pathdata}/download_era5_${year}_${month}.zip -d ${tmpdir}
    cdo -P ${ompthd} remap,${griddesfile},${wgtcaf} ${tmpdir}/data_stream-oper_stepType-instant.nc ${tmpdir}/rmp_era5_${year}_${month}_ins.nc
    cdo -P ${ompthd} remap,${griddesfile},${wgtcaf} ${tmpdir}/data_stream-oper_stepType-avg.nc ${tmpdir}/rmp_era5_${year}_${month}_avg.nc
    cdo -P ${ompthd} remap,${griddesfile},${wgtmeteo} ${pathdata}/meteocloud_${year}_${month}.nc ${tmpdir}/rmp_meteocloud_${year}_${month}.nc
  fi

  if $lmerge; then

    cdo -P ${ompthd} expr,'WIND=sqrt(u^2+v^2)' ${tmpdir}/rmp_meteocloud_${year}_${month}.nc ${tmpdir}/${year}_${month}_temp.nc
    cdo -f nc4c const,10,${tmpdir}/rmp_era5_${year}_${month}_avg.nc ${tmpdir}/${year}_${month}_const.nc
    ncpdq -U ${tmpdir}/rmp_era5_${year}_${month}_avg.nc ${tmpdir}/${year}_${month}_temp2.nc
    ncpdq -U ${tmpdir}/rmp_era5_${year}_${month}_ins.nc ${tmpdir}/${year}_${month}_temp7.nc
    cdo selvar,t,q ${tmpdir}/rmp_meteocloud_${year}_${month}.nc ${tmpdir}/${year}_${month}_temp3.nc

    cdo merge ${tmpdir}/${year}_${month}_const.nc ${tmpdir}/${year}_${month}_temp3.nc ${tmpdir}/${year}_${month}_temp2.nc \
              ${tmpdir}/${year}_${month}_temp.nc ${tmpdir}/${year}_${month}_temp7.nc ${tmpdir}/${year}_${month}_temp4.nc

    ncks -C -x -v hyai,hyam,hybi,hybm ${tmpdir}/${year}_${month}_temp4.nc ${tmpdir}/${year}_${month}_temp5.nc
    ncwa -O -a lev ${tmpdir}/${year}_${month}_temp5.nc ${year}-${month}.nc

    ncrename -v sp,PSRF -v avg_sdswrf,FSDS -v avg_sdlwrf,FLDS -v avg_tprate,PRECTmms -v const,ZBOT -v t,TBOT -v q,QBOT ${year}-${month}.nc
#    ncap2 -O -s 'where(FSDS<0.) FSDS=0' ${year}_${month}.nc
    ncatted -O -a units,ZBOT,m,c,"m" ${year}-${month}.nc

    ncks -O -h --glb author="${author}" ${year}-${month}.nc
    ncks -O -h --glb contact="${email}" ${year}-${month}.nc

    rm ${tmpdir}/${year}_${month}_temp*nc ${tmpdir}/${year}_${month}_const.nc
  fi

  ## adaptation for CLM3.5
  if $lclm3; then

    mv ${year}-${month}.nc ${year}_${month}_tmp.nc

    ## CLM3.5
    ncrename -v lon,LONGXY ${year}_${month}_tmp.nc
    ncrename -v lat,LATIXY ${year}_${month}_tmp.nc

    #
    cdo selvar,LONE,LATN,LONW,LATS,AREA,EDGEE,EDGEN,EDGEW,EDGES ${clm3grid} ${tmpdir}/${year}_${month}_temp11.nc
    cdo -O merge ${tmpdir}/${year}_${month}_temp11.nc ${year}_${month}_tmp.nc ${year}-${month}.nc

    ncrename -d rlon,lon ${year}-${month}.nc
    ncrename -d rlat,lat ${year}-${month}.nc

    ncks -O -h --glb author="${author}" ${year}-${month}.nc
    ncks -O -h --glb contact="${email}" ${year}-${month}.nc

    #
    rm ${year}_${month}_tmp.nc ${tmpdir}/${year}_${month}_temp11.nc

  fi

done
done

