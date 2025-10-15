#!/usr/bin/env bash

# switches
lrmp=false #true
lmerge=true #false
lclm3=true

# 
pathdata=/p/project1/detectlulcc/ferro1/eclm_static_file_workflow/mkforcing/
wgtcaf=/p/project1/detectlulcc/poll1/data/script_remap/wgtdis_era5caf_to_eur11-444x432.nc
wgtmeteo=/p/project1/detectlulcc/poll1/data/script_remap/wgtdis_era5meteo_to_eur11-444x432.nc
griddesfile=/p/largedata2/detectdata/projects/Z04/detect_grid_specs/web_pep_tmp/griddes_EUR-11_TSMP_FZJ-IBG3_444x432_webPEP_sub.txt
clm3grid=/p/scratch/cslts/poll1/sim/EUR-11_ECMWF-ERA5_evaluation_r1i1p1_FZJ-COSMO5-01-CLM3-5-0-ParFlow3-12-0_vEXP/geo/TSMP_EUR-11/static/clm/griddata_CLM_EUR-11_TSMP_FZJ-IBG3_CLMPFLDomain_444x432.nc
tmpdir=tmp_data

# 
author="Stefan POLL"
email="s.poll@fz-juelich.de"

#
mkdir -pv $tmpdir

#
for year in 2017
do
for month in 01 #02 03 04 05 06 07 08 09 10 11 12 
do

  if $lrmp; then
    cdo remap,${griddesfile},${wgtcaf} ${pathdata}/era5_${year}_${month}.nc ${tmpdir}/rmp_era5_${year}_${month}.nc
    cdo remap,${griddesfile},${wgtmeteo} ${pathdata}/meteocloud_${year}_${month}.nc ${tmpdir}/rmp_meteocloud_${year}_${month}.nc
  fi

  if $lmerge; then

    cdo expr,'WIND=sqrt(u^2+v^2)' ${tmpdir}/rmp_meteocloud_${year}_${month}.nc ${tmpdir}/${year}_${month}_temp.nc
    cdo -f nc4c const,10,${tmpdir}/rmp_era5_${year}_${month}.nc ${tmpdir}/${year}_${month}_const.nc
    ncpdq -U ${tmpdir}/rmp_era5_${year}_${month}.nc ${tmpdir}/${year}_${month}_temp2.nc
    cdo selvar,t,q ${tmpdir}/rmp_meteocloud_${year}_${month}.nc ${tmpdir}/${year}_${month}_temp3.nc

    cdo merge ${tmpdir}/${year}_${month}_const.nc ${tmpdir}/${year}_${month}_temp3.nc ${tmpdir}/${year}_${month}_temp2.nc ${tmpdir}/${year}_${month}_temp.nc ${tmpdir}/${year}_${month}_temp4.nc

    ncks -C -x -v hyai,hyam,hybi,hybm ${tmpdir}/${year}_${month}_temp4.nc ${tmpdir}/${year}_${month}_temp5.nc
    ncwa -O -a lev ${tmpdir}/${year}_${month}_temp5.nc ${year}_${month}.nc

    ncrename -v sp,PSRF -v msdwswrf,FSDS -v msdwlwrf,FLDS -v mtpr,PRECTmms -v const,ZBOT -v t,TBOT -v q,SHUM ${year}_${month}.nc
#    ncap2 -O -s 'where(FSDS<0.) FSDS=0' ${year}_${month}.nc
    ncatted -O -a units,ZBOT,m,c,"m" ${year}_${month}.nc

    ncatted -O -h -a author,global,m,c,${author} ${year}_${month}.nc
    ncatted -O -h -a contact,global,m,c,${email} ${year}_${month}.nc

    rm ${tmpdir}/${year}_${month}_temp*nc ${tmpdir}/${year}_${month}_const.nc
  fi

  ## adaptation for CLM3.5
  if $lclm3; then

    cp ${year}_${month}.nc ${year}_${month}_tmp.nc

    ## CLM3.5
    ncrename -v lon,LONGXY ${year}_${month}_tmp.nc
    ncrename -v lat,LATIXY ${year}_${month}_tmp.nc
    ncrename -v SHUM,QBOT ${year}_${month}_tmp.nc

    # 
    cdo selvar,LONE,LATN,LONW,LATS,AREA,EDGEE,EDGEN,EDGEW,EDGES ${clm3grid} ${tmpdir}/${year}_${month}_temp11.nc
    cdo -O merge ${tmpdir}/${year}_${month}_temp11.nc ${year}_${month}_tmp.nc ${year}-${month}.nc

    ncrename -d rlon,lon ${year}-${month}.nc
    ncrename -d rlat,lat ${year}-${month}.nc

    ncatted -O -h -a author,global,m,c,${author} ${year}-${month}.nc
    ncatted -O -h -a contact,global,m,c,${email} ${year}-${month}.nc

    # 
    rm ${year}_${month}_tmp.nc ${tmpdir}/${year}_${month}_temp11.nc

  fi

done
done

