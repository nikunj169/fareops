from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("fare_api_requests_total", "Prediction requests", ["status", "model_version"])
LATENCY = Histogram("fare_api_request_latency_seconds", "Prediction latency", ["model_version"],
                    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0))
PREDICTION = Histogram("fare_api_prediction_usd", "Predicted fare", ["model_version"],
                       buckets=(5, 10, 15, 20, 30, 40, 50, 70, 100))
ABS_ERROR = Histogram("fare_api_abs_error_usd", "Absolute error against label", ["model_version"],
                      buckets=(0.5, 1, 2, 3, 5, 8, 12, 20, 40))
PSI = Gauge("fare_api_feature_psi", "PSI of live window vs reference", ["feature", "model_version"])
ROLLING_MAE = Gauge("fare_api_rolling_mae_usd", "MAE over the last 500 labelled requests", ["model_version"])
MODEL_INFO = Gauge("fare_api_model_info", "Model loaded by this pod", ["model_version"])
