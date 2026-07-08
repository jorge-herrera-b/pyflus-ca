# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import numpy as np
import yaml


def _read_lines(path: str | Path):
    return [
        x.strip()
        for x in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
        if x.strip()
    ]


def _get_after(lines, tag: str):
    if tag not in lines:
        raise ValueError(f"No encontré la etiqueta {tag} en el archivo.")
    return lines[lines.index(tag) + 1]


def load_config(path: str | Path) -> dict[str, Any]:
    """Lee un archivo YAML único con rasters + parámetros + hyperparámetros."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    _validate_config(cfg)
    return cfg


def save_config(cfg: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def _validate_config(cfg: dict[str, Any]) -> None:
    required_top = ["rasters", "classes", "simulation"]
    for key in required_top:
        if key not in cfg:
            raise ValueError(f"Falta sección obligatoria: {key}")

    rasters = cfg["rasters"]
    for key in ["landuse", "probability", "output"]:
        if key not in rasters:
            raise ValueError(f"Falta rasters.{key}")

    sim = cfg["simulation"]
    for key in [
        "future_pixels",
        "cost_matrix",
        "neighborhood_weights",
        "max_iterations",
        "neighborhood_size",
        "acceleration",
    ]:
        if key not in sim:
            raise ValueError(f"Falta simulation.{key}")

    n_types = int(cfg["classes"]["n_types"])
    if len(sim["future_pixels"]) != n_types:
        raise ValueError("simulation.future_pixels debe tener largo igual a classes.n_types")
    if len(sim["neighborhood_weights"]) != n_types:
        raise ValueError("simulation.neighborhood_weights debe tener largo igual a classes.n_types")
    if len(sim["cost_matrix"]) != n_types:
        raise ValueError("simulation.cost_matrix debe tener n_types filas")
    for row in sim["cost_matrix"]:
        if len(row) != n_types:
            raise ValueError("Cada fila de simulation.cost_matrix debe tener n_types columnas")


def config_from_gui_logs(
    log_simulation: str | Path,
    config_mp: str | Path,
    output_yaml: Optional[str | Path] = None,
) -> dict[str, Any]:
    """
    Convierte los archivos de FLUS GUI a un YAML único.

    Lee:
    - logFileSimulation.log: rutas de landuse/probability/output/restricted
    - config_mp.log: demanda, matriz, pesos, iteraciones, vecindad, aceleración, etc.
    """
    log_lines = _read_lines(log_simulation)
    mp_lines = _read_lines(config_mp)

    landuse_path = _get_after(log_lines, "[Path of land use data]")
    probability_path = _get_after(log_lines, "[Path of probability data]")
    output_path = _get_after(log_lines, "[Path of simulation result]")
    restricted_path = _get_after(log_lines, "[Path of restricted area]")
    if restricted_path == "No restrict data":
        restricted_path = None

    n_types = int(_get_after(mp_lines, "[Number of types]"))

    i = mp_lines.index("[Future Pixels]") + 1
    future_pixels = [int(mp_lines[i + k].split(",")[0]) for k in range(n_types)]

    i = mp_lines.index("[Cost Matrix]") + 1
    cost_matrix = [
        [float(v) for v in mp_lines[i + k].split(",")]
        for k in range(n_types)
    ]

    i = mp_lines.index("[Intensity of neighborhood]") + 1
    neighborhood_weights = [
        float(mp_lines[i + k].split(",")[0])
        for k in range(n_types)
    ]

    max_iter = int(_get_after(mp_lines, "[Maximum Number Of Iterations]"))
    neighborhood_size = int(_get_after(mp_lines, "[Size of neighborhood]"))
    acceleration = float(_get_after(mp_lines, "[Accelerated factor]"))

    enclaves = None
    if "[Enclaves for land use type]" in mp_lines:
        enclaves = int(_get_after(mp_lines, "[Enclaves for land use type]"))

    thread = None
    if "[Thread]" in mp_lines:
        thread = int(_get_after(mp_lines, "[Thread]"))

    cfg = {
        "rasters": {
            "landuse": landuse_path,
            "probability": probability_path,
            "restricted": restricted_path,
            "output": output_path,
        },
        "classes": {
            "n_types": n_types,
            "codes": list(range(1, n_types + 1)),
            "names": [f"Landuse{i}" for i in range(1, n_types + 1)],
        },
        "simulation": {
            "future_pixels": future_pixels,
            "cost_matrix": cost_matrix,
            "neighborhood_weights": neighborhood_weights,
            "max_iterations": max_iter,
            "neighborhood_size": neighborhood_size,
            "acceleration": acceleration,
            "enclaves_for_landuse_type": enclaves,
            "thread": thread,
        },
        "hyperparameters": {
            "seed": 123,
            "stop_tolerance_fraction": 0.0001,
            "stable_iterations": 5,
            "darea": {
                "enabled": True,
                "restricted_value": 2,
                "target_class": 2,
            },
            "save_history_csv": None,
        },
        "batch": {
            "enabled": False,
            "output_dir": None,
            "vary": {},
        },
    }

    if output_yaml is not None:
        save_config(cfg, output_yaml)

    return cfg
