#!/usr/bin/env python3
"""
Airport Runway Database Builder using OurAirports Data

OurAirports (https://ourairports.com) is an open data project that provides
comprehensive information about airports worldwide. Data is CC0 licensed.

Data includes:
- 70,000+ airports worldwide
- Runway information (length, width, surface, lighting)
- ICAO and IATA codes
- Geographic coordinates
"""

import sqlite3
import csv
import os
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import urllib.request
import ssl

# Configuration
DATABASE_PATH = "airport_runways.db"
DATA_DIR = "ourairports_data"

# OurAirports data URLs
AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
RUNWAYS_URL = "https://davidmegginson.github.io/ourairports-data/runways.csv"
COUNTRIES_URL = "https://davidmegginson.github.io/ourairports-data/countries.csv"
REGIONS_URL = "https://davidmegginson.github.io/ourairports-data/regions.csv"

# Backup URLs (raw GitHub)
AIRPORTS_URL_BACKUP = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
RUNWAYS_URL_BACKUP = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/runways.csv"


def create_database(db_path: str) -> sqlite3.Connection:
    """Create the SQLite database with proper schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Airports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS airports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ourairports_id INTEGER UNIQUE,
            ident TEXT,
            type TEXT,
            name TEXT,
            latitude REAL,
            longitude REAL,
            elevation_ft REAL,
            continent TEXT,
            iso_country TEXT,
            iso_region TEXT,
            municipality TEXT,
            scheduled_service TEXT,
            gps_code TEXT,
            iata_code TEXT,
            local_code TEXT,
            home_link TEXT,
            wikipedia_link TEXT,
            keywords TEXT,
            data_source TEXT DEFAULT 'OurAirports',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Runways table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ourairports_id INTEGER UNIQUE,
            airport_id INTEGER,
            airport_ref INTEGER,
            airport_ident TEXT,
            length_ft REAL,
            length_m REAL,
            width_ft REAL,
            width_m REAL,
            surface TEXT,
            lighted INTEGER,
            closed INTEGER,
            le_ident TEXT,
            le_latitude REAL,
            le_longitude REAL,
            le_elevation_ft REAL,
            le_heading_deg REAL,
            le_displaced_threshold_ft REAL,
            he_ident TEXT,
            he_latitude REAL,
            he_longitude REAL,
            he_elevation_ft REAL,
            he_heading_deg REAL,
            he_displaced_threshold_ft REAL,
            data_source TEXT DEFAULT 'OurAirports',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (airport_id) REFERENCES airports(id)
        )
    ''')

    # Countries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT,
            continent TEXT,
            wikipedia_link TEXT,
            keywords TEXT
        )
    ''')

    # Historical data table (for future tracking)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runway_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            runway_id INTEGER,
            length_ft REAL,
            width_ft REAL,
            surface TEXT,
            observation_date DATE,
            data_source TEXT,
            notes TEXT,
            FOREIGN KEY (runway_id) REFERENCES runways(id)
        )
    ''')

    # Imagery table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runway_imagery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_id INTEGER,
            runway_id INTEGER,
            image_path TEXT,
            image_url TEXT,
            capture_date DATE,
            imagery_source TEXT,
            zoom_level INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (airport_id) REFERENCES airports(id),
            FOREIGN KEY (runway_id) REFERENCES runways(id)
        )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_ident ON airports(ident)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_iata ON airports(iata_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_country ON airports(iso_country)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_type ON airports(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_runways_airport ON runways(airport_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_runways_airport_ident ON runways(airport_ident)')

    conn.commit()
    return conn


def download_csv(url: str, backup_url: str = None) -> str:
    """Download CSV data from URL."""
    print(f"Downloading from {url}...")

    # Create SSL context that doesn't verify (for environments with proxy issues)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    urls_to_try = [url]
    if backup_url:
        urls_to_try.append(backup_url)

    for try_url in urls_to_try:
        try:
            req = urllib.request.Request(
                try_url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; AirportDB/1.0)'}
            )
            with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
                data = response.read().decode('utf-8')
                print(f"  Downloaded {len(data):,} bytes")
                return data
        except Exception as e:
            print(f"  Error downloading from {try_url}: {e}")
            continue

    raise Exception(f"Failed to download from all URLs")


def save_csv_locally(data: str, filename: str):
    """Save CSV data to local file for future use."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(data)
    print(f"  Saved to {filepath}")


