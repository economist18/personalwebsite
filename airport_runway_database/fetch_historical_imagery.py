#!/usr/bin/env python3
"""
Historical Airport Imagery Fetcher using Google Earth Engine

This script fetches historical satellite imagery from Landsat and Sentinel
collections to track airport runway changes over time (1985-present).

Requirements:
    - Google Cloud account with Earth Engine enabled
    - earthengine-api package
    - Authentication: Run `earthengine authenticate` first

Data sources:
    - Landsat 5 TM (1984-2012)
    - Landsat 7 ETM+ (1999-present)
    - Landsat 8 OLI (2013-present)
    - Landsat 9 OLI-2 (2021-present)
    - Sentinel-2 (2015-present)
"""

import sqlite3
import os
import argparse
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

DATABASE_PATH = "airport_runways.db"
HISTORICAL_DIR = "historical_imagery"

# Check if Earth Engine is available
try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False
    print("Warning: earthengine-api not installed. Install with: pip install earthengine-api")


def initialize_earth_engine():
    """Initialize Google Earth Engine."""
    if not EE_AVAILABLE:
        return False

    try:
        ee.Initialize()
        print("Earth Engine initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing Earth Engine: {e}")
        print("Please run 'earthengine authenticate' first")
        return False


def get_landsat_collection(start_year: int, end_year: int, geometry) -> Optional[object]:
    """Get the appropriate Landsat collection for the time period."""
    if not EE_AVAILABLE:
        return None

    collections = []

    # Landsat 5 (1984-2012)
    if start_year <= 2012 and end_year >= 1984:
        l5_start = max(start_year, 1984)
        l5_end = min(end_year, 2012)
        l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
            .filterDate(f'{l5_start}-01-01', f'{l5_end}-12-31') \
            .filterBounds(geometry) \
            .select(['SR_B3', 'SR_B2', 'SR_B1'], ['R', 'G', 'B'])
        collections.append(l5)

    # Landsat 7 (1999-present)
    if start_year <= 2023 and end_year >= 1999:
        l7_start = max(start_year, 1999)
        l7_end = min(end_year, 2023)
        l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2') \
            .filterDate(f'{l7_start}-01-01', f'{l7_end}-12-31') \
            .filterBounds(geometry) \
            .select(['SR_B3', 'SR_B2', 'SR_B1'], ['R', 'G', 'B'])
        collections.append(l7)

    # Landsat 8 (2013-present)
    if end_year >= 2013:
        l8_start = max(start_year, 2013)
        l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
            .filterDate(f'{l8_start}-01-01', f'{end_year}-12-31') \
            .filterBounds(geometry) \
            .select(['SR_B4', 'SR_B3', 'SR_B2'], ['R', 'G', 'B'])
        collections.append(l8)

    # Landsat 9 (2021-present)
    if end_year >= 2021:
        l9_start = max(start_year, 2021)
        l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
            .filterDate(f'{l9_start}-01-01', f'{end_year}-12-31') \
            .filterBounds(geometry) \
            .select(['SR_B4', 'SR_B3', 'SR_B2'], ['R', 'G', 'B'])
        collections.append(l9)

    if collections:
        return ee.ImageCollection(collections[0]).merge(
            ee.ImageCollection(collections[1]) if len(collections) > 1 else ee.ImageCollection([])
        )
    return None


def get_historical_images_for_airport(
    lat: float,
    lon: float,
    start_year: int = 1985,
    end_year: int = 2024,
    interval_years: int = 5
) -> List[dict]:
    """Get historical imagery for an airport location."""
    if not EE_AVAILABLE:
        return []

    results = []
    point = ee.Geometry.Point([lon, lat])
    region = point.buffer(3000)  # 3km buffer around airport

    for year in range(start_year, end_year + 1, interval_years):
        try:
            # Get images for this year
            start_date = f'{year}-01-01'
            end_date = f'{year}-12-31'

            # Try Landsat first
            collection = get_landsat_collection(year, year, region)

            if collection:
                # Get median composite for the year
                image = collection.filterDate(start_date, end_date).median()

                # Generate download URL
                url = image.getThumbURL({
                    'region': region,
                    'dimensions': 640,
                    'format': 'png'
                })

                results.append({
                    'year': year,
                    'url': url,
                    'source': 'Landsat'
                })

        except Exception as e:
            print(f"  Error getting imagery for year {year}: {e}")

    return results


