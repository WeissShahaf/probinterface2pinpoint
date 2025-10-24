# Reference Data Notes
**Date**: 2025-10-23
**Location**: `I:\My Drive\pinpoint_converter\ref\`

---

## Overview

The `ref/` directory contains reference data for Cambridge Neurotech probes:
- **probe_library/**: Individual probe folders with JSON definitions and images
- **ProbesDataBase_2Dshanks_2025.csv**: Comprehensive database with probe specifications
- **ProbeMaps_Final2025_SW.xlsx**: Additional probe mapping data

---

## ProbesDataBase_2Dshanks_2025.csv Structure

### Key Columns

| Column | Description | Example (H7) |
|--------|-------------|--------------|
| `part` | Probe model designation | H7 |
| `electrodes_n` | Number of electrodes | 64 |
| `shank_lenght_mm` | Shank length in mm | 9 |
| `shanks_n` | Number of shanks | 2 |
| **`shank_thickness_um`** | **Shank thickness in μm** | **15** |
| `electrodes_total` | Total electrodes | 64 |
| `electrodesPerShank_n` | Electrodes per shank | 32 |
| `electrodeWidth_um` | Electrode width | 11 |
| `electrodeHeight_um` | Electrode height | 15 |
| `shankBaseWidth_um` | Shank base width | 60 |
| `shankTipWidth_um` | Shank tip width | 60 |
| `electrode_cols_n` | Number of columns | 2 |
| `electrode_rows_n` | Number of rows | 16 |
| `shankSpacing_um` | Spacing between shanks | 250 |
| `electrodeSpacingWidth_um` | Horizontal spacing | 52 |
| `electrodeSpacingHeight_um` | Vertical spacing | 50 |

### ASSY Series Columns

The CSV has columns for different ASSY series (ASSY-37, ASSY-77, ASSY-116, etc.) with TRUE/FALSE values indicating which series use each probe model.

---

## IMPORTANT: Shank Thickness as Z Coordinate

### ProbeInterface 2D Probe Definition

According to probeinterface documentation and the user's instruction:

**For 2D probes (ndim=2):**
- Electrodes are positioned in the x-y plane
- The **shank thickness should be used as the z coordinate**
- This represents the physical depth/thickness of the probe shank

### Example: ASSY-77-H7

**From CSV Database:**
```
H7: shank_thickness_um = 15 μm
```

**Previous Output (INCORRECT):**
```csv
index,x,y,z,w,h,d,default,layer1,layer2
0,0.0,0.0,0.0,20.0,20.0,0.0,1,1,0
```
❌ z=0.0 (not representing physical thickness)

**Current Output (CORRECT - IMPLEMENTED 2025-10-23):**
```csv
index,x,y,z,w,h,d,default,layer1,layer2
0,0.0,0.0,15.0,20.0,20.0,0.0,1,1,0
```
✅ z=15.0 μm (full shank thickness from database lookup)

---

## Probe Library Structure

### Available Probes

**Total Probes**: 55 probe models in `ref/probe_library/`

**ASSY-77 Series:**
- ASSY-77-H1
- ASSY-77-H7 ← **Currently tested**
- ASSY-77-L3
- ASSY-77-M1v1
- ASSY-77-M1v2
- ASSY-77-M2v1
- ASSY-77-M2v2

**ASSY-116 Series:**
- ASSY-116-H1b
- ASSY-116-H4
- ASSY-116-H7b
- ASSY-116-H8b
- ASSY-116-L2

**ASSY-156 Series:**
- ASSY-156-H1
- ASSY-156-L3
- ASSY-156-M1v1
- ASSY-156-M1v2
- ASSY-156-M2v1
- ASSY-156-M2v2

**ASSY-158 Series:**
- ASSY-158-L3
- ASSY-158-M1v1
- ASSY-158-M1v2
- ASSY-158-M2v1
- ASSY-158-M2v2

**ASSY-196 Series:**
- ASSY-196-H4

**ASSY-236 Series:**
- ASSY-236-H1
- ASSY-236-L3
- ASSY-236-M1v1
- ASSY-236-M1v2
- ASSY-236-M2v1
- ASSY-236-M2v2

**ASSY-276 Series:**
- ASSY-276-H2
- ASSY-276-L3
- ASSY-276-M1v1
- ASSY-276-M1v2
- ASSY-276-M2v1
- ASSY-276-M2v2

**ASSY-325 Series:**
- ASSY-325-H8
- ASSY-325-H9
- ASSY-325-L3
- ASSY-325-M1v2
- ASSY-325-M2v2

**ASSY-350 Series:**
- ASSY-350-H12
- ASSY-350-H13
- ASSY-350-H14-1
- ASSY-350-H14-2
- ASSY-350-H15
- ASSY-350-H16
- ASSY-350-L13
- ASSY-350-L14

**ASSY-37 Series:**
- ASSY-37-H1b
- ASSY-37-H3
- ASSY-37-H4
- ASSY-37-H7b
- ASSY-37-H8b
- ASSY-37-L2

### Probe Folder Contents

Each probe folder contains:
```
ASSY-XX-YY/
├── ASSY-XX-YY.json  # SpikeInterface/probeinterface format
└── ASSY-XX-YY.png   # Probe image/visualization
```

---

## Integration with Converter

### Implementation Status ✅

1. **Z Coordinate**: ✅ **IMPLEMENTED (2025-10-23)**
   - Uses shank thickness from ProbesDataBase_2Dshanks_2025.csv
   - Automatic lookup by probe model name (e.g., "ASSY-77-H7" → "H7" → 15 μm)
   - Implementation: `src/utils/probe_database.py` + updates to `src/formatters/pinpoint.py`

2. **Electrode Depth (d column)**: ✅ **CORRECT**
   - Set to 0.0 (correctly represents 2D electrode depth)

### Implementation Details ✅

#### CSV Database Lookup (IMPLEMENTED)

**Implementation**: `src/utils/probe_database.py`
```python
class ProbeDatabase:
    """Read probe specifications from ProbesDataBase_2Dshanks_2025.csv"""

    def get_shank_thickness(self, probe_name: str) -> Optional[float]:
        """
        Get shank thickness in micrometers for a probe.

        Extracts the probe part code (e.g., "H7" from "ASSY-77-H7")
        and looks up shank_thickness_um in the database.

        Args:
            probe_name: Full probe name (e.g., "ASSY-77-H7")

        Returns:
            Shank thickness in micrometers, or None if not found
        """
        # Extract part code and look up in CSV database
        # Returns shank_thickness_um value (e.g., 15.0)
