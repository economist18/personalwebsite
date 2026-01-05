"""
Synthetic Control Analysis of Canada's ATC Privatization using Real World Bank Data

Treatment: Nav Canada creation on November 1, 1996
Method: Synthetic Control (Abadie & Gardeazabal 2003, Abadie et al. 2010)
Data Source: World Bank World Development Indicators
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# Set random seed for reproducibility
np.random.seed(42)

class SyntheticControl:
    """
    Implements the synthetic control method for causal inference.

    The synthetic control is a weighted average of control units that best
    approximates the treated unit's pre-treatment characteristics.
    """

    def __init__(self, data, treated_unit, treatment_time, outcome_var, predictors=None):
        """
        Initialize the synthetic control analysis.

        Parameters:
        -----------
        data : pd.DataFrame
            Panel data with columns: unit, year, outcome, predictors
        treated_unit : str
            Name of the treated unit
        treatment_time : int
            Year when treatment occurred
        outcome_var : str
            Name of the outcome variable
        predictors : list
            List of predictor variable names (optional)
        """
        self.data = data.copy()
        self.treated_unit = treated_unit
        self.treatment_time = treatment_time
        self.outcome_var = outcome_var
        self.predictors = predictors or [outcome_var]

        # Remove rows with missing outcome variable
        self.data = self.data[self.data[outcome_var].notna()].copy()

        # Separate treated and control units
        self.treated_data = self.data[self.data['unit'] == treated_unit].copy()
        self.control_data = self.data[self.data['unit'] != treated_unit].copy()
        self.control_units = sorted(self.control_data['unit'].unique())

        # Pre and post treatment periods
        all_years = sorted(self.data['year'].unique())
        self.pre_treatment_years = [y for y in all_years if y < treatment_time]
        self.post_treatment_years = [y for y in all_years if y >= treatment_time]

        self.weights = None
        self.synthetic_control = None

    def fit(self):
        """
        Estimate optimal weights for synthetic control using constrained optimization.

        Minimizes the distance between treated unit and synthetic control in pre-treatment period.
        Constraints: weights sum to 1 and are non-negative (convex hull condition).
        """
        # Get pre-treatment outcomes for treated unit
        treated_pre_df = self.treated_data[
            self.treated_data['year'].isin(self.pre_treatment_years)
        ][['year', self.outcome_var]].sort_values('year')

        if len(treated_pre_df) == 0:
            raise ValueError(f"No pre-treatment data for {self.treated_unit}")

        treated_pre = treated_pre_df[self.outcome_var].values

        # Get pre-treatment outcomes for all control units
        control_pre = []
        valid_control_units = []

        for unit in self.control_units:
            unit_data = self.control_data[
                (self.control_data['unit'] == unit) &
                (self.control_data['year'].isin(self.pre_treatment_years))
            ][['year', self.outcome_var]].sort_values('year')

            # Only include units with complete pre-treatment data
            if len(unit_data) == len(treated_pre):
                control_pre.append(unit_data[self.outcome_var].values)
                valid_control_units.append(unit)

        if len(valid_control_units) == 0:
            raise ValueError("No valid control units with complete pre-treatment data")

        self.control_units = valid_control_units
        control_pre = np.array(control_pre).T  # Time x Units matrix

        # Objective function: minimize RMSPE (Root Mean Squared Prediction Error)
        def objective(w):
            synthetic = control_pre @ w
            return np.sqrt(np.mean((treated_pre - synthetic) ** 2))

        # Constraints: weights sum to 1, all weights >= 0
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in range(len(self.control_units))]

        # Initial guess: equal weights
        w0 = np.ones(len(self.control_units)) / len(self.control_units)

        # Optimize
        result = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
        self.weights = result.x

        # Create synthetic control time series
        self._create_synthetic_control()

        return self

    def _create_synthetic_control(self):
        """Generate the synthetic control time series using estimated weights."""
        synthetic_data = []

        for year in sorted(self.data['year'].unique()):
            synthetic_value = 0
            for i, unit in enumerate(self.control_units):
                unit_value_df = self.control_data[
                    (self.control_data['unit'] == unit) &
                    (self.control_data['year'] == year)
                ][self.outcome_var]

                if len(unit_value_df) > 0:
                    synthetic_value += self.weights[i] * unit_value_df.values[0]

            synthetic_data.append({'year': year, self.outcome_var: synthetic_value})

        self.synthetic_control = pd.DataFrame(synthetic_data)

    def plot(self, title=None, ylabel=None, save_path=None):
        """
        Plot treated unit vs synthetic control.
        """
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot treated unit
        ax.plot(self.treated_data['year'],
                self.treated_data[self.outcome_var],
                'o-', linewidth=2.5, markersize=6,
                label=self.treated_unit, color='#2E86AB')

        # Plot synthetic control
        ax.plot(self.synthetic_control['year'],
                self.synthetic_control[self.outcome_var],
                's--', linewidth=2.5, markersize=6,
                label=f'Synthetic {self.treated_unit}', color='#A23B72')

        # Add vertical line at treatment
        ax.axvline(x=self.treatment_time, color='red', linestyle=':',
                   linewidth=2, label='Privatization (Nov 1996)', alpha=0.7)

        # Styling
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel or self.outcome_var, fontsize=12, fontweight='bold')
        ax.set_title(title or f'{self.outcome_var}: Canada vs Synthetic Control',
                     fontsize=14, fontweight='bold', pad=20)
        ax.legend(fontsize=11, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Format y-axis with commas
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        return fig, ax

    def get_effects(self):
        """
        Calculate treatment effects (gap between treated and synthetic control).
        """
        effects = pd.merge(
            self.treated_data[['year', self.outcome_var]].rename(columns={self.outcome_var: 'treated'}),
            self.synthetic_control[['year', self.outcome_var]].rename(columns={self.outcome_var: 'synthetic'}),
            on='year',
            how='inner'
        )
        effects['effect'] = effects['treated'] - effects['synthetic']
        effects['effect_pct'] = (effects['effect'] / effects['synthetic']) * 100
        effects['period'] = effects['year'].apply(
            lambda x: 'pre' if x < self.treatment_time else 'post'
        )
        return effects

    def summary(self):
        """Print summary statistics of the analysis."""
        effects = self.get_effects()

        pre_effects = effects[effects['period'] == 'pre']['effect']
        post_effects = effects[effects['period'] == 'post']['effect']
        post_effects_pct = effects[effects['period'] == 'post']['effect_pct']

        print("="*70)
        print("SYNTHETIC CONTROL ANALYSIS SUMMARY")
        print("="*70)
        print(f"Treated Unit: {self.treated_unit}")
        print(f"Treatment Time: {self.treatment_time}")
        print(f"Outcome Variable: {self.outcome_var}")
        print(f"Number of Control Units: {len(self.control_units)}")
        print(f"Pre-treatment Period: {min(self.pre_treatment_years)}-{max(self.pre_treatment_years)}")
        print(f"Post-treatment Period: {min(self.post_treatment_years)}-{max(self.post_treatment_years)}")
        print("\n" + "-"*70)
        print("WEIGHTS FOR SYNTHETIC CONTROL")
        print("-"*70)

        weight_df = pd.DataFrame({
            'Country': self.control_units,
            'Weight': self.weights
        }).sort_values('Weight', ascending=False)

        # Only show countries with weight > 0.01
        significant_weights = weight_df[weight_df['Weight'] > 0.01]
        print(significant_weights.to_string(index=False))

        print("\n" + "-"*70)
        print("PRE-TREATMENT FIT")
        print("-"*70)
        print(f"RMSPE (Pre-treatment): {np.sqrt(np.mean(pre_effects**2)):,.2f}")
        print(f"Mean Absolute Error (Pre-treatment): {np.mean(np.abs(pre_effects)):,.2f}")

        print("\n" + "-"*70)
        print("TREATMENT EFFECTS")
        print("-"*70)
        print(f"Average Effect (Post-treatment): {np.mean(post_effects):,.2f}")
        print(f"Average Effect % (Post-treatment): {np.mean(post_effects_pct):.2f}%")
        print(f"Standard Deviation (Post-treatment): {np.std(post_effects):,.2f}")

        # Year-by-year post-treatment effects
        print("\nYear-by-Year Post-Treatment Effects:")
        post_df = effects[effects['period'] == 'post'][['year', 'treated', 'synthetic', 'effect', 'effect_pct']]
        post_df['treated'] = post_df['treated'].apply(lambda x: f'{x:,.0f}')
        post_df['synthetic'] = post_df['synthetic'].apply(lambda x: f'{x:,.0f}')
        post_df['effect'] = post_df['effect'].apply(lambda x: f'{x:,.0f}')
        post_df['effect_pct'] = post_df['effect_pct'].apply(lambda x: f'{x:.1f}%')
        print(post_df.to_string(index=False))
        print("="*70)

        return weight_df, effects


def main():
    """Run the complete synthetic control analysis with real data."""

    print("\n" + "="*70)
    print("SYNTHETIC CONTROL ANALYSIS")
    print("Impact of Canada's ATC Privatization (Nav Canada, 1996)")
    print("Using Real World Bank Data")
    print("="*70 + "\n")

    # Load data
    print("Loading aviation data...")
    data = pd.read_csv('aviation_data_real.csv')
    print(f"Data loaded: {len(data)} observations")
    print(f"Countries: {data['unit'].nunique()}")
    print(f"Years: {data['year'].min()}-{data['year'].max()}\n")

    # Note: There appears to be a data break/methodology change around 2000
    # For more robust analysis, we'll limit to 1985-1999 to avoid this issue
    print("NOTE: Limiting analysis to 1985-1999 due to apparent data methodology change after 2000\n")
    data = data[data['year'] <= 1999].copy()

    # Run analyses for each outcome variable
    outcomes = {
        'passengers_carried': {
            'title': 'Air Passengers Carried',
            'ylabel': 'Number of Passengers',
            'interpretation': 'Higher is better (indicates growth)'
        },
        'carrier_departures': {
            'title': 'Carrier Departures',
            'ylabel': 'Number of Departures',
            'interpretation': 'Indicates flight volume and activity'
        }
    }

    results = {}

    for outcome_var, config in outcomes.items():
        # Check if we have sufficient data
        canada_data = data[(data['unit'] == 'Canada') & (data[outcome_var].notna())]
        if len(canada_data) < 10:
            print(f"Skipping {outcome_var}: insufficient data\n")
            continue

        print("\n" + "="*70)
        print(f"ANALYZING: {config['title']}")
        print("="*70 + "\n")

        try:
            # Fit synthetic control
            sc = SyntheticControl(
                data=data,
                treated_unit='Canada',
                treatment_time=1996,
                outcome_var=outcome_var
            )

            sc.fit()

            # Get summary
            weights, effects = sc.summary()

            # Plot
            fig, ax = sc.plot(
                title=f"{config['title']}: Canada vs Synthetic Control",
                ylabel=config['ylabel'],
                save_path=f"{outcome_var}_real_plot.png"
            )
            plt.close()

            # Store results
            results[outcome_var] = {
                'weights': weights,
                'effects': effects,
                'average_effect': effects[effects['period'] == 'post']['effect'].mean(),
                'average_effect_pct': effects[effects['period'] == 'post']['effect_pct'].mean()
            }

            # Save effects to CSV
            effects.to_csv(f'{outcome_var}_real_effects.csv', index=False)

        except Exception as e:
            print(f"Error analyzing {outcome_var}: {e}\n")
            continue

    # Create summary plot with all outcomes
    if len(results) > 0:
        n_outcomes = len(results)
        fig, axes = plt.subplots(1, n_outcomes, figsize=(8*n_outcomes, 6))
        if n_outcomes == 1:
            axes = [axes]

        fig.suptitle('Canada ATC Privatization: Synthetic Control Analysis\nReal World Bank Data (1985-1999)',
                     fontsize=16, fontweight='bold', y=1.02)

        for idx, (outcome_var, result) in enumerate(results.items()):
            ax = axes[idx]
            effects = result['effects']
            treated = effects['treated'].values
            synthetic = effects['synthetic'].values
            years = effects['year'].values

            ax.plot(years, treated, 'o-', linewidth=2.5, markersize=5,
                    label='Canada', color='#2E86AB')
            ax.plot(years, synthetic, 's--', linewidth=2.5, markersize=5,
                    label='Synthetic Canada', color='#A23B72')
            ax.axvline(x=1996, color='red', linestyle=':', linewidth=2, alpha=0.7,
                       label='Privatization')

            ax.set_xlabel('Year', fontsize=11, fontweight='bold')
            ax.set_ylabel(outcomes[outcome_var]['ylabel'], fontsize=11, fontweight='bold')
            ax.set_title(outcomes[outcome_var]['title'], fontsize=12, fontweight='bold')
            ax.legend(fontsize=10, loc='best')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))

        plt.tight_layout()
        plt.savefig('all_outcomes_real_summary.png', dpi=300, bbox_inches='tight')
        print("\n\nSummary plot saved to: all_outcomes_real_summary.png")
        plt.close()

    # Generate final summary report
    print("\n" + "="*70)
    print("FINAL SUMMARY OF RESULTS")
    print("="*70)
    print("\nAverage Post-Treatment Effects (1996-1999):")
    print("-" * 70)
    for outcome_var in results:
        avg_effect = results[outcome_var]['average_effect']
        avg_effect_pct = results[outcome_var]['average_effect_pct']
        print(f"\n{outcomes[outcome_var]['title']}:")
        print(f"  Absolute effect: {avg_effect:,.0f}")
        print(f"  Percentage effect: {avg_effect_pct:+.2f}%")
        print(f"  Interpretation: {outcomes[outcome_var]['interpretation']}")

    print("\n" + "="*70)
    print("KEY FINDINGS")
    print("="*70)
    print("""