def fetch_historical_imagery_for_airports(
    conn: sqlite3.Connection,
    start_year: int = 1985,
    end_year: int = 2024,
    interval_years: int = 5,
    limit: Optional[int] = None
):
    """Fetch historical imagery for airports with ICAO codes."""
    if not initialize_earth_engine():
        print("\nCannot proceed without Earth Engine access.")
        print("\nAlternative: Use Google Earth Pro (desktop application)")
        print("to manually export historical imagery time-lapse.")
        return

    cursor = conn.cursor()

    # Get airports with ICAO codes (major airports)
    query = '''
        SELECT id, icao_code, name, latitude, longitude
        FROM airports
        WHERE icao_code IS NOT NULL
        AND latitude IS NOT NULL
        AND longitude IS NOT NULL
        ORDER BY icao_code
    '''

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    airports = cursor.fetchall()

    print(f"Processing {len(airports)} airports for historical imagery")
    print(f"Time range: {start_year} to {end_year}, every {interval_years} years")

    for i, (airport_id, icao, name, lat, lon) in enumerate(airports):
        print(f"\n[{i+1}/{len(airports)}] {icao} - {name}")

        # Create directory for airport
        airport_dir = os.path.join(HISTORICAL_DIR, icao)
        os.makedirs(airport_dir, exist_ok=True)

        # Get historical images
        images = get_historical_images_for_airport(
            lat, lon, start_year, end_year, interval_years
        )

        for img_info in images:
            year = img_info['year']
            url = img_info['url']
            source = img_info['source']

            filepath = os.path.join(airport_dir, f"{icao}_{year}.png")

            if os.path.exists(filepath):
                print(f"  {year}: Already exists")
                continue

            try:
                import requests
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                # Record in database
                cursor.execute('''
                    INSERT INTO runway_imagery
                    (airport_id, image_path, image_url, capture_date, imagery_source, zoom_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (airport_id, filepath, url, f"{year}-07-01", f"Landsat-{source}", 0))
                conn.commit()

                print(f"  {year}: Saved ({source})")

            except Exception as e:
                print(f"  {year}: Error - {e}")

    print("\nHistorical imagery fetch complete.")


def export_to_google_earth_pro_kml(conn: sqlite3.Connection, output_file: str = "airports.kml"):
    """Export airports to KML for viewing in Google Earth Pro."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.icao_code, a.name, a.latitude, a.longitude,
               COUNT(r.id) as runway_count,
               MAX(r.length_m) as max_runway_length
        FROM airports a
        LEFT JOIN runways r ON a.id = r.airport_id
        WHERE a.icao_code IS NOT NULL
        GROUP BY a.id
        ORDER BY a.icao_code
    ''')

    airports = cursor.fetchall()

    kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>World Airports</name>
    <description>Airport locations for historical imagery analysis in Google Earth Pro</description>
'''

    for icao, name, lat, lon, runway_count, max_length in airports:
        if lat and lon:
            length_str = f"{max_length:.0f}m" if max_length else "Unknown"
            kml_content += f'''
    <Placemark>
        <name>{icao}</name>
        <description><![CDATA[
            <b>{name}</b><br/>
            Runways: {runway_count}<br/>
            Longest: {length_str}
        ]]></description>
        <Point>
            <coordinates>{lon},{lat},0</coordinates>
        </Point>
    </Placemark>'''

    kml_content += '''
</Document>
</kml>'''

    with open(output_file, 'w') as f:
        f.write(kml_content)

    print(f"Exported {len(airports)} airports to {output_file}")
    print("Open this file in Google Earth Pro to view historical imagery manually.")


def main():
    parser = argparse.ArgumentParser(description="Fetch historical satellite imagery")
    parser.add_argument("--start-year", type=int, default=1985, help="Start year")
    parser.add_argument("--end-year", type=int, default=2024, help="End year")
    parser.add_argument("--interval", type=int, default=5, help="Years between images")
    parser.add_argument("--limit", type=int, help="Limit number of airports")
    parser.add_argument("--export-kml", action="store_true", help="Export to KML for Google Earth Pro")
    parser.add_argument("--db", default=DATABASE_PATH, help="Database path")

    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    os.makedirs(HISTORICAL_DIR, exist_ok=True)

    if args.export_kml:
        export_to_google_earth_pro_kml(conn)
    else:
        fetch_historical_imagery_for_airports(
            conn, args.start_year, args.end_year, args.interval, args.limit
        )

    conn.close()


if __name__ == "__main__":
    main()
