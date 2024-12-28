# views/main_view.py

import os
import tempfile
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QComboBox, QPushButton, QFormLayout,
    QSpinBox, QDoubleSpinBox, QSizePolicy, QFrame, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QGuiApplication

class PlotBridge(QWebChannel):
    """
    PlotBridge: For 2-way sync of zoom (time/freq).
    """
    #windowDurationChanged = Signal(int)
    freqRangeChanged = Signal(int,int)

    #@Slot(int)
    #def onZoom(self, duration_sec):
    #    self.windowDurationChanged.emit(duration_sec)

    @Slot(int,int)
    def onFreqZoom(self, fmin, fmax):
        self.freqRangeChanged.emit(fmin, fmax)


class MainView(QMainWindow):
    """
    The main GUI window for ABP analysis.
    """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.plots = {}
        self.temp_files = []

    def init_ui(self):
        # ~80% screen size
        screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        w = int(geometry.width() * 0.8)
        h = int(geometry.height() * 0.8)
        self.resize(w, h)
        self.setWindowTitle("ABP Analysis Tool")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        controls_layout = QVBoxLayout()

        # -----------------------------------------
        # Record Selection
        # -----------------------------------------
        record_group = QGroupBox("Record Selection")
        record_layout = QGridLayout()
        record_group.setLayout(record_layout)

        self.record_combo = QComboBox()
        self.record_combo.setObjectName("record_combo")
        record_layout.addWidget(QLabel("Select Record:"), 0, 0, alignment=Qt.AlignRight)
        record_layout.addWidget(self.record_combo, 0, 1)

        self.load_button = QPushButton("Load Record")
        self.load_button.setObjectName("load_button")
        record_layout.addWidget(self.load_button, 1, 0, 1, 2, alignment=Qt.AlignCenter)

        controls_layout.addWidget(record_group)

        # -----------------------------------------
        # Filter Selection
        # -----------------------------------------
        filter_group = QGroupBox("Filter Selection")
        filter_layout = QFormLayout()
        filter_group.setLayout(filter_layout)

        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["Butterworth", "Running Mean", "Gaussian"])
        filter_layout.addRow(QLabel("Filter Type:"), self.filter_type_combo)
        controls_layout.addWidget(filter_group)

        # -----------------------------------------
        # Butterworth Filter Parameters
        # -----------------------------------------
        self.butterworth_group = QGroupBox("Butterworth Filter Parameters")
        butter_layout = QFormLayout()
        self.butterworth_group.setLayout(butter_layout)

        self.lowcut_spin = QDoubleSpinBox()
        self.lowcut_spin.setRange(0.01, 100.0)
        self.lowcut_spin.setValue(0.3)
        self.lowcut_spin.setSingleStep(0.1)
        self.lowcut_spin.setDecimals(2)
        butter_layout.addRow(QLabel("Lowcut Frequency (Hz):"), self.lowcut_spin)

        self.highcut_spin = QDoubleSpinBox()
        self.highcut_spin.setRange(0.1, 100.0)
        self.highcut_spin.setValue(8.0)
        self.highcut_spin.setSingleStep(0.1)
        self.highcut_spin.setDecimals(2)
        butter_layout.addRow(QLabel("Highcut Frequency (Hz):"), self.highcut_spin)

        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 10)
        self.order_spin.setValue(4)
        butter_layout.addRow(QLabel("Filter Order:"), self.order_spin)

        controls_layout.addWidget(self.butterworth_group)

        # -----------------------------------------
        # Running Mean Filter Parameters
        # -----------------------------------------
        self.running_mean_group = QGroupBox("Running Mean Filter Parameters")
        run_layout = QFormLayout()
        self.running_mean_group.setLayout(run_layout)

        self.window_size_spin = QSpinBox()
        self.window_size_spin.setRange(1, 100)
        self.window_size_spin.setValue(5)
        run_layout.addRow(QLabel("Window Size (samples):"), self.window_size_spin)

        controls_layout.addWidget(self.running_mean_group)

        # -----------------------------------------
        # Gaussian Smoothing Filter Parameters
        # -----------------------------------------
        self.gaussian_group = QGroupBox("Gaussian Smoothing Filter Parameters")
        gaus_layout = QFormLayout()
        self.gaussian_group.setLayout(gaus_layout)

        # CHANGED from "FWHM (s)" to "FWHM (ms)"
        self.fwhm_spin = QDoubleSpinBox()
        self.fwhm_spin.setRange(0.1, 10000.0)  # maybe bigger range for ms
        self.fwhm_spin.setValue(100.0)        # default = 100ms
        self.fwhm_spin.setSingleStep(100.0)
        self.fwhm_spin.setDecimals(2)
        gaus_layout.addRow(QLabel("FWHM (ms):"), self.fwhm_spin)

        controls_layout.addWidget(self.gaussian_group)

        # Show Butterworth by default
        self.butterworth_group.show()
        self.running_mean_group.hide()
        self.gaussian_group.hide()

        # -----------------------------------------
        # Window Duration
        # -----------------------------------------
        #wd_group = QGroupBox("Window Duration")
        #wd_layout = QFormLayout()
        #wd_group.setLayout(wd_layout)

        #self.window_duration_spin = QSpinBox()
        #self.window_duration_spin.setRange(1, 600)
        #self.window_duration_spin.setValue(5)
        #wd_layout.addRow(QLabel("Window Duration (sec):"), self.window_duration_spin)

        #controls_layout.addWidget(wd_group)

        # -----------------------------------------
        # Analysis Parameters
        # -----------------------------------------
        param_group = QGroupBox("Analysis Parameters")
        param_layout = QFormLayout()
        param_group.setLayout(param_layout)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 99)
        self.threshold_spin.setValue(70)
        param_layout.addRow(QLabel("Peak Threshold (%ile):"), self.threshold_spin)

        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(0.01, 5.0)
        self.distance_spin.setValue(0.5)
        self.distance_spin.setSingleStep(0.1)
        self.distance_spin.setDecimals(2)
        param_layout.addRow(QLabel("Peak Distance (s):"), self.distance_spin)

        self.min_value_spin = QDoubleSpinBox()
        self.min_value_spin.setRange(0.0, 300.0)
        self.min_value_spin.setValue(60.0)
        self.min_value_spin.setSingleStep(1.0)
        self.min_value_spin.setDecimals(2)
        param_layout.addRow(QLabel("Allowed Min Value:"), self.min_value_spin)

        self.max_value_spin = QDoubleSpinBox()
        self.max_value_spin.setRange(0.0, 300.0)
        self.max_value_spin.setValue(180.0)
        self.max_value_spin.setSingleStep(1.0)
        self.max_value_spin.setDecimals(2)
        param_layout.addRow(QLabel("Allowed Max Value:"), self.max_value_spin)

        self.apply_button = QPushButton("Apply Parameters")
        param_layout.addRow(self.apply_button)
        controls_layout.addWidget(param_group)

        # -----------------------------------------
        # Plot Options
        # -----------------------------------------
        plot_group = QGroupBox("Plot Options")
        plot_layout = QVBoxLayout()
        plot_group.setLayout(plot_layout)

        self.plot_combo = QComboBox()
        self.plot_combo.addItems(["Time-Domain Analysis", "Frequency-Domain Analysis","Histogram"])
        plot_layout.addWidget(QLabel("Select Graph:"))
        plot_layout.addWidget(self.plot_combo)

        controls_layout.addWidget(plot_group)

        # -----------------------------------------
        # Frequency-Domain Analysis Options
        # -----------------------------------------
        self.freq_domain_group = QGroupBox("Frequency-Domain Analysis Options")
        freq_layout = QFormLayout()
        self.freq_domain_group.setLayout(freq_layout)

        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.0, 200.0)
        self.freq_min_spin.setValue(0.0)
        self.freq_min_spin.setSingleStep(1.0)
        self.freq_min_spin.setDecimals(2)
        freq_layout.addRow(QLabel("Min Frequency (Hz):"), self.freq_min_spin)

        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(0.1, 200.0)
        self.freq_max_spin.setValue(20.0)
        self.freq_max_spin.setSingleStep(1.0)
        self.freq_max_spin.setDecimals(2)
        freq_layout.addRow(QLabel("Max Frequency (Hz):"), self.freq_max_spin)

        self.freq_mag_min_spin = QDoubleSpinBox()
        self.freq_mag_min_spin.setRange(0.0, 1000.0)
        self.freq_mag_min_spin.setValue(0.0)
        self.freq_mag_min_spin.setSingleStep(10.0)
        self.freq_mag_min_spin.setDecimals(2)
        freq_layout.addRow(QLabel("Min Magnitude:"), self.freq_mag_min_spin)

        self.freq_mag_max_spin = QDoubleSpinBox()
        self.freq_mag_max_spin.setRange(0.0, 1000.0)
        self.freq_mag_max_spin.setValue(20.0)
        self.freq_mag_max_spin.setSingleStep(10.0)
        self.freq_mag_max_spin.setDecimals(2)
        freq_layout.addRow(QLabel("Max Magnitude:"), self.freq_mag_max_spin)

        self.freq_domain_group.hide()
        controls_layout.addWidget(self.freq_domain_group)

        # -----------------------------------------
        # Summary Metrics
        # -----------------------------------------
        summary_group = QGroupBox("Summary Metrics")
        summary_layout = QGridLayout()
        summary_group.setLayout(summary_layout)

        # CHANGED the RMSSD labels from (s) -> (ms)
        metrics = {
            "Heart Rate (bpm)": "hr_original_label",
            "Heart Rate Variability (RMSSD) (ms)": "hrv_original_label",
            "Pulse Pressure (mmHg)": "pp_original_label",
            "Signal Quality Index (SQI)": "sqi_original_label",
            "Heart Rate (bpm) [Filtered]": "hr_filtered_label",
            "Heart Rate Variability (RMSSD) (ms) [Filtered]": "hrv_filtered_label",
            "Pulse Pressure (mmHg) [Filtered]": "pp_filtered_label",
            "Signal Quality Index (SQI) [Filtered]": "sqi_filtered_label"
        }

        row = 0
        for metric_name, objName in metrics.items():
            labN = QLabel(metric_name + ":")
            labV = QLabel("N/A")
            labV.setObjectName(objName)
            summary_layout.addWidget(labN, row, 0, alignment=Qt.AlignRight)
            summary_layout.addWidget(labV, row, 1, alignment=Qt.AlignLeft)
            row += 1

        controls_layout.addWidget(summary_group)
        controls_layout.addStretch()

        content_layout.addLayout(controls_layout, stretch=1)

        # Right Panel: QWebEngineViews
        plot_display_layout = QVBoxLayout()

        self.plot_view = QWebEngineView()
        self.plot_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_display_layout.addWidget(self.plot_view)

        self.filter_response_view = QWebEngineView()
        self.filter_response_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_display_layout.addWidget(self.filter_response_view)

        content_layout.addLayout(plot_display_layout, stretch=3)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")


    def update_plots(self, time_plot_html, freq_plot_html, histogram_html, filter_response_html):
        self.plots = {
            "Time-Domain Analysis": time_plot_html,
            "Frequency-Domain Analysis": freq_plot_html,
            "Histogram": histogram_html,
        }
        self.update_filter_response_plot(filter_response_html)

    def update_filter_response_plot(self, filter_response_html):
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tf:
                tf.write(filter_response_html.encode('utf-8'))
                path = tf.name
                self.temp_files.append(path)
            self.filter_response_view.setUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            logging.error(f"Filter freq response load error: {e}")
            self.filter_response_view.setHtml("<h3>Error loading Filter Frequency Response plot.</h3>")
            self.status_bar.showMessage("Error loading Filter Frequency Response plot.")

    def get_plot_html(self, plot_type: str):
        return self.plots.get(plot_type, "<h3>Plot not available.</h3>")

    def show_error_message(self, title, msg):
        QMessageBox.critical(self, title, msg)

    def show_info_message(self, title, msg):
        QMessageBox.information(self, title, msg)

    def closeEvent(self, event):
        logging.info("Application is closing. Deleting temp files.")
        for fp in self.temp_files:
            try:
                os.remove(fp)
            except Exception as e:
                logging.warning(f"Failed to remove temp file '{fp}': {e}")
        event.accept()
