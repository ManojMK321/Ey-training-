# PPG Time Series — Exploratory Data Analysis

> **Photoplethysmography (PPG) signal analysis** pipeline for Red and IR channel data:  
> data cleaning · quality assessment · time-series decomposition · feature engineering · visualization.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Dataset Description](#dataset-description)
4. [Analysis Pipeline](#analysis-pipeline)
5. [Feature Engineering](#feature-engineering)
6. [Key Findings](#key-findings)
7. [Generated Artifacts](#generated-artifacts)
8. [Requirements & Setup](#requirements--setup)
9. [How to Run](#how-to-run)

---

## Project Overview

This project performs a comprehensive **Exploratory Data Analysis (EDA)** on raw PPG (Photoplethysmography) time-series data collected at approximately **50 Hz** (20 ms per sample). PPG sensors measure blood volume changes in peripheral tissue using two light wavelengths:

| Channel | Wavelength | Purpose |
|---------|-----------|---------|
| `red` | Red light (~660 nm) | Blood oxygen / pulse detection |
| `ir` | Infrared light (~940 nm) | Blood oxygen (SpO₂) reference |
| `red_corrected` | Derived | DC-component removed; AC pulse-wave |
| `ir_corrected` | Derived | DC-component removed; AC pulse-wave |

The pipeline covers **six stages**: data loading, quality checks, statistical profiling, outlier analysis, time-series decomposition, and feature engineering — all tracked through structured CSV reports and publication-quality plots.

---

## Repository Structure

```
EDA_Project/
│
├── ppg_time_series_analysis.ipynb   # Main analysis notebook (entry point)
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── data/                            # Raw input data (place raw CSVs here)
│
└── artifacts/
    ├── processed_data/              # Cleaned & feature-engineered CSVs
    │   ├── cleaned_data.csv               (~507 KB) — cleaned 6-column dataset
    │   ├── feature_engineered_data.csv    (~4.4 MB) — 45-column feature set
    │   ├── decomposition_components_ir.csv
    │   ├── decomposition_components_ir_corrected.csv
    │   ├── decomposition_components_red.csv
    │   └── decomposition_components_red_corrected.csv
    │
    ├── reports/                     # EDA summary CSVs
    │   ├── dataset_overview.csv
    │   ├── summary_statistics.csv
    │   ├── missing_value_report.csv
    │   ├── outlier_report.csv
    │   ├── stationarity_report.csv
    │   ├── time_continuity_report.csv
    │   ├── time_series_decomposition_report.csv
    │   └── feature_engineering_columns.csv
    │
    └── plots/                       # All saved visualizations (24 PNGs)
        ├── ppg_signal_overview_dashboard.png
        ├── distribution_dashboard.png
        ├── feature_dashboard.png
        ├── rolling_statistics_dashboard.png
        ├── time_series_{red,ir,red_corrected,ir_corrected}.png
        ├── time_series_decomposition_{red,ir,...}.png
        ├── decomposition_{red,ir,...}.png
        ├── acf_{red,ir,red_corrected,ir_corrected}.png
        └── pacf_{red,ir,red_corrected,ir_corrected}.png
```

---

## Dataset Description

### Columns in `cleaned_data.csv`

| Column | Type | Description |
|--------|------|-------------|
| `seq` | int64 | Sequential record index |
| `timestamp_ms` | int64 | Epoch timestamp in milliseconds |
| `red` | int64 | Raw Red PPG amplitude |
| `ir` | int64 | Raw IR PPG amplitude |
| `red_corrected` | float64 | AC-component of Red channel (DC removed) |
| `ir_corrected` | float64 | AC-component of IR channel (DC removed) |

### Signal Statistics

| Column | Mean | Std Dev | Min | Max | Median |
|--------|------|---------|-----|-----|--------|
| `red` | 40,766.8 | 253.1 | 40,080 | 41,281 | 40,814 |
| `ir` | 100,317.9 | 535.4 | 98,942 | 101,127 | 100,425 |
| `red_corrected` | 7.4 | 88.5 | −232.5 | 441.6 | −13.1 |
| `ir_corrected` | −22.1 | 186.5 | −681.5 | 979.9 | −26.1 |

> The corrected channels are centred near zero (DC removed), revealing the pulsatile AC component essential for pulse-wave morphology analysis.

### Sampling & Timing

| Metric | Value |
|--------|-------|
| Expected interval | 20 ms |
| Approximate sampling rate | **50 Hz** |
| Duplicate timestamps | 54 |
| Missing gap count (>30 ms) | 543 |
| Minimum interval | 0 ms |
| Maximum interval | 43 ms |

> Gaps and duplicates are present — downstream time-series modelling should account for **irregular sampling**.

---

## Analysis Pipeline

The notebook `ppg_time_series_analysis.ipynb` executes the following sequential stages:

### 1. Data Loading
- Reads `cleaned_data.csv` and `feature_engineered_data.csv` from `artifacts/processed_data/`.
- Confirms row/column counts and previews the first records.

### 2. Dataset Overview
- Enumerates all column names, data types, and missing-value counts.
- Saves `artifacts/reports/dataset_overview.csv`.

### 3. Missing Value Analysis
- Computes per-column missing count and percentage.
- Documents the fill strategy: **Linear Interpolation + Median** fallback.
- Saves `artifacts/reports/missing_value_report.csv`.
- Result: Only `time_diff_ms` has 1 missing value (0.013%), all signal columns are complete.

### 4. Summary Statistics
- Computes mean, std, mode, min, max, and median for all four signal columns (`red`, `ir`, `red_corrected`, `ir_corrected`).
- Saves `artifacts/reports/summary_statistics.csv`.

### 5. Time Continuity Assessment
- Derives inter-sample intervals from `timestamp_ms`.
- Detects duplicate timestamps, missing gaps (interval > 1.5× expected), and extreme intervals.
- Saves `artifacts/reports/time_continuity_report.csv`.

### 6. Outlier Detection (IQR Method)
- Applies the **1.5 × IQR** rule to all four signal columns.
- Reports Q1, Q3, IQR, bounds, outlier count, and outlier percentage per column.
- Saves `artifacts/reports/outlier_report.csv`.

| Column | Outliers | Percentage |
|--------|----------|------------|
| `red` | 276 | 3.72 % |
| `ir` | 993 | 13.38 % |
| `red_corrected` | 49 | 0.66 % |
| `ir_corrected` | 664 | 8.95 % |

### 7. Stationarity Testing (ADF)
- Runs the **Augmented Dickey–Fuller (ADF)** test on each signal column.
- Saves `artifacts/reports/stationarity_report.csv`.

| Column | ADF Statistic | p-value | Stationary? |
|--------|--------------|---------|-------------|
| `red` | −0.983 | 0.760 | ❌ No |
| `ir` | −1.591 | 0.488 | ❌ No |
| `red_corrected` | −2.545 | 0.105 | ❌ No |
| `ir_corrected` | −3.629 | **0.005** | ✅ Yes |

### 8. Time-Series Decomposition (STL / Additive)
- Decomposes each signal into **Trend + Seasonality + Residual** components using an additive model with period = 50 (corresponding to ~1 Hz cardiac cycle at 50 Hz).
- Saves four decomposition CSVs and eight decomposition plot PNGs (raw + corrected for each channel).
- Saves `artifacts/reports/time_series_decomposition_report.csv`.

### 9. Signal Plots
- Generates individual time-series plots for all four channels with timestamps on the x-axis.
- Produces ACF and PACF plots for autocorrelation structure analysis.
- Saves all plots to `artifacts/plots/`.

---

## Feature Engineering

The `feature_engineered_data.csv` expands the cleaned 6-column dataset into **45 features** for downstream machine learning or signal processing tasks.

### Feature Categories

| Category | Features |
|----------|---------|
| **Raw signals** | `seq`, `timestamp_ms`, `red`, `ir`, `red_corrected`, `ir_corrected` |
| **Timing** | `time_diff_ms` |
| **Normalized signals** | `red_norm`, `ir_norm`, `red_corrected_norm`, `ir_corrected_norm` |
| **DC / AC decomposition** | `red_dc`, `ir_dc`, `red_ac`, `ir_ac` |
| **Perfusion ratios** | `red_ac_dc_ratio`, `ir_ac_dc_ratio`, `red_ir_ratio`, `corrected_red_ir_ratio`, `ratio_of_ratios` |
| **Rolling statistics (Red corrected)** | `roll_mean`, `roll_std`, `roll_min`, `roll_max`, `roll_range`, `roll_median`, `roll_rms` |
| **Rolling statistics (IR corrected)** | `roll_mean`, `roll_std`, `roll_min`, `roll_max`, `roll_range`, `roll_median`, `roll_rms` |
| **Differencing** | `red_diff_1`, `ir_diff_1`, `red_diff_2`, `ir_diff_2` |
| **Absolute difference** | `red_abs_diff`, `ir_abs_diff` |
| **Outlier flags** | `red_outlier_flag`, `ir_outlier_flag`, `red_corrected_outlier_flag`, `ir_corrected_outlier_flag` |
| **Quality score** | `signal_quality_score` |

> The `ratio_of_ratios` feature is related to the **R-value** used in pulse oximetry SpO₂ estimation:  
> `R = (AC_red / DC_red) / (AC_ir / DC_ir)`

---

## Key Findings

1. **Sampling Rate**: The data was collected at approximately **50 Hz** (20 ms intervals).
2. **Timing Irregularities**: **54 duplicate timestamps** and **543 missing gaps** (intervals > 30 ms) were detected. Interpolation and resampling are advisable before frequency-domain analysis.
3. **Signal Amplitude**: Raw `red` and `ir` channels carry large DC offsets (~40,766 and ~100,318 ADU respectively). The corrected channels remove this baseline, centering signals near zero for morphology analysis.
4. **Outliers**: The raw `ir` channel shows the highest outlier rate at **13.38%**, while the corrected channels are much cleaner (< 1% for `red_corrected`).
5. **Stationarity**: Only the `ir_corrected` channel is stationary (ADF p = 0.005). Raw channels are non-stationary and require differencing or detrending before ARIMA-style modelling.
6. **Decomposition**: An additive model with period = 50 captures the ~1 Hz pulsatile cardiac component as the seasonal element, with a slowly varying trend representing physiological drift.

---

## Generated Artifacts

### Plots (`artifacts/plots/`)

| Plot File | Description |
|-----------|-------------|
| `ppg_signal_overview_dashboard.png` | Multi-panel overview of all four channels |
| `distribution_dashboard.png` | Amplitude distribution histograms |
| `feature_dashboard.png` | Key engineered features visualized |
| `rolling_statistics_dashboard.png` | Rolling mean, std, RMS for corrected channels |
| `time_series_{channel}.png` | Individual time-series for each channel (4 files) |
| `time_series_decomposition_{channel}.png` | Trend + seasonal + residual per channel (4 files) |
| `decomposition_{channel}.png` | Alternative decomposition view (4 files) |
| `acf_{channel}.png` | Autocorrelation Function plots (4 files) |
| `pacf_{channel}.png` | Partial Autocorrelation Function plots (4 files) |

### Reports (`artifacts/reports/`)

| Report CSV | Description |
|------------|-------------|
| `dataset_overview.csv` | Column names, dtypes, missing counts |
| `summary_statistics.csv` | Mean, std, mode, min, max, median per signal |
| `missing_value_report.csv` | Missing value audit with fill strategies |
| `outlier_report.csv` | IQR-based outlier bounds and counts |
| `stationarity_report.csv` | ADF test results per channel |
| `time_continuity_report.csv` | Sampling rate, gaps, and duplicates |
| `time_series_decomposition_report.csv` | Decomposition model and period per channel |
| `feature_engineering_columns.csv` | Full list of 45 engineered feature names |

---

## Requirements & Setup

### Python Version
Python **3.11** (as used in the notebook kernel)

### Dependencies

```txt
pandas
numpy
matplotlib
seaborn
statsmodels
scipy
jupyter
```

Install all dependencies with:

```bash
pip install -r requirements.txt
```

---

## How to Run

1. **Clone / download** this repository.
2. **Place raw data** in the `data/` directory (or ensure `artifacts/processed_data/cleaned_data.csv` already exists).
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Launch Jupyter**:
   ```bash
   jupyter notebook ppg_time_series_analysis.ipynb
   ```
5. **Run all cells** (`Kernel → Restart & Run All`).

All reports will be saved to `artifacts/reports/` and all plots to `artifacts/plots/` automatically.

---

## Notes

- The **`src/`** directory is reserved for modular Python scripts (e.g., signal processing utilities, feature extraction functions) to be refactored from the notebook in future iterations.
- The **`data/`** directory is currently empty; raw PPG data files should be placed here before running the full pipeline end-to-end.
- For irregular time-series modelling (ARIMA, Prophet, etc.), it is recommended to **resample** the data to a uniform 20 ms grid after handling duplicates.

---

*Generated as part of a PPG biomedical signal EDA project — June 2026.*
