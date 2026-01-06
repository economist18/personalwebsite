"""
Compile Loss of Separation Data for Canada ATC Privatization Analysis

Data Sources:
1. Nav Canada annual reports (2021-2024)
2. GAO Report 2005 (historical Nav Canada data)
3. Transportation Safety Board Canada
4. Published research and comparisons

Note: Complete time-series data across multiple countries is NOT available.
This analysis documents what data exists and its limitations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Compile available Nav Canada loss of separation data
# Rate = IFR-to-IFR losses of separation per 100,000 movements

nav_canada_data = {
    'fiscal_year': [
        '1999/2000',
        '2003/2004',
        '2020/2021',
        '2021/2022',
        '2022/2023',
        '2023/2024'
    ],
    'year': [2000, 2004, 2021, 2022, 2023, 2024],  # Approximate calendar year
    'los_rate_per_100k': [
        0.96,  # Source: GAO 2005 report
        0.79,  # Source: GAO 2005 report
        0.17,  # Source: Nav Canada Annual Report 2021
        0.56,  # Source: Nav Canada Annual Report 2022
        0.53,  # Source: Nav Canada Annual Report 2023
        0.40   # Source: Nav Canada Annual Report 2024
    ],
    'source': [
        'GAO Report 2005',
        'GAO Report 2005',
        'Nav Canada AR 2021',
        'Nav Canada AR 2022',
        'Nav Canada AR 2023',
        'Nav Canada AR 2024'
    ],
    'benchmark': [1.0] * 6  # Nav Canada's internal benchmark
}

df_canada = pd.DataFrame(nav_canada_data)

# Add privatization indicator
privatization_year = 1996
df_canada['post_privatization'] = df_canada['year'] > privatization_year
df_canada['years_since_privatization'] = df_canada['year'] - privatization_year

# Comparative data (limited)
comparative_data = {
    'country': ['Canada', 'USA'],
    'ansp': ['Nav Canada', 'FAA'],
    'period': ['Recent (2023)', 'Recent'],
    'los_rate_per_100k': [0.53, 3.3],
    'ratio_to_canada': [1.0, 6.2],
    'source': [
        'Nav Canada Annual Report 2023',
        'Comparative analysis (various sources)'
    ]
}

df_comparison = pd.DataFrame(comparative_data)

# Print data summary
print("="*70)
print("LOSS OF SEPARATION DATA COMPILATION")
print("Canada ATC Privatization Analysis")
print("="*70)

print("\n" + "="*70)
print("NAV CANADA HISTORICAL DATA")
print("="*70)
print(df_canada.to_string(index=False))

print("\n" + "="*70)
print("INTERNATIONAL COMPARISON (Limited Data)")
print("="*70)
print(df_comparison.to_string(index=False))

# Calculate pre/post averages (limited data)
pre_2004 = df_canada[df_canada['year'] <= 2004]['los_rate_per_100k'].mean()
post_2020 = df_canada[df_canada['year'] >= 2020]['los_rate_per_100k'].mean()

print("\n" + "="*70)
print("SUMMARY STATISTICS")
print("="*70)
print(f"Average rate (1999-2004, early post-privatization): {pre_2004:.2f} per 100k")
print(f"Average rate (2020-2024, mature operation):         {post_2020:.2f} per 100k")
print(f"Improvement: {((pre_2004 - post_2020)/pre_2004*100):.1f}%")
print(f"\nNav Canada benchmark: 1.0 per 100,000 movements")
print(f"All observed rates are below benchmark")

# Save data
df_canada.to_csv('nav_canada_loss_of_separation.csv', index=False)
df_comparison.to_csv('international_comparison.csv', index=False)

print("\n" + "="*70)
print("DATA LIMITATIONS")
print("="*70)
print("""
CRITICAL LIMITATIONS:

1. **Missing Years**: Large gap between 2004 and 2021 (17 years)
   - Cannot observe immediate post-privatization trajectory
   - Cannot observe long-term trend

2. **No Pre-Privatization Data**: No data from Transport Canada era (pre-1996)
   - Cannot compare before/after privatization directly
   - Must rely on post-privatization improvements

3. **Limited International Data**:
   - Only USA comparison available (different methodology)
   - No comparable time-series from other countries
   - Different countries use different definitions and denominators

4. **Methodology Differences**:
   - Nav Canada: IFR-to-IFR losses per 100,000 movements
   - FAA: "Operational errors" or "Loss of Standard Separation"
   - Not directly comparable without adjustment

5. **Cannot Perform Synthetic Control**:
   - Requires pre-treatment data (not available)
   - Requires control countries with comparable data (not available)
   - Requires consistent time series (large gap in data)

WHAT WE CAN CONCLUDE:

✓ Nav Canada's loss of separation rate improved from 0.96 (1999/2000) to
  0.79 (2003/2004) in early years

✓ Current rates (0.17-0.56 per 100k, 2020-2024) are substantially better
  than early post-privatization period

✓ Nav Canada's rate (0.53) is approximately 6x better than FAA's (3.3),
  though methodologies may differ

✓ All observed rates are well below Nav Canada's internal benchmark of 1.0

WHAT WE CANNOT CONCLUDE:

✗ Whether privatization caused the improvement (no pre-1996 baseline)

✗ Exact trajectory from 1996-2020 (missing data)

✗ Causal effect using synthetic control (insufficient data)

✗ Precise international comparisons (different methodologies)
""")

print("="*70)
print("FILES SAVED")
print("="*70)
print("  - nav_canada_loss_of_separation.csv")
print("  - international_comparison.csv")
print("="*70 + "\n")
