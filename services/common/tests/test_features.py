from datetime import datetime

import pandas as pd

from fareops_common.features import FEATURES, frame_features, row_features


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "pickup_datetime": [datetime(2024, 2, 3, 8, 15), datetime(2024, 2, 4, 22, 5), datetime(2024, 2, 5, 13, 45)],
        "trip_distance": [2.4, 0.9, 15.2],
        "passenger_count": [1, 2, 3],
        "PULocationID": [161, 132, 43],  # 132 = JFK -> airport flag 1
        "DOLocationID": [237, 1, 230],   # drop-off zone must NOT set the flag (pickup only)
    })


def test_frame_features_matches_row_features():
    df = _frame()
    X = frame_features(df)
    assert X.shape == (3, len(FEATURES))
    for i, row in df.iterrows():
        expected = row_features(row["pickup_datetime"], row["trip_distance"],
                                row["passenger_count"], row["PULocationID"], row["DOLocationID"])
        assert list(X[i]) == expected


def test_airport_flag_only_for_pickup_zone():
    df = _frame()
    X = frame_features(df)
    flag = FEATURES.index("is_airport_pickup")
    assert X[0][flag] == 0.0   # PULocationID 161
    assert X[1][flag] == 1.0   # PULocationID 132 (JFK); DO=1 must not matter
    assert X[2][flag] == 0.0   # PULocationID 43


def test_airport_zones_are_1_132_138():
    df = _frame()
    df["PULocationID"] = [1, 132, 138]
    X = frame_features(df)
    flag = FEATURES.index("is_airport_pickup")
    assert list(X[:, flag]) == [1.0, 1.0, 1.0]
