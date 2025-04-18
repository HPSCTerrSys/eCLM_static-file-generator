load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_code.ncl" 
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_csm.ncl" 
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/contributed.ncl" 
load "$NCARG_ROOT/lib/ncarg/nclscripts/esmf/ESMF_regridding.ncl" 
;
OutFileName = "EUR-11_191808_grid_SCRIP.nc"
;Adjust the filename/path to your gridfile and the variable names of lon lat if needed
;
f     = addfile ("EUR-11_444x432_grid_inclbrz13gp_v2.nc", "r")
lat2d = f->lat                        
lon2d = f->lon
;
;
 
Opt                      = True
Opt@InterpMethod         = "conserve"     ; default conserve
Opt@ForceOverwrite       = True
Opt@PrintTimings         = True
;
curvilinear_to_SCRIP(OutFileName,lat2d,lon2d,Opt)


