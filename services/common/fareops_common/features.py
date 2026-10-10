from datetime import datetime

import numpy as np

AIRPORT_ZONES = frozenset({1, 132, 138})
FEATURES = ["pickup_hour", "pickup_dow", "trip_distance", "passenger_count",
            "PULocationID", "DOLocationID", "is_airport_pickup"]
DRIFT_FEATURES = ["trip_distance", "pickup_hour", "is_airport_pickup"]


def row_features(pickup_datetime: datetime, trip_distance: float, passenger_count: int,
                 pu: int, do: int) -> list[float]:
    """One request -> one feature row. Order MUST match FEATURES."""
    return [float(pickup_datetime.hour), float(pickup_datetime.weekday()),
            float(trip_distance), float(passenger_count), float(pu), float(do),
            1.0 if pu in AIRPORT_ZONES else 0.0]


def frame_features(df) -> np.ndarray:
    """pandas DataFrame with raw columns -> feature matrix. pandas is imported lazily."""
    import pandas as pd
    ts = pd.to_datetime(df["pickup_datetime"])
    return np.column_stack([
        ts.dt.hour, ts.dt.dayofweek, df["trip_distance"], df["passenger_count"],
        df["PULocationID"], df["DOLocationID"],
        df["PULocationID"].isin(AIRPORT_ZONES).astype(int),
    ]).astype("float64")