def load_local_csv(filename: str) -> Optional[str]:
    """Load CSV from local file if exists."""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def parse_float(value: str) -> Optional[float]:
    """Safely parse a float value."""
    if not value or value.strip() == '':
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str) -> Optional[int]:
    """Safely parse an integer value."""
    if not value or value.strip() == '':
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_bool(value: str) -> int:
    """Parse boolean value to 0/1."""
    if not value:
        return 0
    return 1 if value.lower() in ('1', 'true', 'yes') else 0


def import_airports(conn: sqlite3.Connection, csv_data: str) -> Dict[str, int]:
    """Import airports from CSV data. Returns mapping of ident to db id."""
    cursor = conn.cursor()
    reader = csv.DictReader(io.StringIO(csv_data))

    ident_to_id = {}
    count = 0
    skipped = 0

    print("Importing airports...")

    for row in reader:
        try:
            ourairports_id = parse_int(row.get('id'))
            ident = row.get('ident', '')

            cursor.execute('''
                INSERT OR REPLACE INTO airports
                (ourairports_id, ident, type, name, latitude, longitude,
                 elevation_ft, continent, iso_country, iso_region, municipality,
                 scheduled_service, gps_code, iata_code, local_code,
                 home_link, wikipedia_link, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ourairports_id,
                ident,
                row.get('type'),
                row.get('name'),
                parse_float(row.get('latitude_deg')),
                parse_float(row.get('longitude_deg')),
                parse_float(row.get('elevation_ft')),
                row.get('continent'),
                row.get('iso_country'),
                row.get('iso_region'),
                row.get('municipality'),
                row.get('scheduled_service'),
                row.get('gps_code'),
                row.get('iata_code') if row.get('iata_code') else None,
                row.get('local_code'),
                row.get('home_link'),
                row.get('wikipedia_link'),
                row.get('keywords')
            ))

            if ident:
                ident_to_id[ident] = cursor.lastrowid

            count += 1
            if count % 10000 == 0:
                print(f"  Imported {count:,} airports...")
                conn.commit()

        except Exception as e:
            skipped += 1
            if skipped <= 5:
                print(f"  Error importing airport: {e}")

    conn.commit()
    print(f"  Imported {count:,} airports ({skipped} skipped)")
    return ident_to_id


def import_runways(conn: sqlite3.Connection, csv_data: str, ident_to_id: Dict[str, int]):
    """Import runways from CSV data."""
    cursor = conn.cursor()
    reader = csv.DictReader(io.StringIO(csv_data))

    count = 0
    linked = 0
    skipped = 0

    print("Importing runways...")

    for row in reader:
        try:
            ourairports_id = parse_int(row.get('id'))
            airport_ident = row.get('airport_ident', '')
            airport_id = ident_to_id.get(airport_ident)

            length_ft = parse_float(row.get('length_ft'))
            width_ft = parse_float(row.get('width_ft'))

            # Convert to meters
            length_m = length_ft * 0.3048 if length_ft else None
            width_m = width_ft * 0.3048 if width_ft else None

            cursor.execute('''
                INSERT OR REPLACE INTO runways
                (ourairports_id, airport_id, airport_ref, airport_ident,
                 length_ft, length_m, width_ft, width_m, surface, lighted, closed,
                 le_ident, le_latitude, le_longitude, le_elevation_ft, le_heading_deg,
                 le_displaced_threshold_ft, he_ident, he_latitude, he_longitude,
                 he_elevation_ft, he_heading_deg, he_displaced_threshold_ft)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ourairports_id,
                airport_id,
                parse_int(row.get('airport_ref')),
                airport_ident,
                length_ft,
                length_m,
                width_ft,
                width_m,
                row.get('surface'),
                parse_bool(row.get('lighted')),
                parse_bool(row.get('closed')),
                row.get('le_ident'),
                parse_float(row.get('le_latitude_deg')),
                parse_float(row.get('le_longitude_deg')),
                parse_float(row.get('le_elevation_ft')),
                parse_float(row.get('le_heading_degT')),
                parse_float(row.get('le_displaced_threshold_ft')),
                row.get('he_ident'),
                parse_float(row.get('he_latitude_deg')),
                parse_float(row.get('he_longitude_deg')),
                parse_float(row.get('he_elevation_ft')),
                parse_float(row.get('he_heading_degT')),
                parse_float(row.get('he_displaced_threshold_ft'))
            ))

            count += 1
            if airport_id:
                linked += 1

            if count % 10000 == 0:
                print(f"  Imported {count:,} runways...")
                conn.commit()

        except Exception as e:
            skipped += 1
            if skipped <= 5:
                print(f"  Error importing runway: {e}")

    conn.commit()
    print(f"  Imported {count:,} runways ({linked:,} linked to airports, {skipped} skipped)")


