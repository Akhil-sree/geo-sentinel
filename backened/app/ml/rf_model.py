"""
Random Forest static susceptibility model.

Trained on structural terrain features with SPATIAL-BLOCK
cross-validation (GroupKFold by spatial block ID) to avoid
spatial leakage.

Artifacts are stored under:
    models/rf/<version>/

Each model version is stored separately.
"""

import os
import json
import datetime

import joblib
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_score


FEATURES = [
    "slope",
    "elevation_norm",
    "ruggedness",
    "road_proximity",
    "drainage_proximity",
    "settlement_density",
    "sar_change_score",
]


MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "models",
    "rf",
)


VERSION = "rf_2026_01"


def _to_features(z) -> list[float]:
    """
    Convert a Zone object into the feature vector
    expected by the Random Forest.
    """

    return [
        float(z.slope),

        # Normalize elevation to 0-1
        min(
            1.0,
            float(z.elevation) / 2000.0
        ),

        float(z.ruggedness),
        float(z.road_proximity),
        float(z.drainage_proximity),
        float(z.settlement_density),
        float(z.sar_change_score),
    ]


def train(
    zones,
    labels,
    version: str = VERSION,
    spatial_blocks=None,
) -> dict:
    """
    Train the Random Forest susceptibility model.

    Parameters
    ----------
    zones:
        List of Zone objects.

    labels:
        Labels corresponding to each zone:
            0 = LOW
            1 = MODERATE
            2 = HIGH

    version:
        Model version name.

    spatial_blocks:
        Spatial block ID for each zone.

        IMPORTANT:
        In the real pipeline this should be the actual
        spatial grid/block ID, NOT a row-based value.
    """

    if len(zones) != len(labels):
        raise ValueError(
            "zones and labels must have the same length."
        )

    if len(zones) < 3:
        raise ValueError(
            "At least 3 zones are required for 3-fold "
            "spatial cross-validation."
        )

    # ---------------------------------------------------------
    # Create feature matrix
    # ---------------------------------------------------------

    X = np.asarray(
        [_to_features(z) for z in zones],
        dtype=float,
    )

    y = np.asarray(labels)

    # ---------------------------------------------------------
    # Spatial blocks
    # ---------------------------------------------------------

    if spatial_blocks is None:
        # DEMO ONLY.
        #
        # Replace this with actual spatial grid/block IDs
        # in the real pipeline.
        spatial_blocks = np.asarray(
            [i % 3 for i in range(len(zones))]
        )
    else:
        spatial_blocks = np.asarray(spatial_blocks)

    if len(spatial_blocks) != len(zones):
        raise ValueError(
            "spatial_blocks must have the same length "
            "as zones."
        )

    unique_blocks = np.unique(spatial_blocks)

    if len(unique_blocks) < 3:
        raise ValueError(
            "At least 3 unique spatial blocks are required "
            "for GroupKFold(n_splits=3)."
        )

    # ---------------------------------------------------------
    # Random Forest
    # ---------------------------------------------------------

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=4,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    # ---------------------------------------------------------
    # Spatial-block cross-validation
    # ---------------------------------------------------------

    cv = GroupKFold(n_splits=3)

    scores = cross_val_score(
        clf,
        X,
        y,
        cv=cv.split(
            X,
            y,
            groups=spatial_blocks,
        ),
        scoring="accuracy",
        n_jobs=-1,
    )

    # ---------------------------------------------------------
    # Train final model on all data
    # ---------------------------------------------------------

    clf.fit(X, y)

    # ---------------------------------------------------------
    # Create model directory
    # ---------------------------------------------------------

    path = os.path.join(
        MODEL_DIR,
        version,
    )

    os.makedirs(
        path,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Save model
    # ---------------------------------------------------------

    model_path = os.path.join(
        path,
        "model.joblib",
    )

    joblib.dump(
        clf,
        model_path,
    )

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    meta = {
        "version": version,

        "training_date": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

        "features_used": FEATURES,

        "hyperparameters": clf.get_params(),

        "cv_accuracy": float(scores.mean()),

        "cv_accuracy_std": float(scores.std()),

        "cv_scores": [
            float(score)
            for score in scores
        ],

        "n_training_samples": int(len(zones)),

        "n_spatial_blocks": int(
            len(unique_blocks)
        ),
    }

    metadata_path = os.path.join(
        path,
        "metadata.json",
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            meta,
            f,
            indent=2,
        )

    return meta


class RFModel:
    """
    Wrapper around the trained Random Forest model.
    """

    def __init__(
        self,
        model_dir: str = MODEL_DIR,
        version: str = VERSION,
    ):

        self.version = version

        self.path = os.path.join(
            model_dir,
            version,
            "model.joblib",
        )

        if os.path.exists(self.path):
            self.model = joblib.load(self.path)
        else:
            self.model = None

    def available(self) -> bool:
        """
        Return True if the model is available.
        """

        return self.model is not None

    def predict(self, z) -> dict:
        """
        Predict static susceptibility for one zone.
        """

        if self.model is None:
            raise RuntimeError(
                f"Random Forest model '{self.version}' "
                "is not available."
            )

        X = [
            _to_features(z)
        ]

        proba = self.model.predict_proba(X)[0]

        classes = list(
            self.model.classes_
        )

        # -----------------------------------------------------
        # Static risk score
        #
        # LOW      = 0
        # MODERATE = 1
        # HIGH     = 2
        #
        # Weighted expectation gives a value from 0 to 1.
        # -----------------------------------------------------

        if classes:

            score = sum(
                p * c / 2.0
                for p, c in zip(
                    proba,
                    classes,
                )
            )

        else:
            score = 0.0

        score = min(
            1.0,
            max(0.0, score),
        )

        return {
            "static_score": float(score),

            "class_probs": {
                int(c): float(p)
                for c, p in zip(
                    classes,
                    proba,
                )
            },

            "version": self.version,
        }

    def feature_importances(self) -> dict:
        """
        Return Random Forest feature importances.
        """

        if self.model is None:
            return {}

        return {
            feature: round(
                float(importance),
                3,
            )
            for feature, importance in zip(
                FEATURES,
                self.model.feature_importances_,
            )
        }


def load_metrics(version: str = VERSION) -> dict:
    """Load stored training metadata / CV metrics."""
    metadata_path = os.path.join(MODEL_DIR, version, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "note": "Model not yet trained — metrics unavailable.",
        "version": version,
        "cv_accuracy": None,
    }