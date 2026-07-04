import ee


def load_sentinel1_collection(
    roi,
    polarization: str = "VV",
    orbit_pass: str = "DESCENDING",
    instrument_mode: str = "IW"
):
    collection = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(roi)
        .filter(ee.Filter.eq("instrumentMode", instrument_mode))
        .filter(ee.Filter.eq("orbitProperties_pass", orbit_pass))
        .filter(
            ee.Filter.listContains(
                "transmitterReceiverPolarisation",
                polarization
            )
        )
        .select(polarization)
    )

    return collection


def make_median_composite(collection, start_date: str, end_date: str, roi):
    filtered = collection.filterDate(start_date, end_date)

    count = filtered.size()

    image = (
        filtered
        .median()
        .clip(roi)
    )

    return image, count