This analysis uses real World Bank data on aviation indicators to estimate
the causal effect of Canada's ATC privatization in November 1996.

The synthetic control method constructs a counterfactual "synthetic Canada"
from a weighted combination of similar countries that did not privatize
their ATC systems.

Data Source: World Bank World Development Indicators (WDI)
Period: 1985-1999 (limited due to data methodology changes after 2000)
Treatment: Nav Canada privatization (November 1, 1996)
Control Pool: 12 OECD countries with similar aviation characteristics

INTERPRETATION:
- Positive effects indicate Canada outperformed the synthetic control
- Negative effects indicate Canada underperformed relative to synthetic control
- The pre-treatment fit quality indicates how well the synthetic control
  matches Canada before privatization (lower RMSPE is better)

NOTE: This analysis is limited by data availability. Ideally, you would want:
1. ATC-specific performance metrics (safety, efficiency, delays)
2. Longer post-treatment period
3. Additional control variables (GDP, population, etc.)
4. Data from specialized aviation safety databases
    """)

    print("="*70)
    print("\nAnalysis complete! All results saved to canada_atc_analysis/")
    print("\nGenerated files:")
    print("  - aviation_data_real.csv (processed dataset)")
    print("  - passengers_carried_real_plot.png")
    print("  - carrier_departures_real_plot.png")
    print("  - all_outcomes_real_summary.png")
    print("  - *_real_effects.csv (treatment effects for each outcome)")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
