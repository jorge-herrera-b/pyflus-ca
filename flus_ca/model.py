# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional
import itertools
import copy

import numpy as np
import rasterio

from .config import load_config

try:
    from numba import njit
    NUMBA_OK = True
except Exception:
    NUMBA_OK = False


def _read_raster_1(path: str | Path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        profile = src.profile.copy()
    arr = np.where((arr > 0) & (arr <= 255), arr, 0).astype(np.uint8)
    return arr, profile


def _read_probability(path: str | Path, n_types: int):
    with rasterio.open(path) as src:
        arr = src.read(list(range(1, n_types + 1)))
    return arr.astype(np.float32)


def _read_restricted(path: Optional[str | Path], shape):
    if path is None:
        return np.ones(shape, dtype=np.uint8)
    with rasterio.open(path) as src:
        arr = src.read(1)
    return np.where((arr >= 0) & (arr <= 255), arr, 0).astype(np.uint8)


if NUMBA_OK:
    @njit
    def _count_classes(land, n_types):
        counts = np.zeros(n_types, dtype=np.int64)
        rows, cols = land.shape
        for i in range(rows):
            for j in range(cols):
                v = land[i, j]
                if 1 <= v <= n_types:
                    counts[v - 1] += 1
        return counts


    @njit
    def _run_ca(
        land0,
        prob,
        restricted,
        future_pixels,
        cost_matrix,
        weights,
        max_iter,
        neighborhood_size,
        acceleration,
        seed,
        stop_tolerance_fraction,
        stable_iterations,
        darea_enabled,
        darea_restricted_value,
        darea_target_class,
    ):
        np.random.seed(seed)

        rows, cols = land0.shape
        n_types = future_pixels.shape[0]

        land = land0.copy()
        temp = land0.copy()

        counts = _count_classes(land, n_types)
        pixel_sum = 0
        for c in range(n_types):
            pixel_sum += counts[c]

        if neighborhood_size != 1:
            num_windows = neighborhood_size * neighborhood_size - 1
        else:
            num_windows = 1
        half = neighborhood_size // 2

        initial_dist = np.zeros(n_types, dtype=np.float64)
        dyna_dist = np.zeros(n_types, dtype=np.float64)
        best_dist = np.zeros(n_types, dtype=np.float64)
        adjustment_effect = np.ones(n_types, dtype=np.float64)
        opposite2reverse = np.zeros(n_types, dtype=np.int64)
        dist_to_goal = np.zeros(n_types, dtype=np.int64)

        history = np.zeros((max_iter, n_types), dtype=np.int64)
        sumdiff_history = np.zeros(max_iter, dtype=np.int64)

        history_dis = 0
        statistic_history_dis = 0
        last_iter = 0

        val = np.zeros(n_types, dtype=np.int64)
        probability = np.zeros(n_types, dtype=np.float64)
        initial_prob = np.zeros(n_types, dtype=np.float64)
        roulette = np.zeros(n_types + 1, dtype=np.float64)
        neigh_prob = np.zeros(n_types, dtype=np.float64)

        for k in range(max_iter):
            for c in range(n_types):
                dist_to_goal[c] = future_pixels[c] - counts[c]

                if k == 0:
                    initial_dist[c] = dist_to_goal[c]
                    dyna_dist[c] = initial_dist[c] * 1.01
                    best_dist[c] = initial_dist[c]

                if initial_dist[c] == 0:
                    adjustment_effect[c] = 1.0
                    continue

                if abs(best_dist[c]) > abs(dist_to_goal[c]):
                    best_dist[c] = dist_to_goal[c]
                else:
                    if abs(initial_dist[c]) > 0:
                        if (abs(dist_to_goal[c]) - abs(best_dist[c])) / abs(initial_dist[c]) > 0.05:
                            opposite2reverse[c] = 1

                if dyna_dist[c] != 0:
                    adjustment = dist_to_goal[c] / dyna_dist[c]
                else:
                    adjustment = 0.0

                if adjustment < 1.0 and adjustment > 0.0:
                    dyna_dist[c] = dist_to_goal[c]

                    if initial_dist[c] > 0 and adjustment > (1.0 - acceleration):
                        adjustment_effect[c] = adjustment_effect[c] * (adjustment + acceleration)

                    if initial_dist[c] < 0 and adjustment > (1.0 - acceleration):
                        adjustment_effect[c] = adjustment_effect[c] * (1.0 / (adjustment + acceleration))

                if initial_dist[c] > 0 and adjustment > 1.0:
                    adjustment_effect[c] = adjustment_effect[c] * adjustment * adjustment

                if initial_dist[c] < 0 and adjustment > 1.0:
                    adjustment_effect[c] = adjustment_effect[c] * (1.0 / adjustment) * (1.0 / adjustment)

            for i in range(rows):
                for j in range(cols):
                    old_v = land[i, j]

                    if old_v < 1 or old_v > n_types:
                        temp[i, j] = old_v
                        continue

                    # Restricted == 0: no se permite cambio.
                    if restricted[i, j] == 0:
                        temp[i, j] = old_v
                        continue

                    old_type = old_v - 1

                    for c in range(n_types):
                        val[c] = 0
                        probability[c] = 0.0
                        initial_prob[c] = 0.0
                        neigh_prob[c] = 0.0

                    if neighborhood_size != 1:
                        for dx in range(-half, half + 1):
                            for dy in range(-half, half + 1):
                                if dx == 0 and dy == 0:
                                    continue
                                x = i + dx
                                y = j + dy
                                if x < 0 or y < 0 or x >= rows or y >= cols:
                                    continue
                                nb = land[x, y]
                                if 1 <= nb <= n_types:
                                    val[nb - 1] += 1
                    else:
                        for c in range(n_types):
                            val[c] = 1

                    inheritance = 10.0 * n_types

                    for c in range(n_types):
                        suit = prob[c, i, j]
                        initial_prob[c] = suit

                        neigh = (val[c] / num_windows) * (weights[c] + 0.000000001)
                        p = suit * neigh

                        if old_type == c:
                            p = p * adjustment_effect[c] * inheritance

                        p = p * cost_matrix[old_type, c]
                        probability[c] = p

                    total = 0.0
                    for c in range(n_types):
                        total += probability[c]

                    if total != 0.0:
                        for c in range(n_types):
                            neigh_prob[c] = probability[c] / total

                    # Política especial tipo DAREA usada por FLUS: celdas con valor 2 favorecen target_class.
                    if darea_enabled and restricted[i, j] == darea_restricted_value:
                        target = darea_target_class - 1
                        orig_left = 0.0
                        for c in range(n_types):
                            if c != target:
                                orig_left += neigh_prob[c]

                        rdm1 = np.random.random()
                        rdm2 = np.random.random()

                        if initial_prob[target] > rdm2:
                            neigh_prob[target] = neigh_prob[target] + rdm1
                            if neigh_prob[target] >= 1.0:
                                for c in range(n_types):
                                    neigh_prob[c] = 0.0
                                neigh_prob[target] = 1.0
                            else:
                                left_value = 1.0 - neigh_prob[target]
                                if orig_left > 0:
                                    for c in range(n_types):
                                        if c != target:
                                            neigh_prob[c] = neigh_prob[c] / orig_left * left_value

                    roulette[0] = 0.0
                    for c in range(n_types):
                        roulette[c + 1] = roulette[c] + neigh_prob[c]

                    r = np.random.random()
                    assigned = False

                    for new_type in range(n_types):
                        if r <= roulette[new_type + 1] and r > roulette[new_type]:
                            assigned = True
                            is_convert = False

                            if old_type != new_type and cost_matrix[old_type, new_type] != 0:
                                is_convert = True

                            dis_from = dist_to_goal[old_type]
                            dis_to = dist_to_goal[new_type]

                            if initial_dist[new_type] >= 0 and dis_to == 0:
                                adjustment_effect[new_type] = 1.0
                                is_convert = False

                            if initial_dist[old_type] <= 0 and dis_from == 0:
                                adjustment_effect[old_type] = 1.0
                                is_convert = False

                            if initial_dist[old_type] >= 0 and opposite2reverse[old_type] == 1:
                                is_convert = False

                            if initial_dist[new_type] <= 0 and opposite2reverse[new_type] == 1:
                                is_convert = False

                            if is_convert:
                                r3 = np.random.random()
                                if (r3 + (1.0 / n_types)) / (k + 1.0) < initial_prob[new_type]:
                                    is_convert = True
                                else:
                                    is_convert = False

                            if is_convert:
                                temp[i, j] = new_type + 1
                                counts[new_type] += 1
                                counts[old_type] -= 1
                                dist_to_goal[new_type] = future_pixels[new_type] - counts[new_type]
                                dist_to_goal[old_type] = future_pixels[old_type] - counts[old_type]
                            else:
                                temp[i, j] = old_v
                            break

                    if not assigned:
                        temp[i, j] = old_v

            # Actualiza mapa y conteos.
            for c in range(n_types):
                counts[c] = 0

            for i in range(rows):
                for j in range(cols):
                    land[i, j] = temp[i, j]
                    v = land[i, j]
                    if 1 <= v <= n_types:
                        counts[v - 1] += 1

            sum_dis = 0
            for c in range(n_types):
                history[k, c] = counts[c]
                diff = future_pixels[c] - counts[c]
                if diff < 0:
                    diff = -diff
                sum_dis += diff

            sumdiff_history[k] = sum_dis
            last_iter = k + 1

            if sum_dis == 0:
                break

            if k > stable_iterations and sum_dis < pixel_sum * stop_tolerance_fraction:
                break

            if sum_dis == history_dis:
                statistic_history_dis += 1
            else:
                statistic_history_dis = 0

            if statistic_history_dis > stable_iterations and sum_dis < pixel_sum * stop_tolerance_fraction:
                break

            history_dis = sum_dis

        return land, counts, history[:last_iter], sumdiff_history[:last_iter]

else:
    def _run_ca(*args, **kwargs):
        raise ImportError("Numba no está instalado. Ejecuta: pip install numba")


class FLUSCA:
    """Modelo CA de FLUS usando un solo archivo YAML."""

    def __init__(self, config_path: str | Path | dict):
        if isinstance(config_path, dict):
            self.cfg = config_path
        else:
            self.cfg = load_config(config_path)

        self.landuse = None
        self.profile = None
        self.probability = None
        self.restricted = None
        self.result = None
        self.counts = None
        self.history = None
        self.sumdiff_history = None

    def inspect(self) -> dict:
        return {
            "landuse": self.cfg["rasters"]["landuse"],
            "probability": self.cfg["rasters"]["probability"],
            "restricted": self.cfg["rasters"].get("restricted"),
            "output": self.cfg["rasters"]["output"],
            "n_types": self.cfg["classes"]["n_types"],
            "future_pixels": self.cfg["simulation"]["future_pixels"],
            "neighborhood_weights": self.cfg["simulation"]["neighborhood_weights"],
            "max_iterations": self.cfg["simulation"]["max_iterations"],
            "neighborhood_size": self.cfg["simulation"]["neighborhood_size"],
            "acceleration": self.cfg["simulation"]["acceleration"],
            "enclaves_for_landuse_type": self.cfg["simulation"].get("enclaves_for_landuse_type"),
            "thread": self.cfg["simulation"].get("thread"),
            "hyperparameters": self.cfg.get("hyperparameters", {}),
            "batch": self.cfg.get("batch", {}),
        }

    def print_inspect(self):
        for k, v in self.inspect().items():
            print(f"{k}: {v}")

    def load(self):
        n_types = int(self.cfg["classes"]["n_types"])
        rasters = self.cfg["rasters"]

        self.landuse, self.profile = _read_raster_1(rasters["landuse"])
        self.probability = _read_probability(rasters["probability"], n_types)
        self.restricted = _read_restricted(rasters.get("restricted"), self.landuse.shape)

        if self.probability.shape[1:] != self.landuse.shape:
            raise ValueError("El raster de probabilidad y landuse no tienen la misma dimensión.")
        if self.restricted.shape != self.landuse.shape:
            raise ValueError("El raster restricted y landuse no tienen la misma dimensión.")

        return self

    def run(self, seed: Optional[int] = None, verbose: bool = True):
        if self.landuse is None:
            self.load()

        sim = self.cfg["simulation"]
        hyp = self.cfg.get("hyperparameters", {})
        darea = hyp.get("darea", {})

        seed = int(seed if seed is not None else hyp.get("seed", 123))

        if verbose:
            self.print_inspect()

        result, counts, history, sumdiff_history = _run_ca(
            self.landuse,
            self.probability,
            self.restricted,
            np.asarray(sim["future_pixels"], dtype=np.int64),
            np.asarray(sim["cost_matrix"], dtype=np.float64),
            np.asarray(sim["neighborhood_weights"], dtype=np.float64),
            int(sim["max_iterations"]),
            int(sim["neighborhood_size"]),
            float(sim["acceleration"]),
            seed,
            float(hyp.get("stop_tolerance_fraction", 0.0001)),
            int(hyp.get("stable_iterations", 5)),
            bool(darea.get("enabled", True)),
            int(darea.get("restricted_value", 2)),
            int(darea.get("target_class", 2)),
        )

        self.result = result
        self.counts = counts
        self.history = history
        self.sumdiff_history = sumdiff_history

        if verbose:
            print("iteraciones:", len(history))
            print("conteos_finales:", counts.tolist())
            print("diferencia_final:", int(sumdiff_history[-1]) if len(sumdiff_history) else None)

        return self

    def save(self, output_path: Optional[str | Path] = None):
        if self.result is None:
            raise RuntimeError("Primero ejecuta run().")

        output_path = str(output_path or self.cfg["rasters"]["output"])
        profile = self.profile.copy()
        profile.update(count=1, dtype="uint8", nodata=0, compress="lzw")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(self.result.astype(np.uint8), 1)

        return output_path

    def save_history_csv(self, path: Optional[str | Path] = None):
        import pandas as pd

        if self.history is None:
            raise RuntimeError("Primero ejecuta run().")

        if path is None:
            hyp = self.cfg.get("hyperparameters", {})
            path = hyp.get("save_history_csv")

        if path is None:
            return None

        cols = [f"Landuse{i+1}" for i in range(int(self.cfg["classes"]["n_types"]))]
        df = pd.DataFrame(self.history, columns=cols)
        df.insert(0, "iteration", np.arange(1, len(df) + 1))
        df["sum_abs_diff"] = self.sumdiff_history
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        return path

    def run_and_save(self, seed: Optional[int] = None, verbose: bool = True):
        self.run(seed=seed, verbose=verbose)
        out = self.save()
        self.save_history_csv()
        return out


def run_batch_from_config(config_path: str | Path):
    """Corre un lote definido en la sección batch del YAML."""
    cfg = load_config(config_path)
    batch = cfg.get("batch", {})

    if not batch.get("enabled", False):
        model = FLUSCA(cfg)
        model.run_and_save()
        return [cfg["rasters"]["output"]]

    output_dir = Path(batch["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    vary = batch.get("vary", {})
    if not vary:
        raise ValueError("batch.enabled=true, pero batch.vary está vacío.")

    # Solo implementa variación de neighborhood_weights por ahora.
    nw_vary = vary.get("neighborhood_weights", {})
    keys = list(nw_vary.keys())
    values = [nw_vary[k] for k in keys]

    outputs = []
    for i, combo in enumerate(itertools.product(*values), start=1):
        cfg_i = copy.deepcopy(cfg)

        weights = list(cfg_i["simulation"]["neighborhood_weights"])
        for key, value in zip(keys, combo):
            # acepta Landuse3 o índice numérico 3
            if isinstance(key, str) and key.lower().startswith("landuse"):
                idx = int(key.lower().replace("landuse", "")) - 1
            else:
                idx = int(key) - 1
            weights[idx] = float(value)

        cfg_i["simulation"]["neighborhood_weights"] = weights
        cfg_i["rasters"]["output"] = str(output_dir / f"sim_{i:03d}.tif")
        cfg_i["hyperparameters"]["save_history_csv"] = str(output_dir / f"history_{i:03d}.csv")
        cfg_i["hyperparameters"]["seed"] = int(cfg_i["hyperparameters"].get("seed", 123)) + i

        model = FLUSCA(cfg_i)
        model.run_and_save(verbose=False)
        outputs.append(cfg_i["rasters"]["output"])
        print("Guardado:", cfg_i["rasters"]["output"])

    return outputs
