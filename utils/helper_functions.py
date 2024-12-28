# utils/helper_functions.py

import numpy as np
import math
import logging

def interpolate_nans(signal: np.ndarray):
    """
    Interpolate NaN values in the given signal linearly.
    If the entire signal is NaN, returns the signal unchanged.
    """
    if signal is None or len(signal) == 0:
        return signal
    
    sig_copy = signal.copy()
    nans = np.isnan(sig_copy)
    if nans.all():
        logging.warning("Signal is entirely NaNs; cannot interpolate.")
        return sig_copy

    x_valid = np.where(~nans)[0]
    y_valid = sig_copy[~nans]
    x_nans = np.where(nans)[0]

    sig_copy[nans] = np.interp(x_nans, x_valid, y_valid)
    return sig_copy

def validate_value_range(min_val: float, max_val: float) -> bool:
    """
    Return True if min_val < max_val; otherwise False.
    """
    return min_val < max_val

def format_metric(value, unit=None):
    """
    Format a numeric value plus optional unit. Returns 'N/A' if None or NaN.
    """
    if value is None or (isinstance(value, (int, float)) and math.isnan(value)):
        return "N/A"
    try:
        s = f"{value:.2f}"
        if unit:
            s += f" {unit}"
        return s
    except Exception:
        return "N/A"
