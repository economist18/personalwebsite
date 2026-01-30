#!/usr/bin/env python3
"""
Airport Runway Database Query Utility

Provides functions to query and export airport/runway data from the OurAirports database.
"""

import sqlite3
import json
import csv
import argparse
from typing import Optional, List, Dict, Any

DATABASE_PATH = "airport_runways.db"


def get_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    """Get database connection with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def search_airports(
    conn: sqlite3.Connection,
    query: Optional[str] = None,
    icao: Optional[str] = None,
    iata: Optional[str] = None,
    country: Optional[str] = None,
    airport_type: Optional[str] = None,
    min_runway_length_ft: Optional[float] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Search airports with various filters."""
    cursor = conn.cursor()

    sql = '''
        SELECT DISTINCT
            a.id, a.ident, a.iata_code, a.name,
            a.latitude, a.longitude, a.type, a.iso_country,
            a.municipality,
            COUNT(r.id) as runway_count,
            MAX(r.length_ft) as longest_runway_ft
        FROM airports a
        LEFT JOIN runways r ON a.id = r.airport_id
        WHERE 1=1
    '''
    params = []

    if query:
        sql += " AND (a.name LIKE ? OR a.ident LIKE ? OR a.iata_code LIKE ?)"
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])

    if icao:
        sql += " AND a.ident = ?"
        params.append(icao.upper())

    if iata:
        sql += " AND a.iata_code = ?"
        params.append(iata.upper())

    if country:
        sql += " AND a.iso_country = ?"
        params.append(country.upper())

    if airport_type:
        sql += " AND a.type = ?"
        params.append(airport_type)

    sql += " GROUP BY a.id"

    if min_runway_length_ft:
        sql += f" HAVING longest_runway_ft >= {min_runway_length_ft}"

    sql += f" ORDER BY runway_count DESC, longest_runway_ft DESC LIMIT {limit}"

    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def get_airport_details(conn: sqlite3.Connection, airport_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed airport information including all runways."""
    cursor = conn.cursor()

    # Get airport info
    cursor.execute('SELECT * FROM airports WHERE id = ?', (airport_id,))
    airport_row = cursor.fetchone()

    if not airport_row:
        return None

    airport = dict(airport_row)

    # Get runways
    cursor.execute('''
        SELECT id, le_ident, he_ident, length_ft, length_m, width_ft, width_m,
               surface, lighted, closed, le_heading_deg
        FROM runways WHERE airport_id = ?
        ORDER BY length_ft DESC
    ''', (airport_id,))
    airport['runways'] = [dict(row) for row in cursor.fetchall()]

    # Get imagery
    cursor.execute('''
        SELECT image_path, capture_date, imagery_source
        FROM runway_imagery WHERE airport_id = ?
    ''', (airport_id,))
    airport['imagery'] = [dict(row) for row in cursor.fetchall()]

    return airport


def get_airport_by_ident(conn: sqlite3.Connection, ident: str) -> Optional[Dict[str, Any]]:
    """Get airport by ICAO/ident code."""
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM airports WHERE ident = ?', (ident.upper(),))
    row = cursor.fetchone()
    if row:
        return get_airport_details(conn, row['id'])
    return None


def get_longest_runways(
    conn: sqlite3.Connection,
    limit: int = 50,
    exclude_water: bool = True,
    min_length_ft: float = 0
) -> List[Dict[str, Any]]:
    """Get the longest runways in the database."""
    cursor = conn.cursor()

    sql = '''
        SELECT
            r.id, r.le_ident, r.he_ident, r.length_ft, r.length_m,
            r.width_ft, r.surface, r.lighted,
            a.ident, a.iata_code, a.name as airport_name,
            a.iso_country, a.type as airport_type,
            a.latitude, a.longitude
        FROM runways r
        JOIN airports a ON r.airport_id = a.id
        WHERE r.length_ft IS NOT NULL AND r.length_ft > ?
    '''
    params = [min_length_ft]

    if exclude_water:
        sql += " AND a.type NOT IN ('seaplane_base') AND r.surface NOT LIKE '%WATER%'"

    sql += f" ORDER BY r.length_ft DESC LIMIT {limit}"

    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def get_airports_with_most_runways(conn: sqlite3.Connection, limit: int = 50) -> List[Dict[str, Any]]:
    """Get airports with the most runways."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            a.id, a.ident, a.iata_code, a.name,
            a.latitude, a.longitude, a.iso_country, a.type,
            COUNT(r.id) as runway_count,
            GROUP_CONCAT(r.le_ident || '/' || r.he_ident, ', ') as runway_designators,
            MAX(r.length_ft) as longest_runway_ft,
            SUM(r.length_ft) as total_runway_length_ft
        FROM airports a
        JOIN runways r ON a.id = r.airport_id
        WHERE a.type IN ('large_airport', 'medium_airport')
        GROUP BY a.id
        ORDER BY runway_count DESC, longest_runway_ft DESC
        LIMIT ?
    ''', (limit,))
    return [dict(row) for row in cursor.fetchall()]


def get_runways_by_country(conn: sqlite3.Connection, country_code: str) -> List[Dict[str, Any]]:
    """Get all runways in a country."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            a.ident, a.name, a.municipality,
            r.le_ident, r.he_ident, r.length_ft, r.surface
        FROM airports a
        JOIN runways r ON a.id = r.airport_id
        WHERE a.iso_country = ?
        ORDER BY r.length_ft DESC
    ''', (country_code.upper(),))
    return [dict(row) for row in cursor.fetchall()]


