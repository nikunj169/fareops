import glob
import os

import pandas as pd

RAW_COLS = ["pickup_datetime", "trip_distance", "passenger_count", "PULocationID", "DOLocationID", "fare_amount"]


def load_baseline(data_dir: str) -> pd.DataFrame:
    return pd.read_parquet(os.path.join(data_dir, "datasets", "baseline.parquet"))[RAW_COLS]


def load_recent(data_dir: str, n: int) -> pd.DataFrame:
    files = glob.glob(os.path.join(data_dir, "inference-logs", "*.csv"))
    if not files:
        return pd.DataFrame(columns=RAW_COLS + ["ts"])
    df = pd.concat((pd.read_csv(f, on_bad_lines="skip") for f in files), ignore_index=True)
    df = df.dropna(subset=RAW_COLS).sort_values("ts").tail(n).reset_index(drop=True)
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"])
    return df
