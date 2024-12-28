# ABP Signal Viewer

A user-friendly application for analyzing Arterial Blood Pressure (ABP) signals. The application allows you to load ABP records, apply signal processing techniques, and visualize various analyses such as time-domain analysis, histograms, frequency-domain analysis.

## Features

- **Record Selection**: Choose from available ABP records.
- **Signal Filtering**: Apply Butterworth bandpass filters with adjustable parameters.
- **Peak Detection**: Detect peaks in both original and filtered signals.
- **Metrics Calculation**: Compute Heart Rate (HR), Heart Rate Variability (HRV), Pulse Pressure (PP), and Signal Quality Index (SQI).
- **Multiple Plot Types**:
  - Time-Domain Analysis
  - Histogram
  - Frequency-Domain Analysis
- **User-Friendly Interface**: Organized controls and interactive plots.
- **Logging**: Detailed logs for debugging and monitoring.

## Requirements

- Python 3.7 or higher
- PySide6>=6.5.0

- plotly>=5.15.0

- wfdb>=2.5.0

- numpy>=1.24.0

- scipy>=1.10.0

- python-dotenv>=1.0.0

- PyWavelets>=1.3.0

- pyqtgraph>=0.13.0


## Usage

### Running the Application
1. **Run** `runme.bat` as an **administrator**.
2. When prompted with the options menu, select **Option 1** and press **Enter**.
3. After the application opens:
   - Select the desired record and click **Load Record**.
   - If you need to modify filter parameters, make the desired changes and click **Apply Parameters**.

### Building the Executable
1. **Run** `runme.bat` as an **administrator**.
2. When prompted with the options menu, select **Option 2** and press **Enter**.
3. The executable file will be located in the `dist` folder.
4. On some systems, you may need to:
   - Grant permissions in your system's antivirus software.
   - Adjust firewall settings to ensure the build works correctly.

## Notes
- The code has been tested on **Windows**, but not on **Linux**.
- If you notice that the data or graph is not updating:
  1. Change the selected graph to another graph.
  2. Switch back to the desired graph.