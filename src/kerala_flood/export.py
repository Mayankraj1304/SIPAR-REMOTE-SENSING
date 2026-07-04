import ee


def export_image_to_drive(
    image,
    description: str,
    folder: str,
    file_name: str,
    region,
    scale: int = 10
):
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        fileNamePrefix=file_name,
        region=region,
        scale=scale,
        maxPixels=1e13
    )

    task.start()

    print(f"Started export: {description}")

    return task