# mkcropsite – Crop-site surface data generator

`mkcropsite.py` converts a CLM single-site surface data NetCDF file
into a uniform agricultural field configuration by applying three
modifications:

1. **Land cover** – sets `PCT_CROP = 100 %`; clears natural vegetation, lake,
   wetland, glacier, and urban landunits.
2. **Natural PFT** – sets the natural vegetation landunit to 100 % C3
   non-arctic grass (`natpft` index 13).  This landunit carries zero weight
   after step 1, but is kept internally consistent.
3. **Crop type** – sets a single user-chosen Crop Functional Type (CFT) to
   100 % of the crop landunit; all other CFTs are zeroed out.

A sanity check rejects regional (multi-cell) files – only single-site files
(`lsmlat = lsmlon = 1`) are accepted.

## Usage

```bash
python mkcropsite.py <surfdata.nc> --crop-type <CFT> [-o output.nc]
```

### Arguments

| Argument            | Description                                                                                            |
|---------------------|--------------------------------------------------------------------------------------------------------|
| `surfdata.nc`       | Input CLM5 single-site surface data file                                                               |
| `--crop-type <CFT>` | Crop type as CFT global index (15–78) **or** a case-insensitive name substring (e.g. `"winter wheat"`) |
| `-o output.nc`      | Output file path (default: `<input_stem>_<crop_name>.nc` next to the input)                            |
| `--list-crops`      | Print all CFT types present in the file and exit                                                       |

### Examples

```bash
# Winter wheat rainfed (CFT index 21) – specify by index:
python mkcropsite.py surfdata.nc --crop-type 21

# Same, but specify by name:
python mkcropsite.py surfdata.nc --crop-type "winter wheat rainfed"

# Spring wheat, custom output name:
python mkcropsite.py surfdata.nc --crop-type 19 -o surfdata_springwheat.nc

# List all CFT types available in the file:
python mkcropsite.py surfdata.nc --list-crops
```

## CFT index reference (BGC mode, 64 CFTs)

| Index | Name                      | Index | Name                        |
|-------|---------------------------|-------|-----------------------------|
| 15    | C3 unmanaged rainfed      | 16    | C3 unmanaged irrigated      |
| 17    | Temperate corn rainfed    | 18    | Temperate corn irrigated    |
| 19    | Spring wheat rainfed      | 20    | Spring wheat irrigated      |
| 21    | Winter wheat rainfed      | 22    | Winter wheat irrigated      |
| 23    | Temperate soybean rainfed | 24    | Temperate soybean irrigated |
| 25    | Barley rainfed            | 26    | Barley irrigated            |
| 27    | Winter barley rainfed     | 28    | Winter barley irrigated     |
| 29    | Rye rainfed               | 30    | Rye irrigated               |
| 31    | Winter rye rainfed        | 32    | Winter rye irrigated        |
| 33    | Cassava rainfed           | 34    | Cassava irrigated           |
| 35    | Citrus rainfed            | 36    | Citrus irrigated            |
| 37    | Cocoa rainfed             | 38    | Cocoa irrigated             |
| 39    | Coffee rainfed            | 40    | Coffee irrigated            |
| 41    | Cotton rainfed            | 42    | Cotton irrigated            |
| 43    | Datepalm rainfed          | 44    | Datepalm irrigated          |
| 45    | Foddergrass rainfed       | 46    | Foddergrass irrigated       |
| 47    | Grapes rainfed            | 48    | Grapes irrigated            |
| 49    | Groundnuts rainfed        | 50    | Groundnuts irrigated        |
| 51    | Millet rainfed            | 52    | Millet irrigated            |
| 53    | Oilpalm rainfed           | 54    | Oilpalm irrigated           |
| 55    | Potatoes rainfed          | 56    | Potatoes irrigated          |
| 57    | Pulses rainfed            | 58    | Pulses irrigated            |
| 59    | Rapeseed rainfed          | 60    | Rapeseed irrigated          |
| 61    | Rice rainfed              | 62    | Rice irrigated              |
| 63    | Sorghum rainfed           | 64    | Sorghum irrigated           |
| 65    | Sugarbeet rainfed         | 66    | Sugarbeet irrigated         |
| 67    | Sugarcane rainfed         | 68    | Sugarcane irrigated         |
| 69    | Sunflower rainfed         | 70    | Sunflower irrigated         |
| 71    | Miscanthus rainfed        | 72    | Miscanthus irrigated        |
| 73    | Switchgrass rainfed       | 74    | Switchgrass irrigated       |
| 75    | Tropical corn rainfed     | 76    | Tropical corn irrigated     |
| 77    | Tropical soybean rainfed  | 78    | Tropical soybean irrigated  |

## Requirements

- `numpy`
- `netCDF4`

## Notes

- The script writes a **new output file** (a copy of the input) and does not
  modify the original.
- All other variables (soil texture, topography, emission factors, etc.) are
  left unchanged.  Adjust them separately if needed.