```

**Usage in Formatter**: `src/formatters/pinpoint.py`
```python
# In __init__()
self.probe_db = ProbeDatabase()

# In _generate_site_map()
shank_thickness_z = None
if probe_name:
    shank_thickness = self.probe_db.get_shank_thickness(probe_name)
    if shank_thickness is not None:
        shank_thickness_z = float(shank_thickness)

# Override z with shank thickness if available and z is 0
if shank_thickness_z is not None and z == 0:
    z = shank_thickness_z
```

---

## Shank Thickness Values (Common Probes)

| Probe Model | Shank Thickness (μm) | ASSY Series |
|-------------|---------------------|-------------|
| H1 | 15 | 77, 156, 236 |
| H1b | 15 | 37, 116 |
| H2 | 15 | 276 |
| H3 | 15 | 37 |
| H4 | 15 | 37, 116, 196 |
| H7 | 15 | **77**, 158, 276, 236 |
| H7b | 15 | 37, 116 |
| H8 | 15 | 325, 350 |
| H8b | 15 | 37, 116 |
| H9 | 15 | 325 |
| H10 | 15 | 77, 156, 158, 236, 276, 325, 350 |
| L2 | 15 | 37, 116 |
| L3 | 15 | 77, 156, 158, 236, 276, 325 |
| H12 | 15 | 350 |
| H13 | 15 | 350 |
| H14-1 | 15 | 350 |
| H14-2 | 15 | 350 |
| H15 | 15 | 350 |
| H16 | 15 | 350 |
| L13 | 15 | 350 |
| L14 | 15 | 350 |

**Note**: Almost all Cambridge Neurotech 2D probes use **15 μm** shank thickness.

---

## Testing Recommendations

### Test Cases to Validate Z Coordinate Implementation

1. **ASSY-77-H7** (Already tested)
   - Shank thickness: 15 μm
   - Expected z coordinate: 15.0 μm (or 7.5 μm if using half-thickness)

2. **ASSY-276-H2** (Single shank)
   - Shank thickness: 15 μm
   - 32 electrodes on 1 shank

3. **ASSY-350-H13** (Many electrodes)
   - Shank thickness: 15 μm
   - 128 electrodes on 1 shank

4. **ASSY-116-H4** (Different series)
   - Shank thickness: 15 μm
   - 32 electrodes on 1 shank

### Validation Checks

After implementing z coordinate from shank thickness:

```bash
# Convert probe
python src/cli.py convert -i ref/probe_library/ASSY-77-H7/ASSY-77-H7.json -o output/

# Check z values
head -5 "output/ASSY-77-H7/site_map.csv"
# Should show z=15.0 (or 7.5) instead of z=0.0
```

---

## ProbeInterface 2D Probe Standards

### From ProbeInterface Documentation

**2D Probes Definition:**
- `ndim = 2`: Probe is planar (electrodes in x-y plane)
- Z coordinate can represent:
  - Shank thickness (physical depth of probe)
  - Depth of electrode penetration
  - 0 if purely 2D with no thickness consideration

**Best Practice for Cambridge Neurotech:**
- Use shank thickness as z coordinate
- Represents physical 3D structure of "2D" probe
- Important for accurate spatial representation in VirtualBrainLab Pinpoint

---

## Next Steps

✅ **COMPLETED (2025-10-23)**:
1. ✅ Created CSV lookup utility: `src/utils/probe_database.py`
2. ✅ Updated formatter to use shank thickness for z coordinate
3. ✅ Tested with ASSY-77-H7 (z=15.0 μm) and ASSY-276-H2 (z=15.0 μm)
4. ✅ Validation passes for converted probes

**Remaining Tasks**:
1. **Batch Convert**: Process all 55 probes in probe_library/
2. **Handle Edge Cases**: Test probes with different shank thicknesses (if any exist beyond 15 μm)
3. **Add Tests**: Unit tests for ProbeDatabase and shank thickness lookup

---

## Files Locations

**Reference Data:**
- CSV Database: `I:\My Drive\pinpoint_converter\ref\ProbesDataBase_2Dshanks_2025.csv`
- Probe Library: `I:\My Drive\pinpoint_converter\ref\probe_library\`
- Excel Data: `I:\My Drive\pinpoint_converter\ref\ProbeMaps_Final2025_SW.xlsx`

**Test Data:**
- Input: `I:\My Drive\input\cambridgeneurotech\ASSY-77-H7\ASSY-77-H7.json`
- Output: `I:\My Drive\output\cambridgeneurotech\ASSY-77-H7\`

**Documentation:**
- This file: `REFERENCE_DATA_NOTES.md`
- Test results: `ASSY-77-H7_TEST_RESULTS.md`
- Validation report: `TEST_VALIDATION_REPORT.md`

---

**Created**: 2025-10-23
**Purpose**: Document reference data structure and shank thickness usage for 2D probes
