from pathlib import Path
import json
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TILE_GEOJSON = PROJECT_ROOT / "data" / "boundaries" / "kerala_boundary_tiles.geojson"
BATCH_CSV = PROJECT_ROOT / "outputs" / "tables" / "batch_tile_flood_areas_top81.csv"

OUTPUT_TABLES = PROJECT_ROOT / "outputs" / "tables"
OUTPUT_MAPS = PROJECT_ROOT / "outputs" / "maps"
DOCS_DIR = PROJECT_ROOT / "docs"

OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)
OUTPUT_MAPS.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def create_joined_geojson(balanced_ranked):
    with open(TILE_GEOJSON, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    flood_lookup = balanced_ranked.set_index("tile_id").to_dict(orient="index")

    for feature in geojson["features"]:
        tile_id = feature["properties"].get("tile_id")

        if tile_id in flood_lookup:
            row = flood_lookup[tile_id]

            feature["properties"]["balanced_flood_area_sqkm"] = float(row["flood_area_sqkm"])
            feature["properties"]["flood_rank"] = int(row["flood_rank"])

            area = float(row["flood_area_sqkm"])

            if area >= balanced_ranked["flood_area_sqkm"].quantile(0.90):
                severity = "very_high"
            elif area >= balanced_ranked["flood_area_sqkm"].quantile(0.75):
                severity = "high"
            elif area >= balanced_ranked["flood_area_sqkm"].quantile(0.50):
                severity = "medium"
            elif area > 0:
                severity = "low"
            else:
                severity = "none"

            feature["properties"]["flood_severity_class"] = severity
        else:
            feature["properties"]["balanced_flood_area_sqkm"] = None
            feature["properties"]["flood_rank"] = None
            feature["properties"]["flood_severity_class"] = "not_processed"

    output_geojson = OUTPUT_MAPS / "kerala_tiles_balanced_flood_summary.geojson"

    with open(output_geojson, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    print("Saved map GeoJSON:", output_geojson)


def create_validation_checklist(top_tiles):
    checklist = top_tiles.copy()

    checklist["visual_check_flood_near_river_lowland"] = ""
    checklist["visual_check_not_random_noise"] = ""
    checklist["visual_check_permanent_water_removed"] = ""
    checklist["visual_check_slope_mask_ok"] = ""
    checklist["notes"] = ""

    output = OUTPUT_TABLES / "phase1_visual_validation_checklist.csv"
    checklist.to_csv(output, index=False)

    print("Saved validation checklist:", output)


def create_methods_notes(summary, top_tiles):
    balanced_total = summary.loc[
        summary["mask_type"] == "balanced",
        "total_flood_area_sqkm"
    ].values[0]

    sensitive_total = summary.loc[
        summary["mask_type"] == "sensitive",
        "total_flood_area_sqkm"
    ].values[0]

    conservative_total = summary.loc[
        summary["mask_type"] == "conservative",
        "total_flood_area_sqkm"
    ].values[0]

    top_tile = top_tiles.iloc[0]

    notes = f"""# Phase 1 Remote Sensing Results Notes

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

Total sensitive flood area: {sensitive_total:.2f} sq km  
Total balanced flood area: {balanced_total:.2f} sq km  
Total conservative flood area: {conservative_total:.2f} sq km  

Top balanced flood tile: {top_tile["tile_id"]}  
Top tile balanced flood area: {top_tile["flood_area_sqkm"]:.2f} sq km  

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
"""

    output = DOCS_DIR / "phase1_methods_results_notes.md"

    with open(output, "w", encoding="utf-8") as f:
        f.write(notes)

    print("Saved notes:", output)


def main():
    if not BATCH_CSV.exists():
        raise FileNotFoundError(
            f"Batch CSV not found: {BATCH_CSV}\n"
            "Run scripts/run_batch_tiles_summary.py for all 81 tiles first."
        )

    df = pd.read_csv(BATCH_CSV)

    if "status" in df.columns:
        df = df[df["status"] == "processed"].copy()

    summary = (
        df.groupby("mask_type")
        .agg(
            tile_count=("tile_id", "nunique"),
            total_flood_area_sqkm=("flood_area_sqkm", "sum"),
            mean_flood_area_sqkm=("flood_area_sqkm", "mean"),
            median_flood_area_sqkm=("flood_area_sqkm", "median"),
            max_flood_area_sqkm=("flood_area_sqkm", "max"),
            min_flood_area_sqkm=("flood_area_sqkm", "min"),
        )
        .reset_index()
    )

    summary_output = OUTPUT_TABLES / "phase1_flood_area_summary.csv"
    summary.to_csv(summary_output, index=False)

    balanced = df[df["mask_type"] == "balanced"].copy()

    balanced = balanced.sort_values(
        by="flood_area_sqkm",
        ascending=False
    ).reset_index(drop=True)

    balanced["flood_rank"] = balanced.index + 1

    all_ranked_output = OUTPUT_TABLES / "all_tiles_balanced_ranked.csv"
    top_tiles_output = OUTPUT_TABLES / "top_flood_tiles_balanced.csv"

    balanced.to_csv(all_ranked_output, index=False)
    balanced.head(20).to_csv(top_tiles_output, index=False)

    print("Saved summary:", summary_output)
    print("Saved ranked balanced table:", all_ranked_output)
    print("Saved top tiles:", top_tiles_output)

    create_joined_geojson(balanced)
    create_validation_checklist(balanced.head(20))
    create_methods_notes(summary, balanced.head(20))

    print("\nDone. Phase 1 summary outputs created.")


if __name__ == "__main__":
    main()