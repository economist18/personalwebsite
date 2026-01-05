# Synthetic Control Analysis of Canada's ATC Privatization

## Overview

This repository contains a complete synthetic control analysis examining the impact of Canada's air traffic control (ATC) privatization in November 1996 on aviation sector performance.

**Research Question:** What was the causal effect of Canada's ATC privatization (Nav Canada creation) on aviation sector outcomes?

**Method:** Synthetic Control Method (Abadie & Gardeazabal, 2003; Abadie, Diamond & Hainmueller, 2010)

**Author:** Analysis conducted using real World Bank data

**Date:** January 2026

---

## Executive Summary

### Key Findings (Indexed Analysis, 1990=100)

**Air Passengers Carried (1996-1999):**
- **Effect:** +1.34%
- **Interpretation:** Canada's passenger growth slightly outpaced the synthetic control, suggesting modest positive impact

**Carrier Departures (1996-1999):**
- **Effect:** -10.96%
- **Interpretation:** Canada's flight volume growth lagged behind the synthetic control

### Important Caveats

1. **Data Limitations:** Analysis uses airline activity data (passengers, flights) rather than direct ATC performance metrics (safety incidents, delays, operational efficiency)

2. **Limited Post-Treatment Period:** Only 4 years of post-treatment data (1996-1999) due to data methodology changes after 2000

3. **Confounding Factors:** Many other factors affect aviation growth beyond ATC privatization (economic conditions, airline industry changes, etc.)

4. **Measurement:** World Bank data measures airline activity, not ATC system performance directly

---

## Background: Canada's ATC Privatization

### Timeline

- **November 1, 1996:** Canadian federal government transferred ATC operations to Nav Canada
- **Structure:** Private, non-profit corporation
- **Purchase Price:** CAD $1.5 billion
- **Employees Transferred:** 6,400 from Transport Canada to Nav Canada
- **Funding Model:** User-fee based (airlines and aircraft operators pay directly)

### Motivation

- Aging infrastructure requiring modernization
- Government budget constraints
- Desire for operational efficiency and technological advancement

---

## Methodology

### Synthetic Control Method

The synthetic control method creates a "synthetic Canada" - a weighted combination of control countries that closely matches Canada's pre-treatment characteristics. This synthetic version represents what would have happened to Canada without privatization.

**Treatment Unit:** Canada
**Treatment Date:** November 1, 1996
**Control Pool:** 12 OECD countries (USA, UK, France, Germany, Australia, New Zealand, Japan, Netherlands, Sweden, Switzerland, Spain, Italy)

**Pre-treatment Period:** 1985-1995 (11 years)
**Post-treatment Period:** 1996-1999 (4 years)

### Data Source

**World Bank World Development Indicators (WDI)**
- IS.AIR.PSGR: Air transport, passengers carried
- IS.AIR.DPRT: Air transport, registered carrier departures worldwide

Downloaded from: https://datacatalog.worldbank.org/

---

## Results

### 1. Air Passengers Carried (Indexed, 1990=100)

**Synthetic Control Weights:**
- United States: 52.7%
- Sweden: 47.3%

**Pre-treatment Fit:**
- RMSPE: 12.23 index points
- Mean Absolute Error: 10.56 index points

**Treatment Effects (1996-1999):**
| Year | Canada | Synthetic | Effect | Effect % |
|------|--------|-----------|--------|----------|
| 1996 | 111    | 106       | +5     | +4.9%    |
| 1997 | 116    | 114       | +2     | +2.1%    |
| 1998 | 120    | 116       | +4     | +3.2%    |
| 1999 | 119    | 126       | -6     | -4.9%    |

**Average Effect:** +1.30 index points (+1.34%)

**Interpretation:** Canada's passenger growth slightly exceeded the synthetic control in the immediate post-privatization period, though the effect diminished by 1999.

### 2. Carrier Departures (Indexed, 1990=100)

**Synthetic Control Weights:**
- Sweden: 99.9%

**Pre-treatment Fit:**
- RMSPE: 15.74 index points
- Mean Absolute Error: 13.43 index points

