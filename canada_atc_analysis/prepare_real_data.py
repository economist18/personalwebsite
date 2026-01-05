"""
Prepare real-world aviation data for synthetic control analysis of Canada's ATC privatization
"""

import pandas as pd
import numpy as np

# Load World Bank data
print("Loading World Bank WDI data...")
wdi_data = pd.read_csv('WDICSV.csv', low_memory=False)

# Define countries for analysis
# Canada + control donor pool
countries = {
    'CAN': 'Canada',
    'USA': 'United States',
    'GBR': 'United Kingdom',
    'FRA': 'France',
    'DEU': 'Germany',
    'AUS': 'Australia',
    'NZL': 'New Zealand',
    'JPN': 'Japan',
    'NLD': 'Netherlands',
    'SWE': 'Sweden',
    'CHE': 'Switzerland',
    'ESP': 'Spain',
    'ITA': 'Italy'
}

# Extract aviation indicators
aviation_indicators = {
    'IS.AIR.PSGR': 'passengers_carried',
    'IS.AIR.DPRT': 'carrier_departures',
    'IS.AIR.GOOD.MT.K1': 'freight_ton_km'
}

# Years of interest: 1985-2005 (treatment in 1996)
years = [str(y) for y in range(1985, 2006)]

# Extract data for each indicator
all_data = []

for indicator_code, indicator_name in aviation_indicators.items():
    # Filter for this indicator and selected countries
    subset = wdi_data[
        (wdi_data['Indicator Code'] == indicator_code) &
        (wdi_data['Country Code'].isin(countries.keys()))
    ].copy()

    if len(subset) == 0:
        print(f"Warning: No data found for {indicator_name}")
        continue

    # Melt the data to long format
    id_cols = ['Country Name', 'Country Code', 'Indicator Name', 'Indicator Code']
    value_cols = [y for y in years if y in subset.columns]

    melted = subset.melt(
        id_vars=id_cols,
        value_vars=value_cols,
        var_name='year',
        value_name=indicator_name
    )

    melted['year'] = melted['year'].astype(int)
    all_data.append(melted)

# Merge all indicators
print("Merging indicators...")
merged_data = all_data[0]
for df in all_data[1:]:
    merged_data = merged_data.merge(
        df[['Country Code', 'year', df.columns[-1]]],
        on=['Country Code', 'year'],
        how='outer'
    )

# Rename and clean up
merged_data = merged_data.rename(columns={'Country Name': 'country'})
merged_data['unit'] = merged_data['country']

# Add country code mapping
merged_data['country_code'] = merged_data['Country Code']

# Keep only relevant columns
final_data = merged_data[['unit', 'country', 'country_code', 'year'] +
                          list(aviation_indicators.values())]

# Sort by country and year
final_data = final_data.sort_values(['unit', 'year']).reset_index(drop=True)

print(f"\nDataset shape: {final_data.shape}")
print(f"Countries: {final_data['unit'].nunique()}")
print(f"Years: {final_data['year'].min()}-{final_data['year'].max()}")
print(f"\nData availability by country:")
for country in sorted(final_data['unit'].unique()):
    country_data = final_data[final_data['unit'] == country]
    available_years = country_data[country_data['passengers_carried'].notna()]['year'].nunique()
    print(f"  {country}: {available_years} years with passenger data")

# Save processed data
final_data.to_csv('aviation_data_real.csv', index=False)
print("\nData saved to aviation_data_real.csv")

# Print summary statistics
print("\n=== SUMMARY STATISTICS ===")
print("\nCanada data (pre-privatization: 1985-1995):")
canada_pre = final_data[(final_data['unit'] == 'Canada') & (final_data['year'] < 1996)]
print(canada_pre[['year', 'passengers_carried', 'carrier_departures']].dropna())

print("\nCanada data (post-privatization: 1996-2005):")
canada_post = final_data[(final_data['unit'] == 'Canada') & (final_data['year'] >= 1996)]
print(canada_post[['year', 'passengers_carried', 'carrier_departures']].dropna())

# Calculate growth rates for Canada
print("\n=== CANADA GROWTH RATES ===")
canada_data = final_data[final_data['unit'] == 'Canada'].sort_values('year')

for col in ['passengers_carried', 'carrier_departures']:
    if col in canada_data.columns:
        pre_avg_growth = canada_data[canada_data['year'] < 1996][col].pct_change().mean()
        post_avg_growth = canada_data[canada_data['year'] >= 1996][col].pct_change().mean()
        print(f"\n{col}:")
        print(f"  Pre-privatization avg growth: {pre_avg_growth*100:.2f}%")
        print(f"  Post-privatization avg growth: {post_avg_growth*100:.2f}%")

print("\n" + "="*70)
