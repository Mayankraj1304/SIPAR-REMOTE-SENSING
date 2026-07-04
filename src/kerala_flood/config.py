from pathlib import Path
import yaml


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(config_path: str = "configs/phase1_mvp.yaml") -> dict:
    root = get_project_root()
    full_path = root / config_path

    with open(full_path, "r") as f:
        config = yaml.safe_load(f)

    return config