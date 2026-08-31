"""
Rainfall feature engineering.

Computes:
- rainfall_1h/3h/6h/12h/24h/48h/72h/7d rolling sums
- rainfall intensity
- rainfall slope/trend
- rainfall acceleration
- antecedent rainfall
- soil moisture statistics

Window sums use hourly observations.
"""

import numpy as np
import pandas as pd


WINDOWS = {
    "rainfall_1h": 1,
    "rainfall_3h": 3,
    "rainfall_6h": 6,
    "rainfall_12h": 12,
    "rainfall_24h": 24,
    "rainfall_48h": 48,
    "rainfall_72h": 72,
    "rainfall_7d": 168,
}


def compute_rainfall_features(df: pd.DataFrame) -> dict:
    """
    df columns:
        timestamp
        rainfall_mm_per_hr

    Returns a dictionary of rainfall features.
    """

    # Make sure timestamp is datetime
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Sort by timestamp
    df = df.sort_values("timestamp")

    # Convert to hourly observations
    s = (
        df.set_index("timestamp")["rainfall_mm_per_hr"]
        .asfreq("h")
        .fillna(0.0)
    )

    out = {}

    # Rolling rainfall totals
    for name, hrs in WINDOWS.items():
        out[name] = float(s.tail(hrs).sum())

    # Current rainfall intensity
    out["rainfall_rate"] = out["rainfall_1h"]

    # ---------------------------------------------------------
    # Rainfall trend / slope
    # ---------------------------------------------------------

    def window_mean(start, end):
        """
        Mean rainfall between relative positions.

        start=0, end=6 -> latest 6 hours
        start=6, end=12 -> previous 6 hours
        """

        if len(s) >= end:
            values = s.iloc[-end:-start if start > 0 else None]

            if len(values) > 0:
                return float(values.mean())

        # Fallback when insufficient data
        return float(s.iloc[-1]) if len(s) > 0 else 0.0

    recent = window_mean(0, 6)
    prior = window_mean(6, 12)
    older = window_mean(12, 18)

    # Trend: change in rainfall intensity between
    # the latest 6 hours and previous 6 hours
    out["rainfall_slope"] = recent - prior

    # Acceleration: change in slope
    out["rainfall_acceleration"] = (
        (recent - prior) - (prior - older)
    )

    # Antecedent rainfall
    out["antecedent_rainfall"] = out["rainfall_7d"]

    return out


def compute_soil_features(df: pd.DataFrame) -> dict:
    """
    df columns:
        timestamp
        soil_moisture

    Returns soil moisture statistics.
    """

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    s = (
        df.set_index("timestamp")["soil_moisture"]
        .sort_index()
        .asfreq("h")
        .ffill()
    )

    if len(s) == 0:
        return {
            "soil_moisture_current": 0.34,
            "soil_moisture_3d_mean": 0.34,
            "soil_moisture_7d_mean": 0.34,
            "soil_moisture_change": 0.0,
            "soil_moisture_percentile": 0.0,
        }

    # Fill remaining missing values
    s = s.fillna(0.34)

    cur = float(s.iloc[-1])

    # Soil moisture 24-hour change
    if len(s) >= 25:
        soil_change = float(cur - s.iloc[-25])
    else:
        soil_change = 0.0

    return {
        "soil_moisture_current": cur,

        "soil_moisture_3d_mean": float(
            s.tail(72).mean()
        ),

        "soil_moisture_7d_mean": float(
            s.tail(168).mean()
        ),

        "soil_moisture_change": soil_change,

        # Fraction of observations below current value
        "soil_moisture_percentile": float(
            (s < cur).mean()
        ),
    }


def build_model_sequence(
    rain_df: pd.DataFrame,
    soil_df: pd.DataFrame,
    sar_change: float,
    seq_len: int = 48,
) -> list[list[float]]:
    """
    Build a temporal sequence for the model.

    Each timestep contains:

    [
        rain_1h_normalized,
        rain_24h_normalized,
        rain_72h_normalized,
        rain_slope_normalized,
        soil_moisture,
        soil_moisture_change,
        sar_change
    ]

    Missing rainfall values are filled with 0.

    Missing soil values are forward-filled and then
    filled with 0.34.
    """

    # ---------------------------------------------------------
    # Rainfall
    # ---------------------------------------------------------

    rain_df = rain_df.copy()
    rain_df["timestamp"] = pd.to_datetime(rain_df["timestamp"])

    r = (
        rain_df
        .sort_values("timestamp")
        .set_index("timestamp")["rainfall_mm_per_hr"]
        .asfreq("h")
        .fillna(0.0)
    )

    # ---------------------------------------------------------
    # Soil moisture
    # ---------------------------------------------------------

    soil_df = soil_df.copy()
    soil_df["timestamp"] = pd.to_datetime(soil_df["timestamp"])

    s = (
        soil_df
        .sort_values("timestamp")
        .set_index("timestamp")["soil_moisture"]
        .asfreq("h")
        .ffill()
        .fillna(0.34)
    )

    # If rainfall data is empty, return empty sequence
    if len(r) == 0:
        return []

    # Align soil data to rainfall timestamps
    s = s.reindex(r.index).ffill().fillna(0.34)

    seq = []

    # ---------------------------------------------------------
    # Create sequence
    # ---------------------------------------------------------

    start_idx = max(0, len(r) - seq_len)

    for i in range(start_idx, len(r)):

        # 24-hour rainfall
        start_24 = max(0, i - 23)

        r24 = float(
            r.iloc[start_24:i + 1].sum()
        )

        # 72-hour rainfall
        start_72 = max(0, i - 71)

        r72 = float(
            r.iloc[start_72:i + 1].sum()
        )

        # -----------------------------------------------------
        # Rainfall slope
        # -----------------------------------------------------

        if i > 0:
            slope = (
                float(r.iloc[i])
                - float(r.iloc[i - 1])
            )
        else:
            slope = 0.0

        # -----------------------------------------------------
        # Soil moisture
        # -----------------------------------------------------

        current_soil = float(s.iloc[i])

        if i >= 24:
            soil_change = (
                current_soil
                - float(s.iloc[i - 24])
            )
        else:
            soil_change = 0.0

        # -----------------------------------------------------
        # Feature vector
        # -----------------------------------------------------

        seq.append([
            # 1-hour rainfall normalized
            min(
                1.0,
                float(r.iloc[i]) / 40.0
            ),

            # 24-hour rainfall normalized
            min(
                1.0,
                r24 / 300.0
            ),

            # 72-hour rainfall normalized
            min(
                1.0,
                r72 / 600.0
            ),

            # Positive rainfall slope normalized
            min(
                1.0,
                max(
                    0.0,
                    slope / 12.0
                )
            ),

            # Current soil moisture
            current_soil,

            # 24-hour soil moisture change
            soil_change,

            # SAR change
            float(sar_change),
        ])

    return seq