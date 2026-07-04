from pathlib import Path
import json
import ee


def load_tile_roi(tile_geojson_path: str, tile_id: str):
    path = Path(tile_geojson_path)

    with open(path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    tiles_fc = ee.FeatureCollection(geojson)

    roi = (
        tiles_fc
        .filter(ee.Filter.eq("tile_id", tile_id))
        .geometry()
    )

    return roi