# Airport Runway Database

A comprehensive database of worldwide airports and runways, built from open data sources.

## Database Contents

- **84,524 airports** worldwide
- **47,548 runways** with detailed specifications
- Runway lengths, widths, surfaces, and headings
- ICAO and IATA codes
- Geographic coordinates
- Airport types (large, medium, small, heliport, seaplane base, closed)

## Data Source

Data is sourced from [OurAirports](https://ourairports.com), an open data project licensed under CC0 (Public Domain).

## Quick Start

### 1. Build the Database

```bash
cd airport_runway_database
python3 fetch_ourairports.py
```

This downloads the latest airport/runway data and creates `airport_runways.db` (SQLite).

### 2. Query the Database

```bash
# Show statistics
python3 query_database.py --stats

# Search airports
python3 query_database.py --search "JFK"
python3 query_database.py --search "Heathrow"

# Get airport by ICAO code
python3 query_database.py --icao KJFK
python3 query_database.py --icao EGLL

# Get airport by IATA code
python3 query_database.py --iata LAX

# Show longest runways
python3 query_database.py --longest-runways 20

# Show airports with most runways
python3 query_database.py --most-runways 20

# Filter by country
python3 query_database.py --country US --search "international"
```

### 3. Export Data

```bash
# Export to CSV
python3 query_database.py --export-csv airports.csv

# Export to JSON
python3 query_database.py --export-json airports.json

# Export to GeoJSON (for mapping)
python3 query_database.py --export-geojson airports.geojson
```

## Satellite Imagery

To add satellite imagery for airports and runways, you need an API key from one of these providers:

- **Google Maps Static API**: https://developers.google.com/maps/documentation/maps-static/get-api-key
- **Mapbox Static Images**: https://docs.mapbox.com/help/getting-started/access-tokens/
- **Bing Maps**: https://www.microsoft.com/en-us/maps/create-a-bing-maps-key

```bash
# List airports that would get imagery
python3 fetch_imagery.py --list

# Fetch airport imagery (Google example)
python3 fetch_imagery.py --provider google --api-key YOUR_API_KEY

# Fetch with limit
python3 fetch_imagery.py --provider google --api-key YOUR_API_KEY --limit 100

# Fetch individual runway imagery (higher zoom)
python3 fetch_imagery.py --provider google --api-key YOUR_API_KEY --runways --limit 100

# Include small airports
python3 fetch_imagery.py --provider google --api-key YOUR_API_KEY --all-types
```

## Database Schema

### airports
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| ident | TEXT | ICAO code (e.g., KJFK) |
| iata_code | TEXT | IATA code (e.g., JFK) |
| name | TEXT | Airport name |
| latitude | REAL | Latitude in degrees |
| longitude | REAL | Longitude in degrees |
| elevation_ft | REAL | Elevation in feet |
| type | TEXT | large_airport, medium_airport, small_airport, heliport, seaplane_base, closed |
| iso_country | TEXT | ISO country code |
| municipality | TEXT | City/town name |

### runways
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| airport_id | INTEGER | Foreign key to airports |
| airport_ident | TEXT | Airport ICAO code |
| length_ft | REAL | Length in feet |
| length_m | REAL | Length in meters |
| width_ft | REAL | Width in feet |
| surface | TEXT | Surface type (ASP, CON, TURF, etc.) |
| lighted | INTEGER | 1 if lighted, 0 if not |
| closed | INTEGER | 1 if closed, 0 if open |
| le_ident | TEXT | Low-end designator (e.g., 09) |
| he_ident | TEXT | High-end designator (e.g., 27) |
| le_latitude | REAL | Latitude of low end |
| le_longitude | REAL | Longitude of low end |
| le_heading_deg | REAL | Magnetic heading of low end |
| he_latitude | REAL | Latitude of high end |
| he_longitude | REAL | Longitude of high end |
| he_heading_deg | REAL | Magnetic heading of high end |

### runway_imagery
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| airport_id | INTEGER | Foreign key to airports |
| runway_id | INTEGER | Foreign key to runways (optional) |
| image_path | TEXT | Local file path |
| capture_date | DATE | Date of imagery |
| imagery_source | TEXT | Provider name |
| zoom_level | INTEGER | Map zoom level |

## Sample Queries (SQLite)

```sql
-- Longest runways in the world (excluding seaplane bases)
SELECT r.length_ft, r.length_m, a.ident, a.name, a.iso_country, r.surface
FROM runways r
JOIN airports a ON r.airport_id = a.id
WHERE a.type NOT IN ('seaplane_base')
ORDER BY r.length_ft DESC
LIMIT 20;

-- Airports with most runways
SELECT a.ident, a.name, COUNT(r.id) as runway_count
FROM airports a
JOIN runways r ON a.id = r.airport_id
WHERE a.type IN ('large_airport', 'medium_airport')
GROUP BY a.id
ORDER BY runway_count DESC
LIMIT 20;

-- All runways at a specific airport
SELECT le_ident || '/' || he_ident as runway, length_ft, surface, lighted
FROM runways
WHERE airport_ident = 'KJFK'
ORDER BY length_ft DESC;

-- Airports by country with runway data
SELECT a.ident, a.name, COUNT(r.id) as runways, MAX(r.length_ft) as longest
FROM airports a
JOIN runways r ON a.id = r.airport_id
WHERE a.iso_country = 'US'
AND a.type = 'large_airport'
GROUP BY a.id
ORDER BY longest DESC;
```

## Historical Data

The OurAirports database contains **current** runway information only. For historical runway data (1985-present), you would need:

1. **Google Earth Engine** - Access historical Landsat imagery (1984-present) to analyze runway changes visually. Requires a Google Cloud account.

2. **FAA Historical Data** - The FAA maintains historical airport data for US airports at https://www.faa.gov/air_traffic/flight_info/aeronav/

3. **ICAO/National Aviation Authorities** - Historical records require formal data requests to respective aviation authorities.

4. **Internet Archive Wayback Machine** - Historical snapshots of airport information websites.

The `fetch_historical_imagery.py` script provides a framework for fetching historical satellite imagery via Google Earth Engine if you have access.

## Files

| File | Description |
|------|-------------|
| `fetch_ourairports.py` | Downloads OurAirports data and builds the database |
| `query_database.py` | Query tool with CLI interface |
| `fetch_imagery.py` | Downloads satellite imagery (requires API key) |
| `fetch_historical_imagery.py` | Historical imagery via Google Earth Engine |
| `airport_runways.db` | SQLite database (generated) |
| `ourairports_data/` | Cached CSV files from OurAirports |
| `runway_imagery/` | Downloaded imagery (if API key provided) |

## Requirements

- Python 3.7+
- No external dependencies required for basic functionality
- `requests` library for imagery fetching
- `earthengine-api` for historical imagery (optional)

## License

- **Code**: MIT License
- **Data**: CC0 (Public Domain) - from OurAirports
