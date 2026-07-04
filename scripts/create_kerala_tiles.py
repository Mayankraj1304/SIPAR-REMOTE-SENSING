from pathlib import Path
import json
import ee


PROJECT_ID = "sipar-498412"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "boundaries" / "kerala_boundary_tiles.geojson"

GRID_SIZE_DEGREES = 0.25  # smaller = more tiles, bigger = fewer tiles


def initialize_ee():
    try:
        ee.Initialize(project=PROJECT_ID)
        print("Earth Engine initialized.")
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
        print("Earth Engine authenticated and initialized.")


def get_kerala_boundary():
    """
    Uses FAO GAUL level-1 administrative boundary from Earth Engine.
    Filters India -> Kerala.
    """
    states = ee.FeatureCollection("FAO/GAUL/2015/level1")

    kerala = states.filter(
        ee.Filter.And(
            ee.Filter.eq("ADM0_NAME", "India"),
            ee.Filter.eq("ADM1_NAME", "Kerala")
        )
    )

    count = kerala.size().getInfo()
    print("Kerala boundary features found:", count)

    if count == 0:
        raise ValueError("Kerala boundary not found in GAUL dataset.")

    return kerala.geometry()


def create_grid_over_kerala(kerala_geom, grid_size=0.25):
    """
    Creates rectangular grid tiles over Kerala boundary.
    Keeps only tiles that intersect Kerala.
    """

    bounds = kerala_geom.bounds().coordinates().getInfo()[0]

    xs = [coord[0] for coord in bounds]
    ys = [coord[1] for coord in bounds]

    min_lon = min(xs)
    max_lon = max(xs)
    min_lat = min(ys)
    max_lat = max(ys)

    print("Kerala bounds:")
    print("min_lon:", min_lon)
    print("max_lon:", max_lon)
    print("min_lat:", min_lat)
    print("max_lat:", max_lat)

    features = []
    tile_number = 1

    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            cell = ee.Geometry.Rectangle(
                [lon, lat, lon + grid_size, lat + grid_size],
                proj="EPSG:4326",
                geodesic=False
            )

            intersects = cell.intersects(kerala_geom, ee.ErrorMargin(1)).getInfo()

            if intersects:
                clipped = cell.intersection(kerala_geom, ee.ErrorMargin(1))

                feature = ee.Feature(
                    clipped,
                    {
                        "tile_id": f"Tile_{tile_number:03d}",
                        "tile_number": tile_number,
                        "grid_size_deg": grid_size
                    }
                )

                features.append(feature)
                tile_number += 1

            lon += grid_size
        lat += grid_size

    grid_fc = ee.FeatureCollection(features)

    print("Tiles created:", tile_number - 1)

    return grid_fc


def save_feature_collection_to_geojson(fc, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    geojson = fc.getInfo()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    print("Saved GeoJSON to:")
    print(output_path)


def main():
    initialize_ee()

    kerala_geom = get_kerala_boundary()

    tiles = create_grid_over_kerala(
        kerala_geom=kerala_geom,
        grid_size=GRID_SIZE_DEGREES
    )

    save_feature_collection_to_geojson(
        fc=tiles,
        output_path=OUTPUT_PATH
    )


if __name__ == "__main__":
    main()