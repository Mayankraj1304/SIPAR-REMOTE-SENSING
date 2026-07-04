from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.append(str(SRC_PATH))

from kerala_flood.config import load_config
from kerala_flood.gee_auth import initialize_ee
from kerala_flood.aoi import load_tile_roi
from kerala_flood.sentinel1 import load_sentinel1_collection, make_median_composite
from kerala_flood.flood_detection import (
    smooth_sar,
    make_permanent_water_mask,
    make_terrain_mask,
    detect_flood_by_change,
)
from kerala_flood.export import export_image_to_drive


TOP_TILES_CSV = PROJECT_ROOT / "outputs" / "tables" / "top_flood_tiles_balanced.csv"

# Start with 5. Later change to 10 if exports work.
TOP_N_EXPORT = 5

EXPORT_SENSITIVE = False
EXPORT_BALANCED = True
EXPORT_CONSERVATIVE = False
EXPORT_CHANGE_DB = True
EXPORT_CONFIDENCE = True

MASK_THRESHOLDS = {
    "sensitive": -2.0,
    "balanced": -2.5,
    "conservative": -3.0,
}


def export_one_tile(tile_id: str, config: dict):
    print(f"\nPreparing exports for {tile_id}...")

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
        return

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

    folder = config["export"]["folder"]
    scale = config["export"]["scale"]

    if EXPORT_SENSITIVE:
        change_db, flood_mask, confidence = detect_flood_by_change(
            pre_image=pre_smooth,
            flood_image=flood_smooth,
            permanent_water=permanent_water,
            terrain_mask=terrain_mask,
            change_threshold_db=MASK_THRESHOLDS["sensitive"]
        )

        export_image_to_drive(
            image=flood_mask.unmask(0).toByte(),
            description=f"{tile_id}_Sensitive_Flood_Mask",
            folder=folder,
            file_name=f"{tile_id.lower()}_sensitive_flood_mask",
            region=roi,
            scale=scale
        )

    if EXPORT_BALANCED:
        change_db, flood_mask, confidence = detect_flood_by_change(
            pre_image=pre_smooth,
            flood_image=flood_smooth,
            permanent_water=permanent_water,
            terrain_mask=terrain_mask,
            change_threshold_db=MASK_THRESHOLDS["balanced"]
        )

        export_image_to_drive(
            image=flood_mask.unmask(0).toByte(),
            description=f"{tile_id}_Balanced_Flood_Mask",
            folder=folder,
            file_name=f"{tile_id.lower()}_balanced_flood_mask",
            region=roi,
            scale=scale
        )

        if EXPORT_CONFIDENCE:
            export_image_to_drive(
                image=confidence.unmask(0),
                description=f"{tile_id}_Balanced_Confidence",
                folder=folder,
                file_name=f"{tile_id.lower()}_balanced_confidence",
                region=roi,
                scale=scale
            )

        if EXPORT_CHANGE_DB:
            export_image_to_drive(
                image=change_db,
                description=f"{tile_id}_Change_dB",
                folder=folder,
                file_name=f"{tile_id.lower()}_change_db",
                region=roi,
                scale=scale
            )

    if EXPORT_CONSERVATIVE:
        change_db, flood_mask, confidence = detect_flood_by_change(
            pre_image=pre_smooth,
            flood_image=flood_smooth,
            permanent_water=permanent_water,
            terrain_mask=terrain_mask,
            change_threshold_db=MASK_THRESHOLDS["conservative"]
        )

        export_image_to_drive(
            image=flood_mask.unmask(0).toByte(),
            description=f"{tile_id}_Conservative_Flood_Mask",
            folder=folder,
            file_name=f"{tile_id.lower()}_conservative_flood_mask",
            region=roi,
            scale=scale
        )


def main():
    config = load_config()
    initialize_ee(config["project_id"])

    if not TOP_TILES_CSV.exists():
        raise FileNotFoundError(
            f"Top tiles file not found: {TOP_TILES_CSV}\n"
            "Run scripts/rank_flood_tiles.py first."
        )

    top_df = pd.read_csv(TOP_TILES_CSV)
    tile_ids = top_df["tile_id"].head(TOP_N_EXPORT).tolist()

    print("Exporting maps for these tiles:")
    print(tile_ids)

    for tile_id in tile_ids:
        export_one_tile(tile_id, config)

    print("\nExport tasks started.")
    print("Check Google Drive / Earth Engine Tasks for progress.")


if __name__ == "__main__":
    main()