def get_statistics(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Get overall database statistics."""
    cursor = conn.cursor()
    stats = {}

    cursor.execute("SELECT COUNT(*) FROM airports")
    stats['total_airports'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM runways")
    stats['total_runways'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM airports WHERE ident IS NOT NULL")
    stats['airports_with_icao'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM airports WHERE iata_code IS NOT NULL AND iata_code != ''")
    stats['airports_with_iata'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM runway_imagery")
    stats['total_imagery'] = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(length_ft) FROM runways WHERE length_ft > 0")
    avg = cursor.fetchone()[0]
    stats['avg_runway_length_ft'] = avg
    stats['avg_runway_length_m'] = avg * 0.3048 if avg else None

    cursor.execute('''
        SELECT MAX(length_ft) FROM runways r
        JOIN airports a ON r.airport_id = a.id
        WHERE a.type NOT IN ('seaplane_base')
    ''')
    max_len = cursor.fetchone()[0]
    stats['max_runway_length_ft'] = max_len
    stats['max_runway_length_m'] = max_len * 0.3048 if max_len else None

    cursor.execute('''
        SELECT surface, COUNT(*) as count
        FROM runways
        WHERE surface IS NOT NULL AND surface != ''
        GROUP BY UPPER(surface)
        ORDER BY count DESC
        LIMIT 15
    ''')
    stats['surface_types'] = [dict(row) for row in cursor.fetchall()]

    cursor.execute('''
        SELECT type, COUNT(*) as count
        FROM airports
        GROUP BY type
        ORDER BY count DESC
    ''')
    stats['airport_types'] = [dict(row) for row in cursor.fetchall()]

    return stats


def export_to_csv(conn: sqlite3.Connection, output_file: str = "airports_export.csv"):
    """Export all airports and runways to CSV."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            a.ident as icao_code, a.iata_code, a.name,
            a.latitude, a.longitude, a.type as airport_type,
            a.iso_country, a.municipality,
            r.le_ident || '/' || r.he_ident as runway,
            r.length_ft, r.length_m, r.width_ft, r.surface,
            r.lighted, r.le_heading_deg as heading
        FROM airports a
        LEFT JOIN runways r ON a.id = r.airport_id
        ORDER BY a.ident, r.length_ft DESC
    ''')

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ICAO', 'IATA', 'Airport Name', 'Latitude', 'Longitude',
            'Type', 'Country', 'City', 'Runway', 'Length (ft)', 'Length (m)',
            'Width (ft)', 'Surface', 'Lighted', 'Heading'
        ])

        for row in cursor.fetchall():
            writer.writerow(row)

    print(f"Exported to {output_file}")


def export_to_json(conn: sqlite3.Connection, output_file: str = "airports_export.json"):
    """Export all airports and runways to JSON."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, ident, iata_code, name, latitude, longitude,
               type, iso_country, municipality
        FROM airports
        WHERE type IN ('large_airport', 'medium_airport', 'small_airport')
    ''')
    airports = []

    for airport_row in cursor.fetchall():
        airport = dict(airport_row)
        airport_id = airport.pop('id')

        cursor.execute('''
            SELECT le_ident, he_ident, length_ft, length_m, width_ft, surface, lighted
            FROM runways WHERE airport_id = ?
        ''', (airport_id,))
        airport['runways'] = [dict(r) for r in cursor.fetchall()]

        airports.append(airport)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(airports, f, indent=2)

    print(f"Exported {len(airports)} airports to {output_file}")


