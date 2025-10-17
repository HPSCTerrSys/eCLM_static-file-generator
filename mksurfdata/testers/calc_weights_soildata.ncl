; Program to apply ESMF mapping data on data
;
; ml Stages/2020  Intel/2020.2.254-GCC-9.3.0  ParaStationMPI/5.4.7-1 NCL/6.6.2

load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_code.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_csm.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/contributed.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/esmf/ESMF_regridding.ncl"

begin

; inputfile 
   inFileName = "/p/project1/cslts/poll1/preproc/TSMP_EU11/static.resource/02_Resample/SoilGrid_v2017/mksrf_soitex.10level.nc"

; weightfile 
   wgtFileName = "/p/project1/cslts/poll1/eclm_coupling/CTSM/eu_11_eclm_curvilinear/mkmapdata/map_5x5min_IGBP-GSDP_to_EUR-R13B05_nomask_aave_da_c230629.nc"

; outfile
   outFileName = "soildata_soitex_fNCL.nc"

;----------------------------------------------------------------------
; ReadIn variables to interpolate
;----------------------------------------------------------------------

   src_file = addfile(inFileName,"r")
;    temp     = src_file->MAPUNITS(:,:)
   pct_sand_raw  = src_file->PCT_SAND
   pct_clay_raw  = src_file->PCT_CLAY

;----------------------------------------------------------------------
; Apply the weights to a given variable
;----------------------------------------------------------------------
   Opt                = True
   Opt@PrintTimings   = True

;    temp_regrid = ESMF_regrid_with_weights(temp,wgtFileName,Opt)
;    printVarSummary(temp_regrid)

;   do ilay = 0,9
;     temp_regrid = ESMF_regrid_with_weights(pct_sand_raw,wgtFileName,Opt)
;   end do
    pct_sand = ESMF_regrid_with_weights(pct_sand_raw,wgtFileName,Opt)
    pct_clay = ESMF_regrid_with_weights(pct_clay_raw,wgtFileName,Opt)

;----------------------------------------------------------------------
; Save interpolated files in netcdf (easy method)
;----------------------------------------------------------------------
   ncdf = addfile(outFileName ,"c")  ;
  
   ; create global attributes of the file (optional)
   fAtt               = True            ; assign file attributes
   fAtt@title         = "Soildata for CLM"
   fAtt@source_file   =  "soitex by calc_weights_soildata.ncl"
   fAtt@Conventions   = "None"
   fAtt@contact       = "s.poll@fz-juelich.de"
   fAtt@creation_date = systemfunc ("date")
   fileattdef( ncdf, fAtt )            ; copy file attributes
 
   ; save variables in file 
;  ncdf->mapunit_regrid  = temp_regrid
   ncdf->pct_sand  = pct_sand
   ncdf->pct_clay  = pct_clay

end
