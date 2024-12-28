# models/abp_model.py

import os
import wfdb
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
import logging
from abc import ABC, abstractmethod

class FilterStrategy(ABC):
    """
    Abstract base class for filters.
    """
    @abstractmethod
    def apply(self, signal, fs):
        pass

class ButterworthFilter(FilterStrategy):
    """
    Butterworth bandpass filter for ABP signals.
    """
    def __init__(self, lowcut, highcut, order=4):
        self.lowcut = lowcut
        self.highcut = highcut
        self.order = order

    def apply(self, signal, fs):
        from scipy.signal import butter, filtfilt
        try:
            nyquist = 0.5 * fs
            # clamp
            low = max(0.001, min(self.lowcut, nyquist - 0.001))
            high = max(low + 0.001, min(self.highcut, nyquist - 0.001))
            if low >= high:
                raise ValueError(f"Invalid Butterworth freq: low={low}, high={high}.")

            b, a = butter(self.order, [low/nyquist, high/nyquist], btype='band')
            filtered = filtfilt(b, a, signal)
            logging.debug("Butterworth filter applied successfully.")
            return filtered
        except Exception as e:
            logging.error(f"ButterworthFilter error: {e}")
            return None

class RunningMeanFilter(FilterStrategy):
    """
    Running (moving) mean filter using a simple convolution.
    """
    def __init__(self, window_size=5):
        self.window_size = window_size

    def apply(self, signal, fs):
        import numpy as np
        try:
            if self.window_size < 1:
                raise ValueError("window_size must be >=1 for Running Mean.")
            kernel = np.ones(self.window_size)/self.window_size
            filtered = np.convolve(signal, kernel, mode='same')
            logging.debug("Running Mean filter applied successfully.")
            return filtered
        except Exception as e:
            logging.error(f"RunningMeanFilter error: {e}")
            return None

class GaussianFilter(FilterStrategy):
    """
    Gaussian Smoothing Filter using the formula:
      g(t) = exp( -4 ln(2) (t^2) / w^2 ),
    where w = FWHM in Mseconds.
    """
    def __init__(self, fwhm=0.01):
        # fwhm is now given in milliseconds, so let's store it in ms internally
        self.fwhm = fwhm

    def apply(self, signal, fs):
        import numpy as np
        import math
        try:
            if self.fwhm <= 0:
                raise ValueError("Gaussian FWHM must be > 0.")
            # Convert ms -> seconds
            fwhm_seconds = self.fwhm / 1000.0
            # now do the normal logic, using fwhm_seconds as 'w'
            # build kernel in time domain
            w = fwhm_seconds
            t_max = 3.0*w
            dt = 1.0/fs
            t = np.arange(-t_max, t_max+dt, dt)

            ln2 = math.log(2.0)
            kernel = np.exp(-4.0*ln2 * (t**2)/(w**2))
            # normalize area
            kernel /= np.sum(kernel)

            filtered = np.convolve(signal, kernel, mode='same')
            logging.debug("Gaussian smoothing (manual kernel) applied successfully.")
            return filtered
        except Exception as e:
            logging.error(f"GaussianFilter error: {e}")
            return None

