# d:\projects\abp_signal_viewer2\plots\plot_functions.py

import plotly.graph_objects as go
import numpy as np
import logging
from math import pi, log
from scipy.fft import fft, fftfreq
from scipy.signal import freqz, butter  # <-- freqz/butter come from scipy.signal
from models.abp_model import ButterworthFilter, RunningMeanFilter, GaussianFilter

def generate_time_domain_plot(original, filtered, fs,
                              peaks_original=None, peaks_filtered=None,
                              unit="mmHg"):
    """
    Generate a Time-Domain Analysis plot for original and filtered signals.
    """
    try:
        logging.debug("Generating Time-Domain plot.")
        time = np.arange(len(original)) / fs

        fig = go.Figure()

        # --- Original signal ---
        fig.add_trace(go.Scatter(
            x=time,
            y=original,
            mode='lines',
            name='Original',
            line=dict(color='blue')
        ))

        # --- Original peaks ---
        if peaks_original is not None and len(peaks_original) > 0:
            fig.add_trace(go.Scatter(
                x=time[peaks_original],
                y=original[peaks_original],
                mode='markers',
                name='Orig Peaks',
                marker=dict(color='red', size=5)
            ))

        # --- Filtered signal ---
        fig.add_trace(go.Scatter(
            x=time,
            y=filtered,
            mode='lines',
            name='Filtered',
            line=dict(color='green')
        ))

        # --- Filtered peaks ---
        if peaks_filtered is not None and len(peaks_filtered) > 0:
            fig.add_trace(go.Scatter(
                x=time[peaks_filtered],
                y=filtered[peaks_filtered],
                mode='markers',
                name='Filt Peaks',
                marker=dict(color='orange', size=5)
            ))

        fig.update_layout(
            title="Time-Domain Analysis",
            xaxis_title="Time (s)",
            yaxis_title=f"Amplitude ({unit})",
            template='plotly_white',
            height=600,
            showlegend=True
        )

        # Convert figure to HTML
        plot_html = fig.to_html(
            include_plotlyjs='always',
            full_html=False,
            div_id="plot"
        )

        # Additional JavaScript (non-f-string)
        additional_js = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  new QWebChannel(qt.webChannelTransport, function(channel){
      window.bridge = channel.objects.bridge;
  });
  var plot = document.getElementById('plot');
  if(plot) {
    plot.on('plotly_relayout', function(eventdata){
      if(eventdata['xaxis.range[0]']!==undefined && eventdata['xaxis.range[1]']!==undefined){
        var minT = eventdata['xaxis.range[0]'];
        var maxT = eventdata['xaxis.range[1]'];
        var durSec = Math.floor(maxT - minT);
        if(durSec<1) durSec=1;
        if(durSec>600) durSec=600;
        bridge.onZoom(durSec);
      }
    });
  }
</script>
        """

        # Combine into final HTML
        full_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body>
<div>{plot_html}</div>
{additional_js}
</body>
</html>
        """
        return full_html

    except Exception as e:
        logging.error(f"Time-Domain plot error: {e}")
        return "<h3>Error generating Time-Domain Analysis plot.</h3>"


def generate_histogram_plot(original, filtered, unit="mmHg"):
    """
    Generate histograms of Original and Filtered signals.
    """
    try:
        import plotly.subplots as sp
        logging.debug("Generating Histogram plot.")

        fig = sp.make_subplots(
            rows=2, cols=1,
            shared_xaxes=False,
            subplot_titles=("Original ABP Histogram", "Filtered ABP Histogram")
        )

        # Original
        fig.add_trace(go.Histogram(
            x=original,
            nbinsx=50,
            name='Original',
            marker_color='blue'
        ), row=1, col=1)

        # Filtered
        if filtered is not None and len(filtered) > 0:
            clean_f = filtered[~np.isnan(filtered)]
            if len(clean_f) > 0:
                fig.add_trace(go.Histogram(
                    x=clean_f,
                    nbinsx=50,
                    name='Filtered',
                    marker_color='green'
                ), row=2, col=1)
            else:
                fig.add_trace(go.Scatter(x=[], y=[]), row=2, col=1)
        else:
            fig.add_trace(go.Scatter(x=[], y=[]), row=2, col=1)

        fig.update_layout(
            title="Histogram Analysis",
            template='plotly_white',
            height=600,
            showlegend=True
        )
        fig.update_xaxes(title_text=f"Amplitude ({unit})", row=1, col=1)
        fig.update_xaxes(title_text=f"Amplitude ({unit})", row=2, col=1)

        plot_html = fig.to_html(
            include_plotlyjs='always',
            full_html=False,
            div_id="plot"
        )

        additional_js = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  new QWebChannel(qt.webChannelTransport, function(channel){
    window.bridge = channel.objects.bridge;
  });
  var plot = document.getElementById('plot');
  if(plot){
    plot.on('plotly_relayout', function(ev){
      if(ev['xaxis.range[0]']!==undefined && ev['xaxis.range[1]']!==undefined){
         var durSec = Math.floor(ev['xaxis.range[1]'] - ev['xaxis.range[0]']);
         if(durSec<1) durSec=1;
         if(durSec>600) durSec=600;
         bridge.onZoom(durSec);
      }
    });
  }
