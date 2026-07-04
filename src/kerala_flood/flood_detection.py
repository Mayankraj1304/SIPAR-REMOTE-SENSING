import ee


def smooth_sar(image, radius_m: int = 30):
    return image.focal_median(radius=radius_m, units="meters")


def make_permanent_water_mask(roi, occurrence_threshold: int = 90):
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")

    permanent_water = (
        jrc
        .select("occurrence")
        .gte(occurrence_threshold)
        .clip(roi)
    )

    return permanent_water


def make_terrain_mask(roi, slope_threshold: int = 15):
    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem).clip(roi)

    terrain_mask = slope.lt(slope_threshold)

    return terrain_mask, slope


def detect_flood_by_change(
    pre_image,
    flood_image,
    permanent_water,
    terrain_mask,
    change_threshold_db: float = -2.5
):
    change_db = (
        flood_image
        .subtract(pre_image)
        .rename("change_db")
    )

    flood_candidate = change_db.lt(change_threshold_db)

    flood_mask = (
        flood_candidate
        .And(permanent_water.Not())
        .And(terrain_mask)
        .rename("flood_mask")
    )

    flood_mask_clean = (
        flood_mask
        .focal_max(radius=1)
        .focal_min(radius=1)
        .selfMask()
        .rename("flood_mask_clean")
    )

    confidence = (
        change_db
        .multiply(-1)
        .unitScale(0, 8)
        .clamp(0, 1)
        .rename("confidence")
        .updateMask(flood_mask_clean)
    )

    return change_db, flood_mask_clean, confidence


def calculate_flood_area_sqkm(flood_mask, roi, scale: int = 10):
    area_image = flood_mask.multiply(ee.Image.pixelArea())

    area_result = area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=roi,
        scale=scale,
        maxPixels=1e13
    )

    area_dict = area_result.getInfo()

    value = list(area_dict.values())[0] if area_dict else 0

    return value / 1e6