class ABPModel:
    """
    ABPModel loads ABP signals, applies filters, detects peaks, calculates metrics.
    """
    def __init__(self, database_name="mimic3wdb-matched", data_dir="./data"):
        self.database_name = database_name
        self.data_dir = data_dir

        self.abp_signal = None
        self.fs = None
        self.unit = "mmHg"

        self.filtered_signal = None

        self.peaks_original = []
        self.peaks_filtered = []

        self.hr_original = []
        self.hr_filtered = []
        self.rr_intervals_original = []
        self.rr_intervals_filtered = []
        self.hrv_original = 0.0
        self.hrv_filtered = 0.0
        self.sqi_original = 0.0
        self.sqi_filtered = 0.0
        self.pp_original = 0.0
        self.pp_filtered = 0.0

        self.record_loaded = False
        self.filter_strategy = None

    def set_filter_strategy(self, filter_type, **kwargs):
        if filter_type == "Butterworth":
            self.filter_strategy = ButterworthFilter(
                lowcut=kwargs.get('lowcut', 0.5),
                highcut=kwargs.get('highcut', 20.0),
                order=kwargs.get('order', 4)
            )
        elif filter_type == "Running Mean":
            self.filter_strategy = RunningMeanFilter(
                window_size=kwargs.get('window_size', 5)
            )
        elif filter_type == "Gaussian":
            self.filter_strategy = GaussianFilter(
                fwhm=kwargs.get('fwhm', 1.0)
            )
        else:
            logging.error(f"Unknown filter type: {filter_type}")
            self.filter_strategy = None
        if self.filter_strategy:
            logging.info(f"Filter strategy set to {filter_type}.")

    def load_record(self, record_name):
        import os
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            hea_path = os.path.join(self.data_dir, f"{record_name}.hea")
            dat_path = os.path.join(self.data_dir, f"{record_name}.dat")

            if not os.path.exists(hea_path) or not os.path.exists(dat_path):
                logging.info(f"Downloading {record_name} from {self.database_name} ...")
                wfdb.dl_files(
                    self.database_name,
                    dl_dir=self.data_dir,
                    files=[f"{record_name}.hea", f"{record_name}.dat"]
                )
                logging.info("Download complete.")

            record = wfdb.rdrecord(os.path.join(self.data_dir, record_name))
            if "ABP" not in record.sig_name:
                logging.warning(f"No ABP channel found in {record_name}.")
                self.record_loaded = False
                return False

            idx = record.sig_name.index("ABP")
            self.abp_signal = record.p_signal[:, idx]
            self.fs = record.fs
            self.unit = record.units[idx]
            self.record_loaded = True
            logging.info(f"Loaded record {record_name} successfully.")
            return True
        except Exception as e:
            logging.error(f"Load record error: {e}")
            self.record_loaded = False
            return False

    def apply_filter(self):
        if self.abp_signal is None:
            logging.error("No abp_signal to filter.")
            return False
        if not self.filter_strategy:
            logging.error("No filter strategy set.")
            return False
        try:
            filtered = self.filter_strategy.apply(self.abp_signal, self.fs)
            if filtered is None:
                logging.error("Filter returned None.")
                return False
            self.filtered_signal = filtered
            logging.debug("apply_filter done.")
            return True
        except Exception as e:
            logging.error(f"apply_filter error: {e}")
            return False

    def apply_value_range_filter(self, signal, min_val, max_val):
        import numpy as np
        try:
            mask = (signal >= min_val) & (signal <= max_val)
            if not mask.any():
                logging.warning("No values in range.")
                return None
            ret = signal.copy()
            ret[~mask] = np.nan
            return ret
        except Exception as e:
            logging.error(f"value_range_filter error: {e}")
            return None

    def detect_peaks(self, threshold_percentile=95, min_distance_sec=0.5):
        from scipy.signal import find_peaks
        import numpy as np
        try:
            if self.abp_signal is None:
                return False
            distance_samples = int(min_distance_sec * self.fs)
            thr_orig = np.nanpercentile(self.abp_signal, threshold_percentile)
            self.peaks_original, _ = find_peaks(self.abp_signal, height=thr_orig, distance=distance_samples)

            if self.filtered_signal is not None:
                thr_filt = np.nanpercentile(self.filtered_signal, threshold_percentile)
                self.peaks_filtered, _ = find_peaks(self.filtered_signal, height=thr_filt, distance=distance_samples)
            else:
                self.peaks_filtered = []
            return True
        except Exception as e:
            logging.error(f"detect_peaks error: {e}")
            return False

    def calculate_rr_intervals(self, peaks, fs):
        import numpy as np
        if len(peaks) < 2:
            return np.array([])
        return np.diff(peaks) / fs

    def calculate_metrics(self):
        if not self.record_loaded:
            logging.error("No record loaded for metrics.")
            return False
        try:
            self.hr_original, self.rr_intervals_original = self.calculate_hr(self.peaks_original, self.fs)
            self.hrv_original = self.compute_hrv(self.rr_intervals_original)
            self.sqi_original = self.assess_sqi(self.abp_signal)
            self.pp_original = self.calculate_pp(self.abp_signal, self.peaks_original)

            self.hr_filtered, self.rr_intervals_filtered = self.calculate_hr(self.peaks_filtered, self.fs)
            self.hrv_filtered = self.compute_hrv(self.rr_intervals_filtered)
            if self.filtered_signal is not None:
                self.sqi_filtered = self.assess_sqi(self.filtered_signal)
                self.pp_filtered = self.calculate_pp(self.filtered_signal, self.peaks_filtered)
            else:
                self.sqi_filtered = 0.0
                self.pp_filtered = 0.0

            return True
        except Exception as e:
            logging.error(f"calculate_metrics error: {e}")
            return False

    def calculate_hr(self, peaks, fs):
        import numpy as np
        try:
            if len(peaks) < 2:
                return np.array([]), np.array([])
            rr = np.diff(peaks) / fs
            hr = 60.0 / rr
            return hr, rr
        except Exception as e:
            logging.error(f"calc_hr error: {e}")
            return np.array([]), np.array([])

    @staticmethod
    def compute_hrv(rr_intervals):
        import numpy as np
        try:
            if len(rr_intervals) < 2:
                return 0.0
            diff_rr = np.diff(rr_intervals)
            rmssd = np.sqrt(np.mean(diff_rr**2))
            # New: multiply by 1000 => ms
            return rmssd*1000.0
        except Exception as e:
            logging.error(f"compute_hrv error: {e}")
            return 0.0

    def calculate_pp(self, signal, peaks):
        import numpy as np
        try:
            if signal is None or len(signal) == 0 or len(peaks) == 0:
                return 0.0
            svals = signal[peaks]
            return float(np.nanmean(svals) - np.nanmin(signal))
        except Exception as e:
            logging.error(f"calc_pp error: {e}")
            return 0.0

    @staticmethod
    def assess_sqi(signal):
        import numpy as np
        try:
            if signal is None or len(signal) < 2:
                return 0.0
            good = ~np.isnan(signal)
            if good.sum() < 2:
                return 0.0
            s_cln = signal[good]
            avg_der = np.mean(np.abs(np.diff(s_cln)))
            mx = np.nanmax(s_cln)
            if mx == 0:
                return 0.0
            sqi = 1.0 - (avg_der / mx)
            return max(0.0, min(sqi, 1.0))
        except Exception as e:
            logging.error(f"assess_sqi error: {e}")
            return 0.0
