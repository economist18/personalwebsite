#!/usr/bin/env python3
"""
Airport Runway Imagery Fetcher

Fetches satellite imagery for airports and runways.
Supports multiple imagery providers:
- Google Maps Static API
- Mapbox Static API
- Bing Maps API

Usage:
    python fetch_imagery.py --provider google --api-key YOUR_API_KEY
    python fetch_imagery.py --provider mapbox --api-key YOUR_API_KEY
    python fetch_imagery.py --provider bing --api-key YOUR_API_KEY
    python fetch_imagery.py --provider google --api-key YOUR_API_KEY --runways --limit 100
"""

import sqlite3
import requests
import os
import argparse
import time
from datetime import datetime
from typing import Optional

DATABASE_PATH = "airport_runways.db"
IMAGERY_DIR = "runway_imagery"
REQUEST_DELAY = 0.5  # seconds between requests


def get_google_imagery_url(lat: float, lon: float, zoom: int, size: str, api_key: str) -> str:
    """Generate Google Maps Static API URL."""
    return (
        f"https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat},{lon}"
        f"&zoom={zoom}"
        f"&size={size}"
        f"&maptype=satellite"
        f"&key={api_key}"
    )


def get_mapbox_imagery_url(lat: float, lon: float, zoom: int, size: str, api_key: str) -> str:
    """Generate Mapbox Static API URL."""
    width, height = size.split("x")
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static"
        f"/{lon},{lat},{zoom}"
        f"/{width}x{height}"
        f"?access_token={api_key}"
    )


def get_bing_imagery_url(lat: float, lon: float, zoom: int, size: str, api_key: str) -> str:
    """Generate Bing Maps Static API URL."""
    width, height = size.split("x")
    return (
        f"https://dev.virtualearth.net/REST/v1/Imagery/Map/Aerial"
        f"/{lat},{lon}/{zoom}"
        f"?mapSize={width},{height}"
        f"&key={api_key}"
    )


