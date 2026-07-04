# Phase 1 Remote Sensing Results Notes

## Current status

Phase 1 Sentinel-1 SAR flood mapping has been implemented as a reproducible VS Code Python workflow.

The workflow processes Kerala as generated spatial tiles, computes Sentinel-1 VV backscatter change between a pre-flood window and flood-period window, removes permanent water and steep terrain, and estimates flood area under sensitive, balanced, and conservative thresholds.

## Data and settings

Sensor: Sentinel-1 GRD  
Polarization: VV  
Orbit pass: DESCENDING  
Pre-flood window: 2018-07-20 to 2018-08-01  
Flood window: 2018-08-15 to 2018-08-31  

Masks:
- Sensitive: -2.0 dB backscatter change threshold
- Balanced: -2.5 dB backscatter change threshold
- Conservative: -3.0 dB backscatter change threshold

Permanent water was masked using JRC Global Surface Water occurrence.  
Steep terrain was masked using SRTM-derived slope.

## Summary results

Total sensitive flood area: 344.74 sq km  
Total balanced flood area: 273.28 sq km  
Total conservative flood area: 219.42 sq km  

Top balanced flood tile: Tile_016  
Top tile balanced flood area: 84.80 sq km  

## Outputs created

- outputs/tables/all_tiles_balanced_ranked.csv
- outputs/tables/top_flood_tiles_balanced.csv
- outputs/tables/phase1_flood_area_summary.csv
- outputs/maps/kerala_tiles_balanced_flood_summary.geojson
- outputs/tables/phase1_visual_validation_checklist.csv

## Validation / sanity checks to complete

For the top flood tiles, visually inspect:
1. Whether detected flood pixels occur near rivers, backwaters, floodplains, or low-lying areas.
2. Whether the flood mask avoids random speckle-like noise.
3. Whether permanent water bodies are excluded from new flood estimates.
4. Whether steep terrain is mostly excluded.
5. Whether sensitive, balanced, and conservative masks form a logical nested pattern.

## Limitations

This is a SAR change-detection flood estimate, not a final validated flood product.

Known limitations:
- Flooding under vegetation may be underestimated.
- Urban areas can be affected by double-bounce radar effects.
- Steep terrain can create SAR artifacts even after slope masking.
- Sentinel-1 acquisition timing may not exactly match flood peak.
- The tile grid is generated for processing convenience and is not an administrative boundary.
- Results should be validated before being used as final flood extent evidence.

## Next step

Complete visual validation for the top 10 flood tiles, then aggregate results to district or basin level if district boundary data is available.