**Treatment Effects (1996-1999):**
| Year | Canada | Synthetic | Effect | Effect %  |
|------|--------|-----------|--------|-----------|
| 1996 | 88     | 88        | -0     | -0.1%     |
| 1997 | 90     | 100       | -10    | -10.1%    |
| 1998 | 92     | 107       | -16    | -14.7%    |
| 1999 | 92     | 114       | -21    | -18.9%    |

**Average Effect:** -11.87 index points (-10.96%)

**Interpretation:** Canada's flight volume growth was substantially lower than the synthetic control, suggesting potential consolidation or efficiency gains (fewer flights carrying similar passenger numbers).

---

## Files in This Repository

### Analysis Scripts

1. **`prepare_real_data.py`**
   - Extracts and processes World Bank data
   - Creates panel dataset for 13 countries, 1985-2005
   - Generates aviation_data_real.csv

2. **`synthetic_control_real_data.py`**
   - Implements synthetic control method
   - Analyzes absolute values
   - Creates visualizations and effect estimates

3. **`synthetic_control_indexed.py`**
   - Preferred analysis using indexed data (1990=100)
   - Controls for scale differences between countries
   - Better pre-treatment fit

4. **`synthetic_control_analysis.py`**
   - Original template with simulated data (not used in final analysis)

### Data Files

- **`aviation_data_real.csv`** (17 KB)
  - Processed panel dataset
  - 13 countries × 21 years = 273 observations
  - Variables: unit, country, year, passengers_carried, carrier_departures, freight_ton_km

### Results Files

#### Visualizations (PNG)
- `passengers_carried_indexed_plot.png` - Individual plot for passengers
- `carrier_departures_indexed_plot.png` - Individual plot for departures
- `all_outcomes_indexed_summary.png` - **Combined summary plot** (recommended)
- `*_real_plot.png` - Absolute value plots (less useful due to scale issues)

#### Treatment Effects (CSV)
- `passengers_carried_indexed_effects.csv` - Year-by-year effects for passengers
- `carrier_departures_indexed_effects.csv` - Year-by-year effects for departures
- `*_real_effects.csv` - Absolute value effects

---

## How to Reproduce the Analysis

### Prerequisites
```bash
pip install pandas numpy matplotlib scipy
```

### Step 1: Prepare Data
```bash
python prepare_real_data.py
```
This downloads and processes World Bank data into `aviation_data_real.csv`

### Step 2: Run Analysis
```bash
python synthetic_control_indexed.py
```
This generates all visualizations and results files.

### Step 3: Review Results
Open the generated PNG files to view the analysis:
- **`all_outcomes_indexed_summary.png`** - Main results figure
- Individual CSV files contain numerical results

---

## Limitations and Recommendations

### Current Limitations

1. **Outcome Variables**
   - Using airline activity (passengers, flights) as proxies for ATC performance
   - Not direct ATC metrics like safety incidents, delays, or cost efficiency

2. **Short Post-Treatment Window**
   - Only 4 years of post-treatment data (1996-1999)
   - Data methodology change after 2000 prevents longer analysis

3. **Missing Covariates**
   - No controls for GDP, fuel prices, airline industry regulation, etc.
   - Synthetic control relies solely on pre-treatment outcome trends

4. **Pre-Treatment Fit**
   - RMSPE ~12-16 index points indicates decent but not perfect pre-treatment match
   - Some remaining differences between Canada and synthetic control

### Recommendations for Publication

**For a publishable paper, you should:**

1. **Obtain ATC-Specific Data**
   - **Safety:** ICAO ADREP database (requires member state access)
   - **Efficiency:** EUROCONTROL performance data, FAA operational metrics
   - **Costs:** Nav Canada annual reports (1997+), compare to FAA budgets
   - **Delays:** Airport-specific delay statistics

2. **Extend the Analysis**
   - **Longer post-treatment period:** Ideally 10-15 years (through 2010+)
   - **Placebo tests:** Assign fake treatment dates to validate method
   - **Robustness checks:** Try different control pools, different base years

3. **Add Control Variables**
   - GDP growth rates
   - Aviation fuel prices
   - Airline industry deregulation indicators
   - Airport infrastructure investments

4. **Qualitative Evidence**
   - Case studies of Nav Canada innovations
   - Stakeholder interviews (airlines, pilots, controllers)
   - International comparisons (New Zealand, UK also privatized)