def download_image(url: str, save_path: str) -> bool:
    """Download an image from URL and save to path."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Check if response is actually an image
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            print(f"  Warning: Response is not an image ({content_type})")
            return False

        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True

    except Exception as e:
        print(f"  Error downloading image: {e}")
        return False


def fetch_airport_imagery(
    conn: sqlite3.Connection,
    provider: str,
    api_key: str,
    zoom: int = 15,
    size: str = "640x640",
    limit: Optional[int] = None,
    airport_types: list = None
):
    """Fetch imagery for airports in the database."""
    cursor = conn.cursor()

    # Get URL generator based on provider
    url_generators = {
        "google": get_google_imagery_url,
        "mapbox": get_mapbox_imagery_url,
        "bing": get_bing_imagery_url
    }

    if provider not in url_generators:
        print(f"Unknown provider: {provider}")
        return

    get_url = url_generators[provider]

    # Default to major airport types
    if airport_types is None:
        airport_types = ['large_airport', 'medium_airport']

    type_placeholders = ','.join(['?' for _ in airport_types])

    # Get airports without imagery
    query = f'''
        SELECT a.id, a.ident, a.iata_code, a.name, a.latitude, a.longitude, a.type
        FROM airports a
        LEFT JOIN runway_imagery ri ON a.id = ri.airport_id AND ri.runway_id IS NULL
        WHERE ri.id IS NULL
        AND a.latitude IS NOT NULL
        AND a.longitude IS NOT NULL
        AND a.type IN ({type_placeholders})
        ORDER BY
            CASE a.type
                WHEN 'large_airport' THEN 1
                WHEN 'medium_airport' THEN 2
                ELSE 3
            END,
            a.ident
    '''

    params = list(airport_types)
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query, params)
    airports = cursor.fetchall()

    print(f"Found {len(airports)} airports without imagery")
    print(f"Using {provider} API with zoom level {zoom}")

    os.makedirs(IMAGERY_DIR, exist_ok=True)

    for i, (airport_id, ident, iata, name, lat, lon, apt_type) in enumerate(airports):
        code = ident or f"ID{airport_id}"
        print(f"[{i+1}/{len(airports)}] Fetching imagery for {code} ({iata or '-'}) - {name[:50]}")

        # Generate image filename
        filename = f"{code}_{lat:.4f}_{lon:.4f}.jpg"
        filepath = os.path.join(IMAGERY_DIR, filename)

        # Skip if already downloaded
        if os.path.exists(filepath):
            print(f"  Already exists, skipping")
            continue

        # Get imagery URL
        url = get_url(lat, lon, zoom, size, api_key)

        # Download image
        if download_image(url, filepath):
            # Record in database
            cursor.execute('''
                INSERT INTO runway_imagery
                (airport_id, image_path, image_url, capture_date, imagery_source, zoom_level)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (airport_id, filepath, url, datetime.now().date(), provider, zoom))
            conn.commit()
            print(f"  Saved to {filepath}")
        else:
            print(f"  Failed to download")

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    print(f"\nImagery fetch complete. Images saved to {IMAGERY_DIR}/")


def fetch_runway_imagery(
    conn: sqlite3.Connection,
    provider: str,
    api_key: str,
    zoom: int = 17,
    size: str = "640x640",
    limit: Optional[int] = None
):
    """Fetch close-up imagery for individual runways."""
    cursor = conn.cursor()

    url_generators = {
        "google": get_google_imagery_url,
        "mapbox": get_mapbox_imagery_url,
        "bing": get_bing_imagery_url
    }

    if provider not in url_generators:
        print(f"Unknown provider: {provider}")
        return

    get_url = url_generators[provider]

    # Get runways without imagery (using runway endpoint coordinates)
    query = '''
        SELECT r.id, r.airport_id, r.le_ident, r.he_ident,
               r.le_latitude, r.le_longitude, r.length_ft,
               a.ident, a.iata_code, a.name
        FROM runways r
        JOIN airports a ON r.airport_id = a.id
        LEFT JOIN runway_imagery ri ON r.id = ri.runway_id
        WHERE ri.id IS NULL
        AND r.le_latitude IS NOT NULL
        AND r.le_longitude IS NOT NULL
        AND a.type IN ('large_airport', 'medium_airport')
        ORDER BY r.length_ft DESC
    '''

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    runways = cursor.fetchall()

    print(f"Found {len(runways)} runways without imagery")
    print(f"Using {provider} API with zoom level {zoom}")

    runway_dir = os.path.join(IMAGERY_DIR, "runways")
    os.makedirs(runway_dir, exist_ok=True)

    for i, (runway_id, airport_id, le_ident, he_ident, lat, lon, length_ft, ident, iata, name) in enumerate(runways):
        rwy_name = f"{le_ident}/{he_ident}" if le_ident and he_ident else "UNK"
        code = ident or f"APT{airport_id}"
        print(f"[{i+1}/{len(runways)}] {code} Runway {rwy_name} ({length_ft:.0f}ft)")

        # Generate image filename
        safe_rwy = rwy_name.replace("/", "-")
        filename = f"{code}_RWY{safe_rwy}_{lat:.4f}_{lon:.4f}.jpg"
        filepath = os.path.join(runway_dir, filename)

        # Skip if already downloaded
        if os.path.exists(filepath):
            print(f"  Already exists, skipping")
            continue

        # Get imagery URL
        url = get_url(lat, lon, zoom, size, api_key)

        # Download image
        if download_image(url, filepath):
            cursor.execute('''
                INSERT INTO runway_imagery
                (airport_id, runway_id, image_path, image_url, capture_date, imagery_source, zoom_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (airport_id, runway_id, filepath, url, datetime.now().date(), provider, zoom))
            conn.commit()
            print(f"  Saved to {filepath}")
        else:
            print(f"  Failed to download")

        time.sleep(REQUEST_DELAY)

    print(f"\nRunway imagery fetch complete.")


def list_airports_for_imagery(conn: sqlite3.Connection, limit: int = 50):
    """List airports that would be fetched for imagery."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.ident, a.iata_code, a.name, a.latitude, a.longitude, a.type,
               COUNT(r.id) as runway_count
        FROM airports a
        LEFT JOIN runways r ON a.id = r.airport_id
        WHERE a.type IN ('large_airport', 'medium_airport')
        AND a.latitude IS NOT NULL
        GROUP BY a.id
        ORDER BY
            CASE a.type WHEN 'large_airport' THEN 1 ELSE 2 END,
            runway_count DESC
        LIMIT ?
    ''', (limit,))

    print(f"\n{'ICAO':<8} {'IATA':<6} {'Type':<15} {'RWY':<5} {'Name'}")
    print("-" * 80)

    for row in cursor.fetchall():
        print(f"{row[0]:<8} {row[1] or '-':<6} {row[5]:<15} {row[6]:<5} {row[2][:40]}")


def main():
    parser = argparse.ArgumentParser(description="Fetch satellite imagery for airports")
    parser.add_argument("--provider", choices=["google", "mapbox", "bing"],
                        help="Imagery provider")
    parser.add_argument("--api-key", help="API key for imagery provider")
    parser.add_argument("--zoom", type=int, default=15, help="Zoom level (default: 15 for airports, 17 for runways)")
    parser.add_argument("--size", default="640x640", help="Image size (default: 640x640)")
    parser.add_argument("--limit", type=int, help="Limit number of images to fetch")
    parser.add_argument("--runways", action="store_true", help="Fetch individual runway imagery")
    parser.add_argument("--all-types", action="store_true", help="Include small airports")
    parser.add_argument("--list", action="store_true", help="List airports that would be fetched")
    parser.add_argument("--db", default=DATABASE_PATH, help="Database path")

    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        print("Run fetch_ourairports.py first to create the database.")
        return

    conn = sqlite3.connect(args.db)

    if args.list:
        list_airports_for_imagery(conn, args.limit or 50)
        conn.close()
        return

    if not args.provider or not args.api_key:
        print("Airport Runway Imagery Fetcher")
        print("=" * 40)
        print("\nThis tool fetches satellite imagery for airports and runways.")
        print("\nSupported providers:")
        print("  - google: Google Maps Static API")
        print("  - mapbox: Mapbox Static Images API")
        print("  - bing: Bing Maps Static API")
        print("\nUsage examples:")
        print("  python fetch_imagery.py --provider google --api-key YOUR_KEY")
        print("  python fetch_imagery.py --provider google --api-key YOUR_KEY --limit 100")
        print("  python fetch_imagery.py --provider google --api-key YOUR_KEY --runways")
        print("  python fetch_imagery.py --list")
        print("\nTo get API keys:")
        print("  Google: https://developers.google.com/maps/documentation/maps-static/get-api-key")
        print("  Mapbox: https://docs.mapbox.com/help/getting-started/access-tokens/")
        print("  Bing: https://www.microsoft.com/en-us/maps/create-a-bing-maps-key")
        conn.close()
        return

    os.makedirs(IMAGERY_DIR, exist_ok=True)

    airport_types = ['large_airport', 'medium_airport']
    if args.all_types:
        airport_types.append('small_airport')

    if args.runways:
        zoom = args.zoom if args.zoom != 15 else 17  # Default to 17 for runways
        fetch_runway_imagery(conn, args.provider, args.api_key, zoom, args.size, args.limit)
    else:
        fetch_airport_imagery(conn, args.provider, args.api_key, args.zoom, args.size, args.limit, airport_types)

    conn.close()


if __name__ == "__main__":
    main()
