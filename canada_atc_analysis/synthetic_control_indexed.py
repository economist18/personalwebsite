"""
Synthetic Control Analysis using Indexed Data (1990=100)

This addresses the scale mismatch between countries by normalizing all series to an index.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# Import the SyntheticControl class from previous script
exec(open('synthetic_control_real_data.py').read().split('def main():')[0])

def create_indexed_data(data, outcome_var, base_year=1990):
    """
    Convert absolute values to index with base_year = 100.
    """
    indexed_data = []

    for country in data['unit'].unique():
        country_data = data[data['unit'] == country].copy()

        # Get base year value
        base_value = country_data[country_data['year'] == base_year][outcome_var].values
        if len(base_value) == 0 or pd.isna(base_value[0]) or base_value[0] == 0:
            continue

        base_value = base_value[0]

        # Create index
        country_data[f'{outcome_var}_index'] = (country_data[outcome_var] / base_value) * 100

        indexed_data.append(country_data)

    return pd.concat(indexed_data, ignore_index=True)


def main():
    """Run synthetic control with indexed data."""

    print("\n" + "="*70)
    print("SYNTHETIC CONTROL ANALYSIS WITH INDEXED DATA")
    print("Impact of Canada's ATC Privatization (Nav Canada, 1996)")
    print("Using Indexed World Bank Data (1990=100)")
    print("="*70 + "\n")

    # Load data
    print("Loading aviation data...")
    data = pd.read_csv('aviation_data_real.csv')
    print(f"Data loaded: {len(data)} observations\n")

    # Limit to 1985-1999
    data = data[data['year'] <= 1999].copy()

    # Define outcomes
    outcomes = {
        'passengers_carried': 'Air Passengers Carried',
        'carrier_departures': 'Carrier Departures'
    }

    results = {}

    for outcome_var, outcome_name in outcomes.items():
        print("\n" + "="*70)
        print(f"ANALYZING: {outcome_name} (Indexed, 1990=100)")
        print("="*70 + "\n")

        # Create indexed data
        indexed_data = create_indexed_data(data, outcome_var, base_year=1990)
        index_var = f'{outcome_var}_index'

        # Check data availability
        canada_indexed = indexed_data[(indexed_data['unit'] == 'Canada') &
                                       (indexed_data[index_var].notna())]
        if len(canada_indexed) < 10:
            print(f"Insufficient data for {outcome_name}\n")
            continue

        try:
            # Fit synthetic control on indexed data
            sc = SyntheticControl(
                data=indexed_data,
                treated_unit='Canada',
                treatment_time=1996,
                outcome_var=index_var
            )

            sc.fit()

            # Summary
            weights, effects = sc.summary()

            # Plot
            fig, ax = sc.plot(
                title=f"{outcome_name} Index (1990=100): Canada vs Synthetic Control",
                ylabel=f'{outcome_name} Index (1990=100)',
                save_path=f"{outcome_var}_indexed_plot.png"
            )
            plt.close()

            # Store results
            results[outcome_var] = {
                'weights': weights,
                'effects': effects,
                'average_effect': effects[effects['period'] == 'post']['effect'].mean(),
                'average_effect_pct': effects[effects['period'] == 'post']['effect_pct'].mean()
            }

            # Save effects
            effects.to_csv(f'{outcome_var}_indexed_effects.csv', index=False)

        except Exception as e:
            print(f"Error: {e}\n")
            continue

    # Create combined visualization
    if len(results) >= 2:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('Canada ATC Privatization: Synthetic Control Analysis (Indexed Data, 1990=100)\\nWorld Bank Data (1985-1999)',
                     fontsize=16, fontweight='bold', y=1.02)

        for idx, (outcome_var, outcome_name) in enumerate(outcomes.items()):
            if outcome_var not in results:
                continue

            ax = axes[idx]
            effects = results[outcome_var]['effects']

            ax.plot(effects['year'], effects['treated'], 'o-', linewidth=2.5,
                    markersize=5, label='Canada', color='#2E86AB')
            ax.plot(effects['year'], effects['synthetic'], 's--', linewidth=2.5,
                    markersize=5, label='Synthetic Canada', color='#A23B72')
            ax.axvline(x=1996, color='red', linestyle=':', linewidth=2,
                       alpha=0.7, label='Privatization')
            ax.axhline(y=100, color='gray', linestyle='--', linewidth=1,
                       alpha=0.5, label='Base (1990)')

            ax.set_xlabel('Year', fontsize=12, fontweight='bold')
            ax.set_ylabel('Index (1990=100)', fontsize=12, fontweight='bold')
            ax.set_title(outcome_name, fontsize=13, fontweight='bold')
            ax.legend(fontsize=10, loc='best', framealpha=0.9)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        plt.tight_layout()
        plt.savefig('all_outcomes_indexed_summary.png', dpi=300, bbox_inches='tight')
        print("\n\nCombined plot saved to: all_outcomes_indexed_summary.png")
        plt.close()

    # Final summary
    print("\n" + "="*70)
    print("FINAL RESULTS SUMMARY (Indexed Analysis)")
    print("="*70)

    for outcome_var, outcome_name in outcomes.items():
        if outcome_var in results:
            avg_effect = results[outcome_var]['average_effect']
            avg_effect_pct = results[outcome_var]['average_effect_pct']

            print(f"\n{outcome_name}:")
            print(f"  Average effect (index points): {avg_effect:+.2f}")
            print(f"  Average effect (%): {avg_effect_pct:+.2f}%")

            # Interpretation
            if avg_effect > 0:
                print(f"  → Canada grew FASTER than synthetic control post-privatization")
            else:
                print(f"  → Canada grew SLOWER than synthetic control post-privatization")

    print("\n" + "="*70)
    print("INTERPRETATION")
    print("="*70)
    print("""
Using indexed data (1990=100) controls for differences in absolute scale
between countries, allowing for better comparison of growth trajectories.

The synthetic control represents a counterfactual: what would have happened
to Canada's aviation sector if it had NOT privatized its ATC system.

POSITIVE effects = Canada outperformed the synthetic control
NEGATIVE effects = Canada underperformed the synthetic control

Note: This analysis uses World Bank data which primarily captures airline
activity (passengers and flights), not direct ATC performance metrics like
safety, delays, or operational efficiency.

For a complete analysis, you would ideally want:
- ATC-specific safety data (incidents, accidents per million operations)
- Operational efficiency data (delays, on-time performance)
- Cost data (operating costs per flight, cost efficiency)
- Technology adoption metrics
- Customer satisfaction scores

These specialized metrics are available from sources like:
- ICAO safety databases (restricted access)
- EUROCONTROL performance data (European countries)
- Individual ANSP annual reports
- Academic papers on ATC performance
    """)

    print("\n" + "="*70)
    print("FILES GENERATED")
    print("="*70)
    print("  - passengers_carried_indexed_plot.png")
    print("  - carrier_departures_indexed_plot.png")
    print("  - all_outcomes_indexed_summary.png")
    print("  - *_indexed_effects.csv")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
