from pathlib import Path
import json
import pandas as pd
import ee


PROJECT_ID = "sipar-498412"

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TILE_GEOJSON_PATH = PROJECT_ROOT / "data" / "boundaries" / "kerala_boundary_tiles.geojson"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "boundaries" / "kerala_boundary_tiles_ranked.csv"

POLARIZATION = "VV"
ORBIT_PASS = "DESCENDING"

PRE_START = "2018-07-20"
PRE_END = "2018-08-01"

FLOOD_START = "2018-08-15"
FLOOD_END = "2018-08-31"


def initialize_ee():
    try:
        ee.Initialize(project=PROJECT_ID)
        print("Earth Engine initialized.")
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
        print("Earth Engine authenticated and initialized.")


def load_tiles():
    with open(TILE_GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    return ee.FeatureCollection(geojson)


def count_sentinel1_images_for_tile(tile_feature):
    tile_id = tile_feature.get("tile_id").getInfo()
    roi = tile_feature.geometry()

    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(roi)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.eq("orbitProperties_pass", ORBIT_PASS))
        .filter(
            ee.Filter.listContains(
                "transmitterReceiverPolarisation",
                POLARIZATION
            )
        )
        .select(POLARIZATION)
    )

    pre_count = s1.filterDate(PRE_START, PRE_END).size().getInfo()
    flood_count = s1.filterDate(FLOOD_START, FLOOD_END).size().getInfo()
    total_count = pre_count + flood_count

    return {
        "tile_id": tile_id,
        "pre_count": pre_count,
        "flood_count": flood_count,
        "total_count": total_count,
        "polarization": POLARIZATION,
        "orbit_pass": ORBIT_PASS,
        "pre_start": PRE_START,
        "pre_end": PRE_END,
        "flood_start": FLOOD_START,
        "flood_end": FLOOD_END
    }


def main():
    initialize_ee()

    tiles_fc = load_tiles()
    tile_count = tiles_fc.size().getInfo()

    print("Total tiles:", tile_count)

    tiles_list = tiles_fc.toList(tile_count)

    rows = []

    for i in range(tile_count):
        tile_feature = ee.Feature(tiles_list.get(i))

        row = count_sentinel1_images_for_tile(tile_feature)
        rows.append(row)

        print(
            row["tile_id"],
            "| pre:",
            row["pre_count"],
            "| flood:",
            row["flood_count"],
            "| total:",
            row["total_count"]
        )

    df = pd.DataFrame(rows)

    df = df.sort_values(
        by=["total_count", "flood_count", "pre_count"],
        ascending=False
    ).reset_index(drop=True)

    df["rank"] = df.index + 1

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV_PATH, index=False)

    print("\nSaved ranked tile CSV:")
    print(OUTPUT_CSV_PATH)

    print("\nTop 10 tiles:")
    print(df.head(10))

    best_tile = df.iloc[0]

    print("\nBest tile:")
    print("Tile ID:", best_tile["tile_id"])
    print("Total images:", best_tile["total_count"])
    print("Pre images:", best_tile["pre_count"])
    print("Flood images:", best_tile["flood_count"])


if __name__ == "__main__":
    main()