from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from flus_ca.config import _validate_config
from flus_ca.model import FLUSCA


def _write(path: Path, data: np.ndarray, transform=None):
    if data.ndim == 2:
        data = data[None, ...]
    transform = transform or from_origin(0, 5, 1, 1)
    with rasterio.open(
        path, "w", driver="GTiff", width=data.shape[2], height=data.shape[1],
        count=data.shape[0], dtype=data.dtype, crs="EPSG:3857",
        transform=transform, nodata=0,
    ) as dst:
        dst.write(data)


def _cfg(tmp_path):
    return {
        "rasters": {
            "landuse": str(tmp_path / "land.tif"),
            "probability": str(tmp_path / "prob.tif"),
            "restricted": None,
            "output": str(tmp_path / "out.tif"),
        },
        "classes": {"n_types": 2, "codes": [1, 2]},
        "simulation": {
            "future_pixels": [13, 12],
            "cost_matrix": [[1, 1], [1, 1]],
            "neighborhood_weights": [1, 1],
            "max_iterations": 3,
            "neighborhood_size": 3,
            "acceleration": 0.1,
            "thread": 1,
        },
        "hyperparameters": {
            "seed": 7,
            "stop_tolerance_fraction": 0.0001,
            "stable_iterations": 5,
            "darea": {"enabled": False, "restricted_value": 2, "target_class": 2},
        },
    }


def test_single_demand_runs_and_preserves_pixel_count(tmp_path):
    land = np.array([[1, 1, 1, 1, 1], [1, 1, 1, 2, 2], [1, 1, 2, 2, 2],
                     [1, 1, 2, 2, 2], [1, 1, 2, 2, 2]], dtype=np.uint8)
    probability = np.stack([
        np.full((5, 5), 0.55, dtype=np.float32),
        np.full((5, 5), 0.45, dtype=np.float32),
    ])
    _write(tmp_path / "land.tif", land)
    _write(tmp_path / "prob.tif", probability)

    model = FLUSCA(_cfg(tmp_path)).load().run(verbose=False)
    assert model.result.shape == land.shape
    assert int(model.counts.sum()) == land.size
    assert set(np.unique(model.result)).issubset({1, 2})


def test_rejects_even_neighborhood(tmp_path):
    cfg = _cfg(tmp_path)
    cfg["simulation"]["neighborhood_size"] = 4
    try:
        _validate_config(cfg)
    except ValueError as exc:
        assert "impar" in str(exc)
    else:
        raise AssertionError("Debió rechazar una vecindad par")


def test_rejects_misaligned_probability_grid(tmp_path):
    land = np.ones((5, 5), dtype=np.uint8)
    probability = np.ones((2, 5, 5), dtype=np.float32) / 2
    _write(tmp_path / "land.tif", land)
    _write(tmp_path / "prob.tif", probability, transform=from_origin(1, 5, 1, 1))
    try:
        FLUSCA(_cfg(tmp_path)).load()
    except ValueError as exc:
        assert "grilla" in str(exc)
    else:
        raise AssertionError("Debió rechazar una grilla desalineada")
