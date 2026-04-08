"""Abdullah's XGBoost player valuation predictor.

Trains on player_valuation_processed.csv to predict delta_log_value,
then combines with prev_log_value to estimate market value in EUR.
R-squared ~ 0.83 on the test set.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CSV_PATH = _DATA_DIR / "player_valuation_processed.csv"
_MODEL_PATH = _DATA_DIR / "player_valuation_model.joblib"

# The 38 feature columns the model expects (after one-hot encoding + age_squared).
# Derived from the notebook's booster.feature_names.
FEATURE_COLUMNS = [
    "club_at_valuation_id",
    "age",
    "matches_last_365d",
    "minutes_played_last_365d",
    "goals_last_365d",
    "assists_last_365d",
    "yellow_cards_last_365d",
    "red_cards_last_365d",
    "goals_per90_last_365d",
    "assists_per90_last_365d",
    "matches_last_180d",
    "minutes_played_last_180d",
    "goals_last_180d",
    "assists_last_180d",
    "yellow_cards_last_180d",
    "red_cards_last_180d",
    "goals_per90_last_180d",
    "assists_per90_last_180d",
    "prev_log_value",
    "age_squared",
    "position_Defender",
    "position_Goalkeeper",
    "position_Midfield",
    "position_Missing",
    "sub_position_Central Midfield",
    "sub_position_Centre-Back",
    "sub_position_Centre-Forward",
    "sub_position_Defensive Midfield",
    "sub_position_Goalkeeper",
    "sub_position_Left Midfield",
    "sub_position_Left Winger",
    "sub_position_Left-Back",
    "sub_position_Right Midfield",
    "sub_position_Right Winger",
    "sub_position_Right-Back",
    "sub_position_Second Striker",
    "foot_left",
    "foot_right",
]


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_and_save_model() -> str:
    """Reads the CSV, trains the XGBoost model exactly as in the notebook,
    and saves it as a joblib file. Returns the path to the saved model."""
    from xgboost import XGBRegressor
    import joblib

    logger.info("Loading CSV from %s", _CSV_PATH)
    df = pd.read_csv(_CSV_PATH)

    # Additional modifications (same as notebook)
    df = df.sort_values(["player_id", "snapshot_date"])
    df["prev_log_value"] = df.groupby("player_id")["log_market_value"].shift(1)
    df = df.dropna(subset=["prev_log_value"]).copy()
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")

    # Prepare features
    df_model = df.copy()
    df_model = df_model.drop(columns=[
        "player_name",
        "date_of_birth",
        "player_current_club_id",
        "player_current_club_name",
        "country_of_birth",
        "country_of_citizenship",
        "market_value_in_eur",
        "log_market_value",
        "club_at_valuation_name",
        "player_id",
    ], errors="ignore")

    df_model["age_squared"] = df_model["age"] ** 2

    # Target: delta_log_value clipped for stability
    df["delta_log_value"] = df["log_market_value"] - df["prev_log_value"]
    df["delta_log_value"] = df["delta_log_value"].clip(-3, 3)
    y = df["delta_log_value"]

    # One-hot encode categoricals
    categorical_cols = ["position", "sub_position", "foot"]
    df_model = pd.get_dummies(df_model, columns=categorical_cols, drop_first=True)

    # Time-aware split
    split_date = pd.Timestamp("2023-12-31")
    train_mask = df_model["snapshot_date"] < split_date

    X_train = df_model[train_mask].drop(columns=["snapshot_date"])
    y_train = y[train_mask]

    logger.info("Training XGBRegressor on %d rows, %d features ...", len(X_train), len(X_train.columns))

    model = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Save
    os.makedirs(_DATA_DIR, exist_ok=True)
    joblib.dump(model, _MODEL_PATH)
    logger.info("Model saved to %s", _MODEL_PATH)
    return str(_MODEL_PATH)


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

_model_cache = None
_df_cache: pd.DataFrame | None = None


def _load_model():
    """Lazy-load the saved XGBoost model."""
    global _model_cache
    if _model_cache is None:
        import joblib
        if not _MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found at {_MODEL_PATH}. Run train_and_save_model() first."
            )
        _model_cache = joblib.load(_MODEL_PATH)
        logger.info("Loaded XGBoost model from %s", _MODEL_PATH)
    return _model_cache


def _load_csv() -> pd.DataFrame:
    """Lazy-load and prepare the player CSV for lookups."""
    global _df_cache
    if _df_cache is None:
        df = pd.read_csv(_CSV_PATH)
        df = df.sort_values(["player_id", "snapshot_date"])
        df["prev_log_value"] = df.groupby("player_id")["log_market_value"].shift(1)
        df = df.dropna(subset=["prev_log_value"]).copy()
        _df_cache = df
    return _df_cache


def _find_player_row(player_profile: dict) -> pd.Series | None:
    """Look up the most recent row for a player by name (case-insensitive)."""
    df = _load_csv()
    name = player_profile.get("player_name", player_profile.get("name", "")).lower().strip()

    if not name:
        return None

    # Try exact match on player_name column
    mask = df["player_name"].str.lower().str.strip() == name
    if mask.any():
        return df[mask].iloc[-1]  # most recent snapshot

    # Try partial / slug match (e.g. "kylian-mbappe" vs "kylian mbappe")
    name_slug = name.replace(" ", "-")
    mask = df["player_name"].str.lower().str.strip() == name_slug
    if mask.any():
        return df[mask].iloc[-1]

    return None


def predict_market_value_ml(player_profile: dict) -> dict:
    """Predicts market value for a player using Abdullah's XGBoost model.

    Parameters
    ----------
    player_profile : dict
        Must contain at least ``player_name`` (or ``name``). Extra keys like
        ``age``, ``position``, ``goals``, etc. are used if the player is not
        found in the CSV.

    Returns
    -------
    dict
        market_context compatible with the Auto-Negotiate pipeline:
        ``{predicted_value_eur, p25_eur, median_eur, p75_eur, salary_range, comparables, source}``

    Raises
    ------
    ValueError
        If the player cannot be found in the CSV (caller should fall back to default predictor).
    """
    model = _load_model()
    row = _find_player_row(player_profile)

    if row is None:
        raise ValueError(
            f"Player '{player_profile.get('player_name', player_profile.get('name', '?'))}' "
            "not found in the valuation CSV."
        )

    # Build the feature vector exactly as the notebook does
    feature_dict: dict[str, float] = {}

    # Numeric features directly from the row
    numeric_from_row = [
        "club_at_valuation_id", "age",
        "matches_last_365d", "minutes_played_last_365d",
        "goals_last_365d", "assists_last_365d",
        "yellow_cards_last_365d", "red_cards_last_365d",
        "goals_per90_last_365d", "assists_per90_last_365d",
        "matches_last_180d", "minutes_played_last_180d",
        "goals_last_180d", "assists_last_180d",
        "yellow_cards_last_180d", "red_cards_last_180d",
        "goals_per90_last_180d", "assists_per90_last_180d",
        "prev_log_value",
    ]

    for col in numeric_from_row:
        feature_dict[col] = float(row.get(col, 0))

    feature_dict["age_squared"] = feature_dict["age"] ** 2

    # One-hot encode position, sub_position, foot (drop_first=True means Attack, missing-sub, missing-foot are baselines)
    position = str(row.get("position", "")).strip()
    sub_position = str(row.get("sub_position", "")).strip()
    foot = str(row.get("foot", "")).strip()

    for col in FEATURE_COLUMNS:
        if col.startswith("position_"):
            cat = col[len("position_"):]
            feature_dict[col] = 1.0 if position == cat else 0.0
        elif col.startswith("sub_position_"):
            cat = col[len("sub_position_"):]
            feature_dict[col] = 1.0 if sub_position == cat else 0.0
        elif col.startswith("foot_"):
            cat = col[len("foot_"):]
            feature_dict[col] = 1.0 if foot == cat else 0.0

    # Build DataFrame with the exact column order
    X = pd.DataFrame([feature_dict], columns=FEATURE_COLUMNS)

    # Predict delta_log_value
    delta_pred = model.predict(X)[0]
    prev_log = feature_dict["prev_log_value"]
    pred_log = prev_log + delta_pred
    predicted_eur = float(np.exp(pred_log))

    # Try to use manually-researched salary range from sample_players.json first.
    # The ML model predicts transfer market VALUE, not salary. A fixed % conversion
    # can underestimate elite players who command wage premiums above the ratio.
    name_key = player_profile.get("player_name", player_profile.get("name", "")).lower().strip()
    db_salary_range: dict | None = None
    db_comparables: list = []
    db_transfer_source: str = "abdullah_xgboost_v1"

    try:
        import json as _json
        from pathlib import Path as _Path
        _players_path = _Path(__file__).resolve().parent.parent / "data" / "sample_players.json"
        if _players_path.exists():
            with open(_players_path) as _f:
                _db = {p["name"].lower(): p for p in _json.load(_f).get("players", [])}
            if name_key in _db:
                _entry = _db[name_key]
                _mc = _entry.get("market_context", {})
                _sr = _mc.get("salary_range", {})
                if _sr.get("low_eur") and _sr.get("mid_eur") and _sr.get("high_eur"):
                    db_salary_range = _sr
                db_comparables = _mc.get("comparables", [])
                if _mc.get("transfer_value_source"):
                    db_transfer_source = _mc["transfer_value_source"]
    except Exception:
        pass  # non-fatal — fall back to formula

    if db_salary_range:
        salary_range = db_salary_range
    else:
        # Fall back to heuristic. Use higher % for elite players (top-quartile value).
        # EPL elite: salary tends to be 12-22% of transfer value for peak players.
        if predicted_eur >= 80_000_000:
            pct_low, pct_mid, pct_high = 0.12, 0.17, 0.24
        elif predicted_eur >= 40_000_000:
            pct_low, pct_mid, pct_high = 0.10, 0.14, 0.20
        else:
            pct_low, pct_mid, pct_high = 0.08, 0.12, 0.18
        salary_range = {
            "low_eur": round(predicted_eur * pct_low),
            "mid_eur": round(predicted_eur * pct_mid),
            "high_eur": round(predicted_eur * pct_high),
        }

    return {
        "predicted_value_eur": round(predicted_eur),
        "p25_eur": round(predicted_eur * 0.75),
        "median_eur": round(predicted_eur),
        "p75_eur": round(predicted_eur * 1.25),
        "salary_range": salary_range,
        "comparables": db_comparables,  # pass curated comparables from DB
        "source": "abdullah_xgboost_v1",
        "transfer_value_source": db_transfer_source,
    }


# ---------------------------------------------------------------------------
# IMarketPredictor adapter class
# ---------------------------------------------------------------------------

from agents.adapters import IMarketPredictor


class AbdullahPredictor(IMarketPredictor):
    """Abdullah's XGBoost market value predictor, implementing IMarketPredictor.

    Falls back to the default predictor for players not in the CSV.
    """

    def predict(self, player_profile: dict) -> dict:
        try:
            return predict_market_value_ml(player_profile)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("AbdullahPredictor falling back to default: %s", exc)
            from agents.adapters import DefaultMarketPredictor
            return DefaultMarketPredictor().predict(player_profile)


# ---------------------------------------------------------------------------
# CLI entry point for training
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_and_save_model()
