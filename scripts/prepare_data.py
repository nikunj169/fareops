#!/usr/bin/env python3
"""Download NYC TLC yellow-taxi data and build the FareOps datasets."""
import argparse
import pathlib
import urllib.request

import pandas as pd

BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{ym}.parquet"
AIRPORT_ZONES = {1, 132, 138}
COLS = ["tpep_pickup_datetime", "passenger_count", "trip_distance",
        "PULocationID", "DOLocationID", "fare_amount"]


def download(ym: str, raw_dir: pathlib.Path) -> pathlib.Path:
    path = raw_dir / f"yellow_tripdata_{ym}.parquet"
    if not path.exists():
        print(f"downloading {ym} ...")
        urllib.request.urlretrieve(BASE.format(ym=ym), path)
    return path


def clean(path: pathlib.Path, ym: str) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=COLS).rename(columns={"tpep_pickup_datetime": "pickup_datetime"})
    year, month = (int(x) for x in ym.split("-"))
    ts = df["pickup_datetime"]
    df = df[(ts.dt.year == year) & (ts.dt.month == month)].copy()
    df["passenger_count"] = df["passenger_count"].fillna(1).clip(1, 6).astype("int64")
    df["PULocationID"] = df["PULocationID"].astype("int64")
    df["DOLocationID"] = df["DOLocationID"].astype("int64")
    df = df[df["fare_amount"].between(2.5, 250) & df["trip_distance"].between(0.1, 60)]
    return df


def sample(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    out = df.sample(n=min(n, len(df)), random_state=seed)
    return out.sort_values("pickup_datetime").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="e.g. $HOME/fareops-data")
    args = ap.parse_args()
    root = pathlib.Path(args.out).expanduser()
    raw, ds = root / "raw", root / "datasets"
    raw.mkdir(parents=True, exist_ok=True)
    ds.mkdir(parents=True, exist_ok=True)

    jan = clean(download("2024-01", raw), "2024-01")
    feb = clean(download("2024-02", raw), "2024-02")
    is_airport_jan = jan["PULocationID"].isin(AIRPORT_ZONES)
    is_airport_feb = feb["PULocationID"].isin(AIRPORT_ZONES)

    outputs = {
        "baseline.parquet": sample(jan[~is_airport_jan], 100_000, 42),
        "replay_normal.parquet": sample(feb[~is_airport_feb], 20_000, 7),
        "replay_airport.parquet": sample(feb[is_airport_feb], 20_000, 7),
    }
    for name, frame in outputs.items():
        frame.to_parquet(ds / name, index=False)
        print(f"{name}: rows={len(frame)} mean_distance={frame.trip_distance.mean():.2f} "
              f"mean_fare={frame.fare_amount.mean():.2f}")


if __name__ == "__main__":
    main()
