"""
Visualize and Analyze Available Loss of Separation Data

Creates visualizations and alternative analyses given data limitations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Load compiled data
df_canada = pd.read_csv('nav_canada_loss_of_separation.csv')
df_comparison = pd.read_csv('international_comparison.csv')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')

#===========================
# Figure 1: Nav Canada Trend Over Time
#===========================
fig, ax = plt.subplots(figsize=(14, 8))

# Plot data points
ax.plot(df_canada['year'], df_canada['los_rate_per_100k'],
        'o-', linewidth=3, markersize=12, color='#2E86AB', label='Observed Rate',
        markerfacecolor='#2E86AB', markeredgecolor='white', markeredgewidth=2)

# Add privatization line
ax.axvline(x=1996, color='red', linestyle='--', linewidth=2.5,
           label='Privatization (Nov 1996)', alpha=0.7)

# Add benchmark line
ax.axhline(y=1.0, color='gray', linestyle=':', linewidth=2,
           label='Nav Canada Benchmark (1.0)', alpha=0.6)

# Shade missing data region
ax.axvspan(2004, 2021, alpha=0.15, color='orange',
           label='Missing Data Period')

# Annotate key points
for idx, row in df_canada.iterrows():
    ax.annotate(f"{row['los_rate_per_100k']:.2f}",
                xy=(row['year'], row['los_rate_per_100k']),
                xytext=(0, 10), textcoords='offset points',
                ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

# Labels and title
ax.set_xlabel('Year', fontsize=14, fontweight='bold')
ax.set_ylabel('IFR-to-IFR Loss of Separation\n(per 100,000 movements)',
              fontsize=14, fontweight='bold')
ax.set_title('Nav Canada Loss of Separation Rate Over Time\n' +
             'Limited Historical Data with 17-Year Gap',
             fontsize=16, fontweight='bold', pad=20)

# Legend
ax.legend(fontsize=12, loc='upper right', framealpha=0.9)

# Grid and spines
ax.grid(True, alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Set y-axis to start at 0
ax.set_ylim(0, 1.2)

# Add note about data gap
ax.text(2012.5, 0.6, 'DATA GAP\n17 Years',
        ha='center', va='center', fontsize=14, fontweight='bold',
        color='orange', alpha=0.8, rotation=90)

plt.tight_layout()
plt.savefig('nav_canada_los_trend.png', dpi=300, bbox_inches='tight')
print("✓ Saved: nav_canada_los_trend.png")
plt.close()

#===========================
# Figure 2: International Comparison
#===========================
fig, ax = plt.subplots(figsize=(10, 7))

countries = df_comparison['ansp'].values
rates = df_comparison['los_rate_per_100k'].values
colors = ['#2E86AB', '#E63946']

bars = ax.barh(countries, rates, color=colors, edgecolor='black', linewidth=2)

# Add value labels
for i, (bar, rate) in enumerate(zip(bars, rates)):
    ax.text(rate + 0.15, bar.get_y() + bar.get_height()/2,
            f'{rate:.2f}',
            ha='left', va='center', fontsize=14, fontweight='bold')

# Labels
ax.set_xlabel('Loss of Separation Rate\n(per 100,000 operations/movements)',
              fontsize=13, fontweight='bold')
ax.set_title('International Comparison: Loss of Separation Rates\n' +
             '(Note: Different methodologies - not directly comparable)',
             fontsize=14, fontweight='bold', pad=20)

# Add ratio annotation
ratio = rates[1] / rates[0]
ax.text(2.0, 0.5, f'FAA rate is {ratio:.1f}x\nhigher than\nNav Canada',
        ha='center', va='center', fontsize=12,
        bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig('international_comparison.png', dpi=300, bbox_inches='tight')
print("✓ Saved: international_comparison.png")
plt.close()

#===========================
# Figure 3: Before-After Comparison (within post-privatization period)
#===========================
fig, ax = plt.subplots(figsize=(10, 7))

early_post = df_canada[df_canada['year'] <= 2004]
mature = df_canada[df_canada['year'] >= 2020]

early_avg = early_post['los_rate_per_100k'].mean()
mature_avg = mature['los_rate_per_100k'].mean()

periods = ['Early Post-Privatization\n(1999-2004)', 'Mature Operation\n(2020-2024)']
averages = [early_avg, mature_avg]
colors_bar = ['#F4A261', '#2A9D8F']

bars = ax.bar(periods, averages, color=colors_bar, edgecolor='black', linewidth=2, width=0.6)

# Add value labels
for bar, avg in zip(bars, averages):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 0.02,
            f'{avg:.2f}',
            ha='center', va='bottom', fontsize=16, fontweight='bold')

# Add improvement annotation
improvement = ((early_avg - mature_avg) / early_avg) * 100
ax.annotate('', xy=(0, early_avg), xytext=(1, mature_avg),
            arrowprops=dict(arrowstyle='<->', lw=2, color='red'))
ax.text(0.5, (early_avg + mature_avg)/2 + 0.05, f'{improvement:.1f}%\nimprovement',
        ha='center', va='bottom', fontsize=13, fontweight='bold', color='red',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='red', linewidth=2))

# Benchmark line
ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=2, label='Benchmark (1.0)', alpha=0.6)

ax.set_ylabel('Average Loss of Separation Rate\n(per 100,000 movements)',
              fontsize=13, fontweight='bold')
ax.set_title('Nav Canada Safety Improvement Over Time\n' +
             'Comparing Early vs. Mature Post-Privatization Periods',
             fontsize=14, fontweight='bold', pad=20)
ax.legend(fontsize=11)
ax.set_ylim(0, 1.1)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('before_after_comparison.png', dpi=300, bbox_inches='tight')
print("✓ Saved: before_after_comparison.png")
plt.close()

#===========================
# Figure 4: Combined Summary Figure
#===========================
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

# Subplot 1: Trend
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(df_canada['year'], df_canada['los_rate_per_100k'],
        'o-', linewidth=3, markersize=10, color='#2E86AB')
ax1.axvline(x=1996, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax1.axhline(y=1.0, color='gray', linestyle=':', linewidth=2, alpha=0.6)
ax1.axvspan(2004, 2021, alpha=0.15, color='orange')
ax1.set_xlabel('Year', fontsize=11, fontweight='bold')
ax1.set_ylabel('LOS Rate per 100k', fontsize=11, fontweight='bold')
ax1.set_title('A) Nav Canada Loss of Separation Trend', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(0, 1.2)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# Subplot 2: International comparison
ax2 = fig.add_subplot(gs[1, 0])
ax2.barh(df_comparison['ansp'], df_comparison['los_rate_per_100k'],
         color=['#2E86AB', '#E63946'], edgecolor='black', linewidth=1.5)
ax2.set_xlabel('LOS Rate per 100k', fontsize=11, fontweight='bold')
ax2.set_title('B) International Comparison', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='x')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

# Subplot 3: Early vs Mature
ax3 = fig.add_subplot(gs[1, 1])
ax3.bar(['Early\n(1999-2004)', 'Mature\n(2020-2024)'],
        [early_avg, mature_avg],
        color=['#F4A261', '#2A9D8F'], edgecolor='black', linewidth=1.5)
ax3.axhline(y=1.0, color='gray', linestyle='--', linewidth=2, alpha=0.6)
ax3.set_ylabel('Average LOS Rate per 100k', fontsize=11, fontweight='bold')
ax3.set_title('C) Post-Privatization Improvement', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_ylim(0, 1.1)
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)

fig.suptitle('Nav Canada Loss of Separation Analysis\nComprehensive Summary with Available Data',
             fontsize=16, fontweight='bold', y=0.98)

plt.savefig('summary_all_analyses.png', dpi=300, bbox_inches='tight')
print("✓ Saved: summary_all_analyses.png")
plt.close()

#===========================
# Print Summary Statistics
#===========================
print("\n" + "="*70)
print("ANALYSIS COMPLETE - SUMMARY")
print("="*70)
print(f"\nData Points Available: {len(df_canada)}")
print(f"Years Covered: {df_canada['year'].min()}-{df_canada['year'].max()}")
print(f"Years Since Privatization: {df_canada['years_since_privatization'].min()}-{df_canada['years_since_privatization'].max()}")

print(f"\nEarly Post-Privatization (1999-2004):")
print(f"  Average Rate: {early_avg:.2f} per 100,000 movements")
print(f"  Range: {early_post['los_rate_per_100k'].min():.2f} - {early_post['los_rate_per_100k'].max():.2f}")

print(f"\nMature Operation (2020-2024):")
print(f"  Average Rate: {mature_avg:.2f} per 100,000 movements")
print(f"  Range: {mature['los_rate_per_100k'].min():.2f} - {mature['los_rate_per_100k'].max():.2f}")

print(f"\nImprovement: {improvement:.1f}%")
print(f"Nav Canada vs FAA: {df_comparison.iloc[0]['los_rate_per_100k']:.2f} vs {df_comparison.iloc[1]['los_rate_per_100k']:.2f} (Nav Canada {ratio:.1f}x better)")

print("\n" + "="*70)
print("VISUALIZATIONS CREATED")
print("="*70)
print("  1. nav_canada_los_trend.png - Time series with data gap")
print("  2. international_comparison.png - Nav Canada vs FAA")
print("  3. before_after_comparison.png - Early vs mature periods")
print("  4. summary_all_analyses.png - Combined overview")
print("="*70)
