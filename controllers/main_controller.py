# controllers/main_controller.py

import logging
from PySide6.QtCore import QUrl, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QLabel

from models.abp_model import ABPModel
from views.main_view import MainView, PlotBridge
from plots.plot_functions import (
    generate_time_domain_plot,
    generate_histogram_plot,
    generate_frequency_domain_plot,
    generate_filter_frequency_response_plot
)
from utils.helper_functions import validate_value_range, format_metric

class MainController:
    def __init__(self, view: MainView, model: ABPModel):
        self.view = view
        self.model = model
        self.temp_files = []

        self.all_records = [
            "p09/p099982/3001360_0001",
            "p09/p099982/3001360_0002",
            "p09/p099982/3001360_0003",
        ]
        self.view.record_combo.addItems(self.all_records)

        # Connect signals
        self.view.load_button.clicked.connect(self.load_record)
        self.view.apply_button.clicked.connect(self.apply_parameters)
        self.view.plot_combo.currentIndexChanged.connect(self.display_selected_plot)

        self.view.freq_min_spin.valueChanged.connect(self.update_frequency_domain_plot)
        self.view.freq_max_spin.valueChanged.connect(self.update_frequency_domain_plot)
        self.view.freq_mag_min_spin.valueChanged.connect(self.update_frequency_domain_plot)
        self.view.freq_mag_max_spin.valueChanged.connect(self.update_frequency_domain_plot)

        self.view.filter_type_combo.currentTextChanged.connect(self.update_filter_parameters_visibility)
        #self.view.window_duration_spin.valueChanged.connect(self.on_window_duration_changed)

        self.setup_web_channel()
        self.view.status_bar.showMessage("Ready")

    def setup_web_channel(self):
        self.channel = QWebChannel()
        self.bridge = PlotBridge()
        self.channel.registerObject('bridge', self.bridge)

        self.view.plot_view.page().setWebChannel(self.channel)
        self.view.filter_response_view.page().setWebChannel(self.channel)

        #self.bridge.windowDurationChanged.connect(self.on_plot_zoom)
        self.bridge.freqRangeChanged.connect(self.on_plot_freq_zoom)

    def update_filter_parameters_visibility(self, filter_type: str):
        if filter_type=="Butterworth":
            self.view.butterworth_group.show()
            self.view.running_mean_group.hide()
            self.view.gaussian_group.hide()
        elif filter_type=="Running Mean":
            self.view.butterworth_group.hide()
            self.view.running_mean_group.show()
            self.view.gaussian_group.hide()
        elif filter_type=="Gaussian":
            self.view.butterworth_group.hide()
            self.view.running_mean_group.hide()
            self.view.gaussian_group.show()
        else:
            self.view.butterworth_group.hide()
            self.view.running_mean_group.hide()
            self.view.gaussian_group.hide()

    def load_record(self):
        rec = self.view.record_combo.currentText()
        logging.info(f"Loading record {rec} ...")
        if not self.model.load_record(rec):
            self.view.show_error_message("Load Error","Failed to load record.")
            return

        mn = self.view.min_value_spin.value()
        mx = self.view.max_value_spin.value()
        if not validate_value_range(mn,mx):
            self.view.show_error_message("Param Error","Min >= Max.")
            return

        rng_filter = self.model.apply_value_range_filter(self.model.abp_signal,mn,mx)
        if rng_filter is None or len(rng_filter)==0:
            self.view.show_error_message("Range Filter","No valid data in range.")
            return
        self.model.filtered_signal = rng_filter

        # set filter strategy
        ft = self.view.filter_type_combo.currentText()
        if ft=="Butterworth":
            lw = self.view.lowcut_spin.value()
            hi = self.view.highcut_spin.value()
            od = self.view.order_spin.value()
            self.model.set_filter_strategy("Butterworth", lowcut=lw, highcut=hi, order=od)
        elif ft=="Running Mean":
            ws = self.view.window_size_spin.value()
            self.model.set_filter_strategy("Running Mean", window_size=ws)
        elif ft=="Gaussian":
            fwhm = self.view.fwhm_spin.value()
            self.model.set_filter_strategy("Gaussian", fwhm=fwhm)
        else:
            self.view.show_error_message("Filter Error","Unknown filter type.")
            return

        if not self.model.apply_filter():
            self.view.show_error_message("Filter Error","Failed to apply filter.")
            return

        thr = self.view.threshold_spin.value()
        dist = self.view.distance_spin.value()
        if not self.model.detect_peaks(threshold_percentile=thr, min_distance_sec=dist):
            self.view.show_error_message("Peaks Error","Failed to detect peaks.")
            return

        if not self.model.calculate_metrics():
            self.view.show_error_message("Metrics Error","Failed to calc metrics.")
            return

        # Generate plots
        t_html = generate_time_domain_plot(
            self.model.abp_signal,self.model.filtered_signal,self.model.fs,
            self.model.peaks_original,self.model.peaks_filtered,self.model.unit
        )
        f_html = generate_frequency_domain_plot(
            self.model.abp_signal,self.model.filtered_signal,self.model.fs,
            freq_min=self.view.freq_min_spin.value(),
            freq_max=self.view.freq_max_spin.value(),
            mag_min=self.view.freq_mag_min_spin.value(),
            mag_max=self.view.freq_mag_max_spin.value(),
            unit="Hz"
        )
        h_html = generate_histogram_plot(
            self.model.abp_signal,self.model.filtered_signal,self.model.unit
        )
        fr_html = generate_filter_frequency_response_plot(
            self.model.filter_strategy,self.model.fs
        )
        self.view.update_plots(t_html,f_html,h_html,fr_html)
        self.update_summary_metrics()

        # Display whichever plot is selected
        self.display_selected_plot()

        self.view.show_info_message("Record Loaded",
            f"'{rec}' loaded. #Samples={len(self.model.abp_signal)}, FS={self.model.fs} Hz.\n"
            f"Peaks(Orig)={len(self.model.peaks_original)}, Filt={len(self.model.peaks_filtered)}"
        )

    def apply_parameters(self):
        if not self.model.record_loaded:
            self.view.show_error_message("No Record","Load a record first.")
            return
        try:
            mn = self.view.min_value_spin.value()
            mx = self.view.max_value_spin.value()
            if not validate_value_range(mn,mx):
                raise ValueError("Min >= Max.")
            rngf = self.model.apply_value_range_filter(self.model.abp_signal,mn,mx)
            if rngf is None or len(rngf)==0:
                raise ValueError("No valid data after range filter.")
            self.model.filtered_signal = rngf

            ft = self.view.filter_type_combo.currentText()
            if ft=="Butterworth":
                lw = self.view.lowcut_spin.value()
                hi = self.view.highcut_spin.value()
                od = self.view.order_spin.value()
                self.model.set_filter_strategy("Butterworth", lowcut=lw, highcut=hi, order=od)
            elif ft=="Running Mean":
                ws = self.view.window_size_spin.value()
                self.model.set_filter_strategy("Running Mean", window_size=ws)
            elif ft=="Gaussian":
                fwhm = self.view.fwhm_spin.value()
                self.model.set_filter_strategy("Gaussian", fwhm=fwhm)
            else:
                raise ValueError("Unknown filter type: "+ft)

            if not self.model.apply_filter():
                raise ValueError("Failed to apply filter.")

            thr = self.view.threshold_spin.value()
            dist = self.view.distance_spin.value()
            if not self.model.detect_peaks(threshold_percentile=thr,min_distance_sec=dist):
                raise ValueError("Detect peaks failed.")

            if not self.model.calculate_metrics():
                raise ValueError("Calc metrics failed.")

            # Re-gen plots
            t_html = generate_time_domain_plot(
                self.model.abp_signal,self.model.filtered_signal,self.model.fs,
                self.model.peaks_original,self.model.peaks_filtered,self.model.unit
            )
            f_html = generate_frequency_domain_plot(
                self.model.abp_signal,self.model.filtered_signal,self.model.fs,
                freq_min=self.view.freq_min_spin.value(),
                freq_max=self.view.freq_max_spin.value(),
                mag_min=self.view.freq_mag_min_spin.value(),
                mag_max=self.view.freq_mag_max_spin.value(),
                unit="Hz"
            )
            h_html = generate_histogram_plot(
                self.model.abp_signal,self.model.filtered_signal,self.model.unit
            )
            fr_html = generate_filter_frequency_response_plot(
                self.model.filter_strategy,self.model.fs
            )
            self.view.update_plots(t_html,f_html,h_html,fr_html)
            self.update_summary_metrics()

            self.display_selected_plot()
            self.view.show_info_message("Parameters Applied","Analysis updated.")
        except Exception as e:
            logging.error(f"apply_parameters error: {e}")
            self.view.show_error_message("Apply Error", str(e))

    def display_selected_plot(self):
        pt = self.view.plot_combo.currentText()
        logging.info(f"display_selected_plot => {pt}")
        if pt=="Histogram":
            self.view.freq_domain_group.hide()
            html = self.view.get_plot_html("Histogram")
        elif pt=="Time-Domain Analysis":
            self.view.freq_domain_group.hide()
            html = self.view.get_plot_html("Time-Domain Analysis")
        elif pt=="Frequency-Domain Analysis":
            self.view.freq_domain_group.show()
            html = self.view.get_plot_html("Frequency-Domain Analysis")
        else:
            html = "<h3>Unknown plot selection</h3>"

        self.load_plot(html)

        # If time-domain, apply window duration
        #if pt=="Time-Domain Analysis":
        #    dur = self.view.window_duration_spin.value()
        #    self.on_window_duration_changed(dur)

    def update_frequency_domain_plot(self):
        # re-gen freq domain if that's the current selected
        if self.view.plot_combo.currentText()!="Frequency-Domain Analysis":
            return
        try:
            fm = self.view.freq_min_spin.value()
            fx = self.view.freq_max_spin.value()
            mgm = self.view.freq_mag_min_spin.value()
            mgx = self.view.freq_mag_max_spin.value()
            if fm>=fx:
                raise ValueError("freq min >= freq max")
            html = generate_frequency_domain_plot(
                self.model.abp_signal,self.model.filtered_signal,self.model.fs,
                freq_min=fm,freq_max=fx,
                mag_min=mgm,mag_max=mgx,
                unit="Hz"
            )
            self.load_plot(html)
        except Exception as e:
            logging.error(f"update_frequency_domain_plot error: {e}")
            self.view.show_error_message("Freq Plot Error", str(e))

    def load_plot(self, html_content):
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tf:
                tf.write(html_content.encode('utf-8'))
                path = tf.name
                self.temp_files.append(path)
            self.view.plot_view.setUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            logging.error(f"load_plot error: {e}")
            self.view.plot_view.setHtml("<h3>Error loading plot.</h3>")

    def update_summary_metrics(self):
        logging.debug("Updating summary metrics.")
        m = {
            "hr_original_label": format_metric(
                self.model.hr_original.mean() if len(self.model.hr_original)>0 else None, "bpm"
            ),
            "hrv_original_label": format_metric(
                self.model.hrv_original if self.model.hrv_original>0 else None, "ms"
            ),
            "sqi_original_label": format_metric(
                self.model.sqi_original if self.model.sqi_original>0 else None
            ),
            "pp_original_label": format_metric(
                self.model.pp_original if self.model.pp_original>0 else None, "mmHg"
            ),
            "hr_filtered_label": format_metric(
                self.model.hr_filtered.mean() if len(self.model.hr_filtered)>0 else None, "bpm"
            ),
            "hrv_filtered_label": format_metric(
                self.model.hrv_filtered if self.model.hrv_filtered>0 else None, "ms"
            ),
            "sqi_filtered_label": format_metric(
                self.model.sqi_filtered if self.model.sqi_filtered>0 else None
            ),
            "pp_filtered_label": format_metric(
                self.model.pp_filtered if self.model.pp_filtered>0 else None, "mmHg"
            )
        }
        for labid,val in m.items():
            lbl = self.view.findChild(QLabel, labid)
            if lbl:
                lbl.setText(val)

    def on_window_duration_changed(self, seconds):
        """
        If the current plot is Time-Domain, set x-axis to [0..seconds].
        Wait for Plotly to be loaded in the page, then do Plotly.relayout().
        """
        if not self.model.record_loaded:
            return

        current_plot = self.view.plot_combo.currentText()
        if current_plot == "Time-Domain Analysis":
            import logging
            logging.info(f"Window Duration => {seconds}s (Time-Domain).")

            # We embed JS that repeatedly checks (every 200ms) whether
            #   1) window.Plotly is defined
            #   2) document.getElementById('plot') is found
            # If both exist, it calls Plotly.relayout(), then stops.
            js_code = f"""
var targetSec = {seconds};
var checkInterval = setInterval(function() {{
    var plotDiv = document.getElementById('plot');
    if (window.Plotly && plotDiv) {{
        Plotly.relayout(plotDiv, {{
            'xaxis.range': [0, targetSec]
        }});
        clearInterval(checkInterval);
    }} else {{
        console.log('Plotly or #plot not found yet, retrying...');
    }}
}}, 200);
"""
            self.view.plot_view.page().runJavaScript(js_code)

    #@Slot(int)
    #def on_plot_zoom(self, duration_sec):
    #    """
    #    Called from JS if user zooms time domain => update spin box
    #    """
    #    logging.info(f"User zoom => time domain = {duration_sec}s.")
    #    self.view.window_duration_spin.blockSignals(True)
    #    self.view.window_duration_spin.setValue(duration_sec)
    #    self.view.window_duration_spin.blockSignals(False)

    @Slot(int,int)
    def on_plot_freq_zoom(self, fmin, fmax):
        """
        Called from JS if user zoom freq domain => update freq spin
        """
        logging.info(f"User freq zoom => min={fmin}, max={fmax}")
        if fmin<0: fmin=0
        if fmax<=fmin: fmax=fmin+1
        if fmax>200: fmax=200

        self.view.freq_min_spin.blockSignals(True)
        self.view.freq_max_spin.blockSignals(True)
        self.view.freq_min_spin.setValue(fmin)
        self.view.freq_max_spin.setValue(fmax)
        self.view.freq_min_spin.blockSignals(False)
        self.view.freq_max_spin.blockSignals(False)

        self.update_frequency_domain_plot()
