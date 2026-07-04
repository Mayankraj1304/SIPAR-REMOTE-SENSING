from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Change this if your file name is different
INPUT_CSV = PROJECT_ROOT / "outputs" / "tables" / "batch_tile_flood_areas_top10.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BALANCED_OUTPUT = OUTPUT_DIR / "top_flood_tiles_balanced.csv"
ALL_RANKED_OUTPUT = OUTPUT_DIR / "all_tiles_balanced_ranked.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "phase1_flood_area_summary.csv"


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_CSV}\n"
            "If you only processed 10 tiles, change INPUT_CSV to batch_tile_flood_areas_top10.csv."
        )

    df = pd.read_csv(INPUT_CSV)

    print("Loaded:", INPUT_CSV)
    print("Rows:", len(df))
    print("Columns:", list(df.columns))

    # Keep only successfully processed rows
    if "status" in df.columns:
        df = df[df["status"] == "processed"].copy()

    # Rank balanced mask
    balanced = df[df["mask_type"] == "balanced"].copy()

    balanced = balanced.sort_values(
        by="flood_area_sqkm",
        ascending=False
    ).reset_index(drop=True)

    balanced["flood_rank"] = balanced.index + 1

    balanced.to_csv(ALL_RANKED_OUTPUT, index=False)
    balanced.head(20).to_csv(BALANCED_OUTPUT, index=False)

    print("\nTop 20 balanced flood tiles:")
    print(balanced[["flood_rank", "tile_id", "flood_area_sqkm"]].head(20))

    # Summary by mask type
    summary = (
        df.groupby("mask_type", dropna=False)
        .agg(
            tile_count=("tile_id", "nunique"),
            total_flood_area_sqkm=("flood_area_sqkm", "sum"),
            mean_flood_area_sqkm=("flood_area_sqkm", "mean"),
            median_flood_area_sqkm=("flood_area_sqkm", "median"),
            max_flood_area_sqkm=("flood_area_sqkm", "max"),
            min_flood_area_sqkm=("flood_area_sqkm", "min"),
        )
        .reset_index()
    )

    summary.to_csv(SUMMARY_OUTPUT, index=False)

    print("\nSaved:")
    print(BALANCED_OUTPUT)
    print(ALL_RANKED_OUTPUT)
    print(SUMMARY_OUTPUT)

    print("\nSummary:")
    print(summary)


if __name__ == "__main__":
    main()