def import_countries(conn: sqlite3.Connection, csv_data: str):
    """Import countries from CSV data."""
    cursor = conn.cursor()
    reader = csv.DictReader(io.StringIO(csv_data))

    count = 0
    for row in reader:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO countries
                (code, name, continent, wikipedia_link, keywords)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                row.get('code'),
                row.get('name'),
                row.get('continent'),
                row.get('wikipedia_link'),
                row.get('keywords')
            ))
            count += 1
        except Exception as e:
            pass

    conn.commit()
    print(f"  Imported {count} countries")


def generate_statistics(conn: sqlite3.Connection):
    """Generate and print database statistics."""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM airports")
    print(f"Total airports: {cursor.fetchone()[0]:,}")

    cursor.execute("SELECT COUNT(*) FROM runways")
    print(f"Total runways: {cursor.fetchone()[0]:,}")

    # By airport type
    print("\nAirports by type:")
    cursor.execute('''
        SELECT type, COUNT(*) as count
        FROM airports
        GROUP BY type
        ORDER BY count DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")

    # Airports with codes
    cursor.execute("SELECT COUNT(*) FROM airports WHERE iata_code IS NOT NULL AND iata_code != ''")
    print(f"\nAirports with IATA code: {cursor.fetchone()[0]:,}")

    cursor.execute("SELECT COUNT(*) FROM airports WHERE gps_code IS NOT NULL AND gps_code != ''")
    print(f"Airports with ICAO/GPS code: {cursor.fetchone()[0]:,}")

    # Runway statistics
    cursor.execute("SELECT AVG(length_ft) FROM runways WHERE length_ft IS NOT NULL AND length_ft > 0")
    avg_length = cursor.fetchone()[0]
    if avg_length:
        print(f"\nAverage runway length: {avg_length:.0f}ft ({avg_length*0.3048:.0f}m)")

    cursor.execute("SELECT MAX(length_ft) FROM runways")
    max_length = cursor.fetchone()[0]
    if max_length:
        print(f"Longest runway: {max_length:.0f}ft ({max_length*0.3048:.0f}m)")

    # Top 10 longest runways
    print("\nTop 10 longest runways:")
    cursor.execute('''
        SELECT r.length_ft, r.le_ident, r.he_ident, r.surface,
               a.ident, a.name, a.iso_country
        FROM runways r
        JOIN airports a ON r.airport_id = a.id
        WHERE r.length_ft IS NOT NULL
        ORDER BY r.length_ft DESC
        LIMIT 10
    ''')
    for i, row in enumerate(cursor.fetchall(), 1):
        rwy_name = f"{row[1]}/{row[2]}" if row[1] and row[2] else "Unknown"
        print(f"  {i:2}. {row[0]:,.0f}ft ({row[0]*0.3048:,.0f}m) - {row[4]} {row[5][:40]} ({row[6]}) - RWY {rwy_name}")

    # Airports with most runways
    print("\nAirports with most runways:")
    cursor.execute('''
        SELECT a.ident, a.name, a.iso_country, COUNT(r.id) as rwy_count
        FROM airports a
        JOIN runways r ON a.id = r.airport_id
        GROUP BY a.id
        ORDER BY rwy_count DESC
        LIMIT 10
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1][:40]} ({row[2]}): {row[3]} runways")

    # Surface types
    print("\nRunway surface types:")
    cursor.execute('''
        SELECT surface, COUNT(*) as count
        FROM runways
        WHERE surface IS NOT NULL AND surface != ''
        GROUP BY surface
        ORDER BY count DESC
        LIMIT 15
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")

    # By continent
    print("\nAirports by continent:")
    cursor.execute('''
        SELECT continent, COUNT(*) as count
        FROM airports
        WHERE continent IS NOT NULL
        GROUP BY continent
        ORDER BY count DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")

    print("="*60)


def main():
    """Main entry point."""
    print("="*60)
    print("AIRPORT RUNWAY DATABASE BUILDER")
    print("Data Source: OurAirports (https://ourairports.com)")
    print("License: CC0 (Public Domain)")
    print("="*60)
    print()

    # Create database
    print("Creating database...")
    conn = create_database(DATABASE_PATH)

    # Try to download data (with fallback to local cache)
    try:
        # Download airports
        airports_csv = load_local_csv("airports.csv")
        if not airports_csv:
            airports_csv = download_csv(AIRPORTS_URL, AIRPORTS_URL_BACKUP)
            save_csv_locally(airports_csv, "airports.csv")

        # Download runways
        runways_csv = load_local_csv("runways.csv")
        if not runways_csv:
            runways_csv = download_csv(RUNWAYS_URL, RUNWAYS_URL_BACKUP)
            save_csv_locally(runways_csv, "runways.csv")

        # Download countries (optional)
        try:
            countries_csv = load_local_csv("countries.csv")
            if not countries_csv:
                countries_csv = download_csv(COUNTRIES_URL)
                save_csv_locally(countries_csv, "countries.csv")
        except:
            countries_csv = None
            print("  Countries data not available")

    except Exception as e:
        print(f"Error downloading data: {e}")
        print("\nPlease download the CSV files manually from:")
        print("  https://ourairports.com/data/")
        print(f"And place them in the '{DATA_DIR}' directory.")
        return

    # Import data
    print("\n" + "-"*40)
    ident_to_id = import_airports(conn, airports_csv)
    import_runways(conn, runways_csv, ident_to_id)
    if countries_csv:
        import_countries(conn, countries_csv)

    # Generate statistics
    generate_statistics(conn)

    print(f"\nDatabase saved to: {DATABASE_PATH}")
    print(f"Database size: {os.path.getsize(DATABASE_PATH) / (1024*1024):.1f} MB")

    print("\n" + "="*60)
    print("NOTES ON HISTORICAL DATA")
    print("="*60)
    print("""
The OurAirports database contains CURRENT runway information.
For historical data (1985-present), you would need:

1. Google Earth Engine (historical Landsat imagery from 1984)
   - Requires Google Cloud account
   - Can analyze runway changes over time via imagery

2. FAA Historical Data (US airports only)
   - https://www.faa.gov/air_traffic/flight_info/aeronav/

3. ICAO/National Aviation Authorities
   - Historical records require formal data requests

4. Internet Archive Wayback Machine
   - Historical snapshots of airport websites

To add satellite imagery, run:
  python fetch_imagery.py --provider google --api-key YOUR_KEY
""")

    conn.close()


if __name__ == "__main__":
    main()
