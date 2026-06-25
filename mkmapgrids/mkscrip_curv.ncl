load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_code.ncl" 
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_csm.ncl" 
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/contributed.ncl" 
load "$NCARG_ROOT/lib/ncarg/nclscripts/esmf/ESMF_regridding.ncl" 
;
; Create a SCRIP file from a curvilinear grid.
;
; Variables can be passed on the command line, e.g.:
;   ncl 'ifile="mygrid.nc"' 'ofile="mygrid_SCRIP.nc"' mkscrip_curv.ncl
;
; Defaults (edit here for interactive use):
if (.not. isvar("ifile")) then
    ifile = "EUR-11_444x432_grid_inclbrz13gp_v2.nc"
end if
if (.not. isvar("ofile")) then
    ofile = "EUR-11_191808_grid_SCRIP.nc"
end if
if (.not. isvar("latvar")) then
    latvar = "lat"
end if
if (.not. isvar("lonvar")) then
    lonvar = "lon"
end if

f     = addfile(ifile, "r")
lat2d = f->$latvar$
lon2d = f->$lonvar$

Opt                      = True
Opt@InterpMethod         = "conserve"     ; default conserve
Opt@ForceOverwrite       = True
Opt@PrintTimings         = True

curvilinear_to_SCRIP(ofile, lat2d, lon2d, Opt)