5. **Mechanism Analysis**
   - How did privatization affect outcomes?
   - Technology adoption patterns
   - Organizational changes
   - Investment in infrastructure

---

## Data Sources for Future Research

### ATC Performance Data

1. **ICAO (International Civil Aviation Organization)**
   - **ADREP:** Accident/Incident Data Reporting system
   - **Safety Reports:** Annual state of global aviation safety
   - **Access:** Requires ICAO member state credentials
   - **Contact:** ADREP@icao.int

2. **EUROCONTROL (European countries)**
   - **ANS Performance Portal:** https://ansperformance.eu/
   - **Metrics:** Delays, safety, cost-efficiency, environment
   - **Coverage:** 41 European states with monthly updates
   - **Access:** Public data portal with customizable reports

3. **FAA (United States)**
   - **ASPM:** Aviation System Performance Metrics
   - **OPSNET:** Official FAA operations and delay data
   - **Access:** https://www.faa.gov/data_research/
   - **Historical:** Statistical Handbook (1960-2003) via Hathi Trust

4. **Nav Canada**
   - **Annual Reports:** 1997-present at navcanada.ca
   - **Metrics:** Safety incidents, operational efficiency, financial performance
   - **Access:** Public annual reports (PDF)

5. **Aviation Safety Network (ASN)**
   - **Database:** https://aviation-safety.net/
   - **Coverage:** 11,000+ accident descriptions since 1919
   - **Access:** Public, searchable by country and date
   - **Note:** No bulk download; manual data collection needed

6. **World Bank**
   - **Global Aviation Dashboard:** Recent connectivity metrics
   - **WDI:** Historical passenger and flight data (used in this analysis)
   - **Access:** Public, downloadable CSV files

### Academic Literature

**Key Papers on Synthetic Control:**
- Abadie & Gardeazabal (2003): "The Economic Costs of Conflict"
- Abadie, Diamond & Hainmueller (2010): "Synthetic Control Methods for Comparative Case Studies"
- Abadie, Diamond & Hainmueller (2015): "Comparative Politics and the Synthetic Control Method"

**ATC Privatization Studies:**
- Poole & Edwards (various): Reason Foundation studies on ATC privatization
- GAO (2005): "Preliminary Observations on Commercialized Air Navigation Service Providers"
- Research on UK NATS, German DFS, Australian Airservices privatizations

---

## Citation

If you use this analysis in your research, please cite:

```
Synthetic Control Analysis of Canada's ATC Privatization (2026)
Data Source: World Bank World Development Indicators
Method: Abadie & Gardeazabal (2003), Abadie et al. (2010)
GitHub: [Repository URL]
```

---

## Contact & Support

For questions about this analysis:
- Review the code comments in the Python scripts
- Check the generated CSV files for detailed numerical results
- Consult the methodology papers cited above

---

## Acknowledgments

**Data Sources:**
- [NAV CANADA Aviation History](https://www.navcanada.ca/en/news/blog/aviation-history-how-privatization-shaped--nav-canadas-future.aspx)
- [Canada's experience with ATC privatization | Canadian Bar Association](https://www.cba.org/Sections/Air-and-Space-Law/Articles/ATC-privatization)
- [Nav Canada - Wikipedia](https://en.wikipedia.org/wiki/Nav_Canada)
- [World Bank World Development Indicators](https://data.worldbank.org/)
- [Our World in Data - Aviation Safety](https://ourworldindata.org/)
- [ICAO Aviation Data](https://www.icao.int/aviation-data)
- [EUROCONTROL Performance Review](https://www.eurocontrol.int/air-navigation-services-performance-review)

**Methodology:**
- Abadie, A., & Gardeazabal, J. (2003). "The Economic Costs of Conflict: A Case Study of the Basque Country." *American Economic Review*, 93(1), 113-132.
- Abadie, A., Diamond, A., & Hainmueller, J. (2010). "Synthetic Control Methods for Comparative Case Studies: Estimating the Effect of California's Tobacco Control Program." *Journal of the American Statistical Association*, 105(490), 493-505.

---

**Last Updated:** January 5, 2026
