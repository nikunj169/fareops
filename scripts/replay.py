#!/usr/bin/env python3
"""Replay NYC trips against fare-api at a fixed rate, sending the true fare as the label."""
import argparse
import collections
import time

import httpx
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--rps", type=float, default=15.0)
    ap.add_argument("--limit", type=int, default=0, help="stop after N requests (0 = run until Ctrl-C)")
    ap.add_argument("--no-label", action="store_true")
    args = ap.parse_args()

    df = pd.read_parquet(args.file)
    client = httpx.Client(timeout=5.0)
    interval, next_t = 1.0 / args.rps, time.perf_counter()
    sent = ok = 0
    versions: collections.Counter = collections.Counter()
    while True:
        row = df.iloc[sent % len(df)]
        body = {"pickup_datetime": row.pickup_datetime.isoformat(),
                "trip_distance": float(row.trip_distance),
                "passenger_count": int(row.passenger_count),
                "PULocationID": int(row.PULocationID),
                "DOLocationID": int(row.DOLocationID)}
        if not args.no_label:
            body["actual_fare"] = float(row.fare_amount)
        try:
            r = client.post(f"{args.url}/predict", json=body)
            if r.status_code == 200:
                ok += 1
                versions[r.json()["model_version"]] += 1
        except httpx.HTTPError:
            pass
        sent += 1
        if sent % int(args.rps * 10) == 0:
            print(f"sent={sent} ok={ok} versions={dict(versions)}", flush=True)
            versions.clear()
        if args.limit and sent >= args.limit:
            break
        next_t += interval
        time.sleep(max(0.0, next_t - time.perf_counter()))


if __name__ == "__main__":
    main()