def export_to_geojson(conn: sqlite3.Connection, output_file: str = "airports.geojson"):
    """Export airports to GeoJSON format."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            a.ident, a.iata_code, a.name,
            a.latitude, a.longitude, a.type,
            COUNT(r.id) as runway_count,
            MAX(r.length_ft) as longest_runway
        FROM airports a
        LEFT JOIN runways r ON a.id = r.airport_id
        WHERE a.latitude IS NOT NULL AND a.longitude IS NOT NULL
        AND a.type IN ('large_airport', 'medium_airport', 'small_airport')
        GROUP BY a.id
    ''')

    features = []
    for row in cursor.fetchall():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row['longitude'], row['latitude']]
            },
            "properties": {
                "icao": row['ident'],
                "iata": row['iata_code'],
                "name": row['name'],
                "type": row['type'],
                "runway_count": row['runway_count'],
                "longest_runway_ft": row['longest_runway']
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f)

    print(f"Exported {len(features)} airports to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Query airport runway database")
    parser.add_argument("--db", default=DATABASE_PATH, help="Database path")
    parser.add_argument("--search", help="Search airports by name/code")
    parser.add_argument("--icao", help="Get airport by ICAO code")
    parser.add_argument("--iata", help="Search by IATA code")
    parser.add_argument("--country", help="Filter by country code (e.g., US, GB, DE)")
    parser.add_argument("--longest-runways", type=int, metavar="N", help="Show N longest runways")
    parser.add_argument("--most-runways", type=int, metavar="N", help="Show airports with most runways")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--export-csv", metavar="FILE", help="Export to CSV")
    parser.add_argument("--export-json", metavar="FILE", help="Export to JSON")
    parser.add_argument("--export-geojson", metavar="FILE", help="Export to GeoJSON")

    args = parser.parse_args()

    conn = get_connection(args.db)

    if args.stats:
        stats = get_statistics(conn)
        print("\n=== Database Statistics ===")
        print(f"Total airports: {stats['total_airports']:,}")
        print(f"Total runways: {stats['total_runways']:,}")
        print(f"Airports with ICAO: {stats['airports_with_icao']:,}")
        print(f"Airports with IATA: {stats['airports_with_iata']:,}")
        print(f"Total imagery: {stats['total_imagery']:,}")
        if stats['avg_runway_length_ft']:
            print(f"Average runway length: {stats['avg_runway_length_ft']:.0f}ft ({stats['avg_runway_length_m']:.0f}m)")
        if stats['max_runway_length_ft']:
            print(f"Longest paved runway: {stats['max_runway_length_ft']:.0f}ft ({stats['max_runway_length_m']:.0f}m)")
        print("\nAirport types:")
        for t in stats['airport_types']:
            print(f"  {t['type']}: {t['count']:,}")
        print("\nSurface types:")
        for s in stats['surface_types']:
            print(f"  {s['surface']}: {s['count']:,}")

    elif args.search:
        results = search_airports(conn, query=args.search, country=args.country)
        print(f"\nFound {len(results)} airports matching '{args.search}':\n")
        for a in results:
            iata_str = f" / {a['iata_code']}" if a['iata_code'] else ""
            print(f"  {a['ident']}{iata_str} - {a['name']}")
            print(f"    Location: {a['latitude']:.4f}, {a['longitude']:.4f} ({a['iso_country']})")
            print(f"    Type: {a['type']}, Runways: {a['runway_count']}, Longest: {a['longest_runway_ft'] or 'N/A'}ft")
            print()

    elif args.icao:
        airport = get_airport_by_ident(conn, args.icao)
        if airport:
            print(f"\n=== {airport['ident']} - {airport['name']} ===")
            print(f"IATA: {airport['iata_code'] or 'N/A'}")
            print(f"Type: {airport['type']}")
            print(f"Location: {airport['latitude']:.6f}, {airport['longitude']:.6f}")
            print(f"Country: {airport['iso_country']}")
            print(f"City: {airport['municipality'] or 'N/A'}")
            print(f"\nRunways ({len(airport['runways'])}):")
            for r in airport['runways']:
                rwy_name = f"{r['le_ident']}/{r['he_ident']}" if r['le_ident'] and r['he_ident'] else "Unknown"
                length_m = f"{r['length_m']:.0f}m" if r['length_m'] else "N/A"
                print(f"  {rwy_name}: {r['length_ft']:.0f}ft ({length_m}) x {r['width_ft'] or '?'}ft")
                print(f"    Surface: {r['surface'] or 'Unknown'}, Lighted: {'Yes' if r['lighted'] else 'No'}")
        else:
            print(f"Airport {args.icao} not found")

    elif args.iata:
        results = search_airports(conn, iata=args.iata)
        if results:
            airport = get_airport_details(conn, results[0]['id'])
            print(f"\n=== {airport['ident']} / {airport['iata_code']} - {airport['name']} ===")
            print(f"Location: {airport['latitude']:.6f}, {airport['longitude']:.6f}")
            print(f"Country: {airport['iso_country']}")
            print(f"\nRunways ({len(airport['runways'])}):")
            for r in airport['runways']:
                rwy_name = f"{r['le_ident']}/{r['he_ident']}" if r['le_ident'] and r['he_ident'] else "Unknown"
                print(f"  {rwy_name}: {r['length_ft']:.0f}ft ({r['length_m']:.0f}m)")
        else:
            print(f"Airport with IATA code {args.iata} not found")

    elif args.longest_runways:
        runways = get_longest_runways(conn, args.longest_runways, exclude_water=True)
        print(f"\n=== Top {args.longest_runways} Longest Runways (excluding seaplane bases) ===\n")
        for i, r in enumerate(runways, 1):
            rwy_name = f"{r['le_ident']}/{r['he_ident']}" if r['le_ident'] and r['he_ident'] else "Unknown"
            print(f"{i:3}. {r['length_ft']:,.0f}ft ({r['length_m']:,.0f}m)")
            print(f"     {r['ident']} ({r['iata_code'] or '-'}) {r['airport_name'][:50]} ({r['iso_country']})")
            print(f"     Runway {rwy_name}, Surface: {r['surface'] or 'Unknown'}")
            print()

    elif args.most_runways:
        airports = get_airports_with_most_runways(conn, args.most_runways)
        print(f"\n=== Airports with Most Runways (Large/Medium airports) ===\n")
        for i, a in enumerate(airports, 1):
            print(f"{i:3}. {a['ident']} ({a['iata_code'] or '-'}) - {a['name']}")
            print(f"     {a['runway_count']} runways, Longest: {a['longest_runway_ft']:,.0f}ft")
            print(f"     Runways: {a['runway_designators'][:80]}...")
            print()

    elif args.export_csv:
        export_to_csv(conn, args.export_csv)

    elif args.export_json:
        export_to_json(conn, args.export_json)

    elif args.export_geojson:
        export_to_geojson(conn, args.export_geojson)

    else:
        # Default: show summary
        stats = get_statistics(conn)
        print("\n=== Airport Runway Database ===")
        print(f"Source: OurAirports (https://ourairports.com)")
        print(f"Total airports: {stats['total_airports']:,}")
        print(f"Total runways: {stats['total_runways']:,}")
        print(f"Airports with IATA code: {stats['airports_with_iata']:,}")
        print("\nUse --help to see query options")
        print("\nExamples:")
        print("  python query_database.py --stats")
        print("  python query_database.py --search 'JFK'")
        print("  python query_database.py --icao KJFK")
        print("  python query_database.py --iata LAX")
        print("  python query_database.py --longest-runways 20")
        print("  python query_database.py --most-runways 20")
        print("  python query_database.py --country US --search 'international'")

    conn.close()


if __name__ == "__main__":
    main()
