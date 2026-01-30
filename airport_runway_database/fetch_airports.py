#!/usr/bin/env python3
"""
Airport Runway Database Builder

Fetches worldwide airport and runway data from OpenStreetMap
and builds a SQLite database with runway information.

Data source: OpenStreetMap via Overpass API
"""

import sqlite3
import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import math

# Configuration
DATABASE_PATH = "airport_runways.db"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
IMAGERY_DIR = "runway_imagery"

# Rate limiting for Overpass API
REQUEST_DELAY = 10  # seconds between requests


def create_database(db_path: str) -> sqlite3.Connection:
    """Create the SQLite database with proper schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Airports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS airports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osm_id INTEGER UNIQUE,
            icao_code TEXT,
            iata_code TEXT,
            name TEXT,
            latitude REAL,
            longitude REAL,
            elevation_m REAL,
            airport_type TEXT,
            country TEXT,
            wikipedia_link TEXT,
            data_source TEXT DEFAULT 'OpenStreetMap',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Runways table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_id INTEGER,
            osm_id INTEGER,
            runway_designator TEXT,
            length_m REAL,
            width_m REAL,
            surface TEXT,
            lighted INTEGER,
            heading REAL,
            latitude REAL,
            longitude REAL,
            geometry_wkt TEXT,
            data_source TEXT DEFAULT 'OpenStreetMap',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (airport_id) REFERENCES airports(id)
        )
    ''')

    # Historical data table (for tracking changes over time)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runway_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            runway_id INTEGER,
            length_m REAL,
            width_m REAL,
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

    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_icao ON airports(icao_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_iata ON airports(iata_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_country ON airports(country)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_runways_airport ON runways(airport_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_runway_history_runway ON runway_history(runway_id)')

    conn.commit()
    return conn


def calculate_runway_length(coords: List[Tuple[float, float]]) -> float:
    """Calculate runway length in meters from coordinates using Haversine formula."""
    if len(coords) < 2:
        return 0

    # Use first and last point for runway length
    lat1, lon1 = coords[0]
    lat2, lon2 = coords[-1]

    # Haversine formula
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def calculate_heading(coords: List[Tuple[float, float]]) -> float:
    """Calculate runway heading from coordinates."""
    if len(coords) < 2:
        return 0

    lat1, lon1 = coords[0]
    lat2, lon2 = coords[-1]

    # Calculate bearing
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def coords_to_wkt(coords: List[Tuple[float, float]]) -> str:
    """Convert coordinate list to WKT LINESTRING."""
    if not coords:
        return ""
    points = ", ".join([f"{lon} {lat}" for lat, lon in coords])
    return f"LINESTRING({points})"


def fetch_airports_by_region(south: float, west: float, north: float, east: float) -> dict:
    """Fetch airports and runways for a bounding box region."""

    query = f"""
    [out:json][timeout:180];
    (
      // Airports
      node["aeroway"="aerodrome"]({south},{west},{north},{east});
      way["aeroway"="aerodrome"]({south},{west},{north},{east});
      relation["aeroway"="aerodrome"]({south},{west},{north},{east});

      // Runways
      way["aeroway"="runway"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """

    try:
        response = requests.post(OVERPASS_URL, data={"data": query}, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching region ({south},{west},{north},{east}): {e}")
        return {"elements": []}


def process_osm_data(data: dict) -> Tuple[List[dict], List[dict]]:
    """Process raw OSM data into airports and runways."""
    airports = []
    runways = []
    nodes = {}

    # First pass: collect all nodes for coordinate lookup
    for element in data.get("elements", []):
        if element["type"] == "node":
            nodes[element["id"]] = (element["lat"], element["lon"])

    # Second pass: process airports and runways
    for element in data.get("elements", []):
        tags = element.get("tags", {})

        if tags.get("aeroway") == "aerodrome":
            # Get center coordinates
            if element["type"] == "node":
                lat, lon = element["lat"], element["lon"]
            elif element["type"] == "way" and "nodes" in element:
                node_coords = [nodes.get(n) for n in element["nodes"] if n in nodes]
                if node_coords:
                    lat = sum(c[0] for c in node_coords) / len(node_coords)
                    lon = sum(c[1] for c in node_coords) / len(node_coords)
                else:
                    continue
            else:
                continue

            airport = {
                "osm_id": element["id"],
                "icao_code": tags.get("icao"),
                "iata_code": tags.get("iata"),
                "name": tags.get("name", tags.get("official_name", "Unknown")),
                "latitude": lat,
                "longitude": lon,
                "elevation_m": tags.get("ele"),
                "airport_type": tags.get("aerodrome:type", tags.get("type", "unknown")),
                "wikipedia_link": tags.get("wikipedia")
            }
            airports.append(airport)

        elif tags.get("aeroway") == "runway" and element["type"] == "way":
            # Get runway coordinates
            if "nodes" not in element:
                continue

            coords = [nodes.get(n) for n in element["nodes"] if n in nodes]
            coords = [c for c in coords if c is not None]

            if len(coords) < 2:
                continue

            # Calculate center point
            center_lat = sum(c[0] for c in coords) / len(coords)
            center_lon = sum(c[1] for c in coords) / len(coords)

            # Parse width
            width = tags.get("width")
            if width:
                try:
                    width = float(width.replace("m", "").strip())
                except:
                    width = None

            # Parse length (prefer explicit tag, calculate if not present)
            length = tags.get("length")
            if length:
                try:
                    length = float(length.replace("m", "").strip())
                except:
                    length = calculate_runway_length(coords)
            else:
                length = calculate_runway_length(coords)

            runway = {
                "osm_id": element["id"],
                "runway_designator": tags.get("ref", tags.get("name", "Unknown")),
                "length_m": length,
                "width_m": width,
                "surface": tags.get("surface"),
                "lighted": 1 if tags.get("lighted") == "yes" else 0,
                "heading": calculate_heading(coords),
                "latitude": center_lat,
                "longitude": center_lon,
                "geometry_wkt": coords_to_wkt(coords)
            }
            runways.append(runway)

    return airports, runways


def find_nearest_airport(runway: dict, airports: List[dict], max_distance_km: float = 10) -> Optional[dict]:
    """Find the nearest airport to a runway within max_distance_km."""
    runway_lat = runway["latitude"]
    runway_lon = runway["longitude"]

    nearest = None
    min_distance = float('inf')

    for airport in airports:
        # Quick distance approximation
        lat_diff = abs(airport["latitude"] - runway_lat)
        lon_diff = abs(airport["longitude"] - runway_lon)

        # Rough km per degree
        km_per_lat = 111
        km_per_lon = 111 * math.cos(math.radians(runway_lat))

        distance = math.sqrt((lat_diff * km_per_lat)**2 + (lon_diff * km_per_lon)**2)

        if distance < min_distance and distance < max_distance_km:
            min_distance = distance
            nearest = airport

    return nearest


def insert_airports_and_runways(conn: sqlite3.Connection, airports: List[dict], runways: List[dict]):
    """Insert airports and runways into the database."""
    cursor = conn.cursor()

    # Insert airports
    airport_id_map = {}  # osm_id -> db_id

    for airport in airports:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO airports
                (osm_id, icao_code, iata_code, name, latitude, longitude,
                 elevation_m, airport_type, wikipedia_link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                airport["osm_id"],
                airport.get("icao_code"),
                airport.get("iata_code"),
                airport.get("name"),
                airport["latitude"],
                airport["longitude"],
                airport.get("elevation_m"),
                airport.get("airport_type"),
                airport.get("wikipedia_link")
            ))

            if cursor.rowcount > 0:
                airport_id_map[airport["osm_id"]] = cursor.lastrowid
            else:
                # Already exists, get the id
                cursor.execute('SELECT id FROM airports WHERE osm_id = ?', (airport["osm_id"],))
                result = cursor.fetchone()
                if result:
                    airport_id_map[airport["osm_id"]] = result[0]
        except Exception as e:
            print(f"  Error inserting airport {airport.get('name')}: {e}")

    # Insert runways and link to nearest airport
    for runway in runways:
        nearest_airport = find_nearest_airport(runway, airports)
        airport_db_id = None

        if nearest_airport and nearest_airport["osm_id"] in airport_id_map:
            airport_db_id = airport_id_map[nearest_airport["osm_id"]]

        try:
            cursor.execute('''
                INSERT OR IGNORE INTO runways
                (airport_id, osm_id, runway_designator, length_m, width_m,
                 surface, lighted, heading, latitude, longitude, geometry_wkt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                airport_db_id,
                runway["osm_id"],
                runway.get("runway_designator"),
                runway.get("length_m"),
                runway.get("width_m"),
                runway.get("surface"),
                runway.get("lighted"),
                runway.get("heading"),
                runway["latitude"],
                runway["longitude"],
                runway.get("geometry_wkt")
            ))
        except Exception as e:
            print(f"  Error inserting runway {runway.get('runway_designator')}: {e}")

    conn.commit()


def get_world_regions() -> List[Tuple[float, float, float, float]]:
    """Get list of bounding boxes covering the world in manageable chunks."""
    regions = []

    # Divide world into 30x30 degree boxes
    for lat in range(-90, 90, 30):
        for lon in range(-180, 180, 30):
            south = lat
            north = min(lat + 30, 90)
            west = lon
            east = min(lon + 30, 180)
            regions.append((south, west, north, east))

    return regions


def fetch_all_airports(conn: sqlite3.Connection):
    """Fetch all airports and runways from OpenStreetMap."""
    regions = get_world_regions()
    total_regions = len(regions)

    print(f"Fetching airport data from {total_regions} regions...")
    print("This will take some time due to API rate limits.\n")

    all_airports = []
    all_runways = []

    for i, (south, west, north, east) in enumerate(regions):
        print(f"Region {i+1}/{total_regions}: ({south},{west}) to ({north},{east})")

        data = fetch_airports_by_region(south, west, north, east)
        airports, runways = process_osm_data(data)

        print(f"  Found {len(airports)} airports, {len(runways)} runways")

        if airports or runways:
            insert_airports_and_runways(conn, airports, runways)
            all_airports.extend(airports)
            all_runways.extend(runways)

        # Rate limiting
        if i < total_regions - 1:
            print(f"  Waiting {REQUEST_DELAY}s for rate limiting...")
            time.sleep(REQUEST_DELAY)

    return all_airports, all_runways


def add_country_info(conn: sqlite3.Connection):
    """Add country information based on coordinates (simplified)."""
    # This is a simplified version - for production use a proper reverse geocoding service
    print("\nNote: Country information requires reverse geocoding API (not included in basic version)")


def generate_statistics(conn: sqlite3.Connection):
    """Generate and print database statistics."""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)

    cursor.execute("SELECT COUNT(*) FROM airports")
    airport_count = cursor.fetchone()[0]
    print(f"Total airports: {airport_count:,}")

    cursor.execute("SELECT COUNT(*) FROM runways")
    runway_count = cursor.fetchone()[0]
    print(f"Total runways: {runway_count:,}")

    cursor.execute("SELECT COUNT(*) FROM airports WHERE icao_code IS NOT NULL")
    icao_count = cursor.fetchone()[0]
    print(f"Airports with ICAO code: {icao_count:,}")

    cursor.execute("SELECT COUNT(*) FROM airports WHERE iata_code IS NOT NULL")
    iata_count = cursor.fetchone()[0]
    print(f"Airports with IATA code: {iata_count:,}")

    cursor.execute("SELECT COUNT(*) FROM runways WHERE length_m IS NOT NULL")
    length_count = cursor.fetchone()[0]
    print(f"Runways with length data: {length_count:,}")

    cursor.execute("SELECT AVG(length_m) FROM runways WHERE length_m IS NOT NULL AND length_m > 0")
    avg_length = cursor.fetchone()[0]
    if avg_length:
        print(f"Average runway length: {avg_length:.1f}m ({avg_length*3.28084:.1f}ft)")

    cursor.execute("SELECT MAX(length_m) FROM runways WHERE length_m IS NOT NULL")
    max_length = cursor.fetchone()[0]
    if max_length:
        print(f"Longest runway: {max_length:.1f}m ({max_length*3.28084:.1f}ft)")

    # Runway count distribution
    print("\nRunways per airport:")
    cursor.execute('''
        SELECT runway_count, COUNT(*) as airports
        FROM (
            SELECT airport_id, COUNT(*) as runway_count
            FROM runways
            WHERE airport_id IS NOT NULL
            GROUP BY airport_id
        )
        GROUP BY runway_count
        ORDER BY runway_count
        LIMIT 10
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]} runway(s): {row[1]:,} airports")

    print("="*60)


def main():
    """Main entry point."""
    print("="*60)
    print("AIRPORT RUNWAY DATABASE BUILDER")
    print("Data Source: OpenStreetMap")
    print("="*60)
    print()

    # Create database
    print("Creating database...")
    conn = create_database(DATABASE_PATH)

    # Create imagery directory
    os.makedirs(IMAGERY_DIR, exist_ok=True)

    # Fetch all airport data
    fetch_all_airports(conn)

    # Generate statistics
    generate_statistics(conn)

    print(f"\nDatabase saved to: {DATABASE_PATH}")
    print("\nNOTE: Historical data (1985-present) requires:")
    print("  1. Google Earth Engine access for historical imagery")
    print("  2. Aviation authority data archives")
    print("  3. Manual digitization from historical sources")
    print("\nTo add satellite imagery, run: python fetch_imagery.py --api-key YOUR_KEY")

    conn.close()


if __name__ == "__main__":
    main()