</script>
        """

        full_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body>
<div>{plot_html}</div>
{additional_js}
</body>
</html>
        """
        return full_html

    except Exception as e:
        logging.error(f"Histogram plot error: {e}")
        return "<h3>Error generating Histogram plot.</h3>"


def generate_frequency_domain_plot(original, filtered, fs,
                                   freq_min=0, freq_max=20,
                                   mag_min=None, mag_max=50, unit="Hz"):
    """
    Generate Frequency-Domain Analysis (FFT) for Original & Filtered ABP signals.
    """
    try:
        logging.debug("Generating Frequency-Domain plot.")
        oc = original[~np.isnan(original)]
        fc = filtered[~np.isnan(filtered)] if filtered is not None else np.array([])

        # Original
        N_o = len(oc)
        if N_o > 1:
            yf_o = fft(oc)
            xf_o = fftfreq(N_o, 1/fs)[:N_o//2]
            mag_o = (2.0 / N_o) * np.abs(yf_o[:N_o//2])
        else:
            xf_o, mag_o = np.array([]), np.array([])

        # Filtered
        N_f = len(fc)
        if N_f > 1:
            yf_f = fft(fc)
            xf_f = fftfreq(N_f, 1/fs)[:N_f//2]
            mag_f = (2.0 / N_f) * np.abs(yf_f[:N_f//2])
        else:
            xf_f, mag_f = np.array([]), np.array([])

        fig = go.Figure()

        if len(xf_o) > 0:
            fig.add_trace(go.Scatter(
                x=xf_o,
                y=mag_o,
                mode='lines',
                name='Original',
                line=dict(color='blue')
            ))
        if len(xf_f) > 0:
            fig.add_trace(go.Scatter(
                x=xf_f,
                y=mag_f,
                mode='lines',
                name='Filtered',
                line=dict(color='green')
            ))

        fig.update_layout(
            title="Frequency-Domain Analysis",
            xaxis_title=f"Frequency ({unit})",
            yaxis_title="Magnitude",
            template='plotly_white',
            height=600,
            showlegend=True
        )
        fig.update_xaxes(range=[freq_min, freq_max])
        if mag_min is not None and mag_max is not None and mag_max > mag_min:
            fig.update_yaxes(range=[mag_min, mag_max])

        plot_html = fig.to_html(
            include_plotlyjs='always',
            full_html=False,
            div_id="plot"
        )

        # Keep JavaScript as a normal triple-quoted string
        additional_js = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  new QWebChannel(qt.webChannelTransport, function(channel){
    window.bridge = channel.objects.bridge;
  });
  var plot = document.getElementById('plot');
  if(plot){
    plot.on('plotly_relayout', function(ev){
      if(ev['xaxis.range[0]']!==undefined && ev['xaxis.range[1]']!==undefined){
         var fMin = Math.floor(ev['xaxis.range[0]']);
         var fMax = Math.floor(ev['xaxis.range[1]']);
         if(fMin<0) fMin=0;
         if(fMax<=fMin) fMax=fMin+1;
         if(fMax>200) fMax=200;
         bridge.onFreqZoom(fMin,fMax);
      }
    });
  }
</script>
        """

        full_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body>
<div>{plot_html}</div>
{additional_js}
</body>
</html>
        """
        return full_html

    except Exception as e:
        logging.error(f"Frequency-Domain plot error: {e}")
        return "<h3>Error generating Frequency-Domain plot.</h3>"


def generate_filter_frequency_response_plot(filter_strategy, fs):
    """
    Show filter "response". 
    - Butterworth / RunningMean => frequency domain response
    - Gaussian => time-domain kernel response
    """
    logging.debug("Generating Filter Frequency Response plot.")
    if not filter_strategy:
        return "<h3>No filter strategy set.</h3>"

    try:
        nyquist = 0.5 * fs

        # BUTTERWORTH
        if isinstance(filter_strategy, ButterworthFilter):
            lowcut = filter_strategy.lowcut
            highcut = filter_strategy.highcut
            order = filter_strategy.order

            lc = max(0.001, min(lowcut, nyquist - 0.001))
            hc = max(lc + 0.001, min(highcut, nyquist - 0.001))

            b, a = butter(order, [lc/nyquist, hc/nyquist], btype='band')
            w, h = freqz(b, a, worN=8000)
            freq = w * (nyquist / np.pi)
            mag = 20 * np.log10(np.abs(h) + 1e-6)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=freq, y=mag,
                mode='lines', line=dict(color='blue'),
                name='ButterworthResp'
            ))
            fig.add_vline(x=lc, line=dict(color='green', dash='dash'),
                          annotation_text='Lowcut', line_width=2)
            fig.add_vline(x=hc, line=dict(color='red', dash='dash'),
                          annotation_text='Highcut', line_width=2)

            fig.update_layout(
                title='Butterworth Filter Frequency Response',
                xaxis_title='Frequency (Hz)',
                yaxis_title='Magnitude (dB)',
                template='plotly_white',
                height=400,
                showlegend=False
            )
            fig.update_yaxes(range=[-100, 10])
            fig.update_xaxes(range=[0, nyquist])

            plot_html = fig.to_html(
                include_plotlyjs='always',
                full_html=False,
                div_id="plot"
            )
            return f"""
<html><head><meta charset="utf-8"></head>
<body>
<div>{plot_html}</div>
</body></html>
            """

        # RUNNING MEAN
        elif isinstance(filter_strategy, RunningMeanFilter):
            ws = filter_strategy.window_size
            kernel = np.ones(ws) / ws
            w, h = freqz(kernel, [1], worN=8000)
            freq = w * nyquist / np.pi
            mag = 20 * np.log10(np.abs(h) + 1e-6)
            cutoff_approx = fs / (2 * ws)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=freq, y=mag,
                mode='lines', line=dict(color='purple'),
                name='RunningMeanResp'
            ))
            fig.add_vline(x=cutoff_approx, line=dict(color='orange', dash='dash'),
                          annotation_text='Approx Cutoff', line_width=2)

            fig.update_layout(
                title=f'Running Mean Filter (window={ws}) Freq Response',
                xaxis_title='Frequency (Hz)',
                yaxis_title='Magnitude (dB)',
                template='plotly_white',
                height=400,
                showlegend=False
            )
            fig.update_yaxes(range=[-100, 10])
            fig.update_xaxes(range=[0, nyquist])

            plot_html = fig.to_html(
                include_plotlyjs='always',
                full_html=False,
                div_id="plot"
            )
            return f"""
<html><head><meta charset="utf-8"></head>
<body>
<div>{plot_html}</div>
</body></html>
            """

        # GAUSSIAN
        elif isinstance(filter_strategy, GaussianFilter):
            fwhm = filter_strategy.fwhm
            t_max = 3.0 * fwhm
            dt = 0.01 * fwhm
            t = np.arange(-t_max, t_max + dt, dt)
            ln2 = log(2.0)
            g = np.exp(-4.0 * ln2 * (t**2) / (fwhm**2))
            g /= g.max()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=t, y=g,
                mode='lines', line=dict(color='magenta'),
                name='Gaussian Kernel (Time-Domain)'
            ))
            fig.update_layout(
                title=f'Gaussian Filter Time Response (FWHM={fwhm}s)',
                xaxis_title='Time (s)',
                yaxis_title='Amplitude',
                template='plotly_white',
                height=400,
                showlegend=False
            )
            plot_html = fig.to_html(
                include_plotlyjs='always',
                full_html=False,
                div_id="plot"
            )
            return f"""
<html><head><meta charset="utf-8"></head>
<body>
<div>{plot_html}</div>
</body></html>
            """

        else:
            return "<h3>Unsupported filter strategy for frequency response.</h3>"

    except Exception as e:
        logging.error(f"Filter freq response error: {e}")
        return "<h3>Error generating Filter Frequency Response plot.</h3>"
