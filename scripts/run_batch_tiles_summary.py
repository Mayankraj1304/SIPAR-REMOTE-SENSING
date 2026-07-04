from pathlib import Path
import sys
import pandas as pd

# -----------------------------
# Project paths
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.append(str(SRC_PATH))

# -----------------------------
# Imports from your project
# -----------------------------
from kerala_flood.config import load_config
from kerala_flood.gee_auth import initialize_ee
from kerala_flood.aoi import load_tile_roi
from kerala_flood.sentinel1 import load_sentinel1_collection, make_median_composite
from kerala_flood.flood_detection import (
    smooth_sar,
    make_permanent_water_mask,
    make_terrain_mask,
    detect_flood_by_change,
    calculate_flood_area_sqkm
)


# -----------------------------
# Settings
# -----------------------------
TOP_N_TILES = 10   # first run 10, later change to 81 for all tiles

MASK_SETTINGS = {
    "sensitive": -2.0,
    "balanced": -2.5,
    "conservative": -3.0
}


def process_one_tile(tile_id, config):
    print(f"\nProcessing {tile_id}...")

    tile_geojson_path = PROJECT_ROOT / config["paths"]["tile_geojson"]

    roi = load_tile_roi(
        tile_geojson_path=str(tile_geojson_path),
        tile_id=tile_id
    )

    s1 = load_sentinel1_collection(
        roi=roi,
        polarization=config["sentinel1"]["polarization"],
        orbit_pass=config["sentinel1"]["orbit_pass"],
        instrument_mode=config["sentinel1"]["instrument_mode"]
    )

    pre_img, pre_count = make_median_composite(
        collection=s1,
        start_date=config["dates"]["pre_start"],
        end_date=config["dates"]["pre_end"],
        roi=roi
    )

    flood_img, flood_count = make_median_composite(
        collection=s1,
        start_date=config["dates"]["flood_start"],
        end_date=config["dates"]["flood_end"],
        roi=roi
    )

    pre_count_value = pre_count.getInfo()
    flood_count_value = flood_count.getInfo()

    print("Pre images:", pre_count_value)
    print("Flood images:", flood_count_value)

    if pre_count_value == 0 or flood_count_value == 0:
        print(f"Skipping {tile_id}: missing Sentinel-1 images.")
        return [{
            "tile_id": tile_id,
            "status": "skipped_no_images",
            "pre_image_count": pre_count_value,
            "flood_image_count": flood_count_value,
            "mask_type": None,
            "threshold_db": None,
            "flood_area_sqkm": None
        }]

    pre_smooth = smooth_sar(pre_img, radius_m=30)
    flood_smooth = smooth_sar(flood_img, radius_m=30)

    permanent_water = make_permanent_water_mask(
        roi=roi,
        occurrence_threshold=config["thresholds"]["permanent_water_occurrence"]
    )

    terrain_mask, slope = make_terrain_mask(
        roi=roi,
        slope_threshold=config["thresholds"]["slope_threshold"]
    )

    rows = []

    for mask_type, threshold in MASK_SETTINGS.items():
        change_db, flood_mask, confidence = detect_flood_by_change(
            pre_image=pre_smooth,
            flood_image=flood_smooth,
            permanent_water=permanent_water,
            terrain_mask=terrain_mask,
            change_threshold_db=threshold
        )

        flood_area_sqkm = calculate_flood_area_sqkm(
            flood_mask=flood_mask,
            roi=roi,
            scale=config["export"]["scale"]
        )

        print(f"{mask_type} | threshold {threshold} dB | area {flood_area_sqkm:.3f} sq km")

        rows.append({
            "tile_id": tile_id,
            "status": "processed",
            "pre_start": config["dates"]["pre_start"],
            "pre_end": config["dates"]["pre_end"],
            "flood_start": config["dates"]["flood_start"],
            "flood_end": config["dates"]["flood_end"],
            "polarization": config["sentinel1"]["polarization"],
            "orbit_pass": config["sentinel1"]["orbit_pass"],
            "pre_image_count": pre_count_value,
            "flood_image_count": flood_count_value,
            "mask_type": mask_type,
            "threshold_db": threshold,
            "flood_area_sqkm": flood_area_sqkm
        })

    return rows


def main():
    config = load_config()
    initialize_ee(config["project_id"])

    ranked_csv = PROJECT_ROOT / "data" / "boundaries" / "kerala_boundary_tiles_ranked.csv"

    if not ranked_csv.exists():
        raise FileNotFoundError(
            f"Ranked tile CSV not found: {ranked_csv}\n"
            "Run scripts/rank_tiles_by_sentinel1_count.py first."
        )

    ranked_df = pd.read_csv(ranked_csv)

    tile_ids = ranked_df["tile_id"].head(TOP_N_TILES).tolist()

    print("Tiles selected:")
    print(tile_ids)

    all_rows = []

    for tile_id in tile_ids:
        try:
            rows = process_one_tile(tile_id, config)
            all_rows.extend(rows)
        except Exception as e:
            print(f"Error processing {tile_id}: {e}")

            all_rows.append({
                "tile_id": tile_id,
                "status": "error",
                "error_message": str(e),
                "mask_type": None,
                "threshold_db": None,
                "flood_area_sqkm": None
            })

    output_path = PROJECT_ROOT / "outputs" / "tables" / f"batch_tile_flood_areas_top{TOP_N_TILES}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result_df = pd.DataFrame(all_rows)
    result_df.to_csv(output_path, index=False)

    print("\nSaved batch result:")
    print(output_path)

    print("\nPreview:")
    print(result_df.head(20))


if __name__ == "__main__":
    main()