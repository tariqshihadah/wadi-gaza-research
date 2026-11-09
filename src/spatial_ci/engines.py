"""Interchangeable Moran's I correlogram engines."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from scipy.signal import correlate

from .models import CorrelogramData


class CorrelogramEngine(Protocol):
    """Protocol implemented by all correlogram engines."""

    def compute(self, values: np.ndarray, max_lag: int) -> CorrelogramData: ...


def _empty_result(
    values: np.ndarray, max_lag: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Prepare common valid-pixel arrays and output arrays."""
    valid = np.isfinite(values)
    n = int(valid.sum())
    if n < 2:
        raise ValueError("At least two valid pixels are required")
    mean = float(values[valid].mean())
    deviations = np.where(valid, values - mean, 0.0)
    denominator = float(np.square(deviations).sum())
    if denominator == 0:
        raise ValueError("Moran's I is undefined for a constant raster")
    lags = np.arange(1, max_lag + 1, dtype=int)
    return valid, deviations, lags, float(n), denominator


class FFTEngine:
    """Compute ring Moran's I using full FFT correlation."""

    def compute(self, values: np.ndarray, max_lag: int) -> CorrelogramData:
        """Compute Moran's I for all requested lags."""
        valid, deviations, lags, n, denominator = _empty_result(values, max_lag)
        mask = valid.astype(float)
        product_map = correlate(deviations, deviations, mode="full", method="fft")
        count_map = np.rint(correlate(mask, mask, mode="full", method="fft")).astype(np.int64)
        center = np.array(values.shape) - 1
        numerators = np.zeros(max_lag + 1)
        pair_counts = np.zeros(max_lag + 1, dtype=np.int64)
        for row in range(product_map.shape[0]):
            dy = row - center[0]
            for col in range(product_map.shape[1]):
                dx = col - center[1]
                lag = max(abs(dy), abs(dx))
                if 1 <= lag <= max_lag:
                    numerators[lag] += product_map[row, col]
                    pair_counts[lag] += count_map[row, col]
        moran = np.full(max_lag, np.nan)
        nonzero = pair_counts[1:] > 0
        moran[nonzero] = n / pair_counts[1:][nonzero] * numerators[1:][nonzero] / denominator
        return CorrelogramData(lags, moran, pair_counts[1:])


class BruteForceEngine:
    """Readable direct implementation of binary Chebyshev rings."""

    def compute(self, values: np.ndarray, max_lag: int) -> CorrelogramData:
        """Compute Moran's I by slicing every ring offset."""
        valid, deviations, lags, n, denominator = _empty_result(values, max_lag)
        moran = np.full(max_lag, np.nan)
        pair_counts = np.zeros(max_lag, dtype=np.int64)
        height, width = values.shape
        for lag in range(1, max_lag + 1):
            numerator = 0.0
            count = 0
            for dy in range(-lag, lag + 1):
                for dx in range(-lag, lag + 1):
                    if max(abs(dy), abs(dx)) != lag:
                        continue
                    source_rows, target_rows = _slices(height, dy)
                    source_cols, target_cols = _slices(width, dx)
                    source_valid = valid[source_rows, source_cols]
                    target_valid = valid[target_rows, target_cols]
                    paired = source_valid & target_valid
                    numerator += float(np.multiply(
                        deviations[source_rows, source_cols][paired],
                        deviations[target_rows, target_cols][paired],
                    ).sum())
                    count += int(paired.sum())
            pair_counts[lag - 1] = count
            if count:
                moran[lag - 1] = n / count * numerator / denominator
        return CorrelogramData(lags, moran, pair_counts)


def _slices(length: int, offset: int) -> tuple[slice, slice]:
    """Return aligned source and target slices for one offset."""
    if offset >= 0:
        return slice(0, length - offset), slice(offset, length)
    return slice(-offset, length), slice(0, length + offset)


class PySALEngine:
    """Compute rings with libpysal/esda for independent validation."""

    def __init__(self, max_pixels: int = 40_000):
        self.max_pixels = max_pixels

    def compute(self, values: np.ndarray, max_lag: int) -> CorrelogramData:
        """Compute binary-ring Moran's I using PySAL."""
        valid, _, lags, _, _ = _empty_result(values, max_lag)
        if values.size > self.max_pixels:
            raise ValueError(f"PySAL engine is limited to {self.max_pixels} grid pixels")
        try:
            from esda import Moran
            from libpysal.weights import lat2W
            from libpysal.weights.util import higher_order, w_subset
        except ImportError as exc:
            raise ImportError("PySALEngine requires optional packages libpysal and esda") from exc
        weights = lat2W(*values.shape, rook=False)
        ids = np.flatnonzero(valid).tolist()
        y = values[valid]
        moran = np.full(max_lag, np.nan)
        pair_counts = np.zeros(max_lag, dtype=np.int64)
        for index, lag in enumerate(range(1, max_lag + 1)):
            ring = w_subset(higher_order(weights, lag), ids)
            pair_counts[index] = int(round(ring.s0))
            if pair_counts[index]:
                moran[index] = float(Moran(y, ring, transformation="B", permutations=0).I)
        return CorrelogramData(lags, moran, pair_counts)


ENGINES = {"fft": FFTEngine, "bruteforce": BruteForceEngine, "pysal": PySALEngine}


def get_engine(name: str) -> CorrelogramEngine:
    """Return a configured correlogram engine by registry name."""
    try:
        return ENGINES[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown correlogram engine: {name}") from exc
