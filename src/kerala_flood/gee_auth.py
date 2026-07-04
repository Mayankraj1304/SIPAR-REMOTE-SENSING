import ee

def initialize_ee(project_id: str):
    try:
        ee.Initialize(project=project_id)
        print("Earth Engine initialized")
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project_id)
        print("Earth Engine authenticated and initialized")