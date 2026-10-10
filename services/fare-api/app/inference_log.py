import os
import threading

HEADER = "ts,pickup_datetime,trip_distance,passenger_count,PULocationID,DOLocationID,fare_amount,prediction,model_version\n"
MAX_BYTES = 20 * 1024 * 1024


class InferenceLog:
    def __init__(self, data_dir: str, pod_name: str):
        folder = os.path.join(data_dir, "inference-logs")
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, f"{pod_name}.csv")
        self.lock = threading.Lock()

    def write(self, values: list) -> None:
        line = ",".join(str(v) for v in values) + "\n"
        with self.lock:
            if os.path.exists(self.path) and os.path.getsize(self.path) > MAX_BYTES:
                os.replace(self.path, self.path + ".1")  # .csv.1 is ignored by the trainer
            new = not os.path.exists(self.path)
            with open(self.path, "a") as fh:
                if new:
                    fh.write(HEADER)
                fh.write(line)
