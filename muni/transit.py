#!/usr/bin/python3
"""
Transit library for finding MUNI bus stops by location and getting arrivals.
Provides functions to work with 511.org API and local coordinates.json.

Usage:
    import transit
    stops = transit.find_stops_within_radius("Sequoia Fabrica", radius_miles=0.5)
    for stop in stops:
        arrivals = transit.get_arrivals_for_stop(stop['code'])
"""

import os
import json
import gzip
import requests
import time
from datetime import datetime, timezone
from math import sqrt, cos, pi
import tempfile
import subprocess
import shutil

API_KEY = os.getenv("SF_TRANSIT_API_KEY")
AGENCY = os.getenv("MUNI_AGENCY", "SF")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.expanduser("~/.cache/muni")
CACHE_FILE = os.path.join(CACHE_DIR, "arrivals.json")
CACHE_MAX_AGE_SECONDS = 120  # 2 minutes
GTFS_CACHE_FILE = os.path.join(CACHE_DIR, "stops.txt")
GTFS_MAX_AGE_SECONDS = 86400  # 24 hours

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================================================================
# Cache Functions
# ============================================================================

def _get_cache():
    """Load cache from file"""
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cache(cache):
    """Save cache to file"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass

def _is_cache_fresh(cache_time):
    """Check if cache is less than 2 minutes old"""
    age = time.time() - cache_time
    return age < CACHE_MAX_AGE_SECONDS

def _is_gtfs_cache_fresh():
    """Check if GTFS cache exists and is less than 24 hours old"""
    if not os.path.exists(GTFS_CACHE_FILE):
        return False
    age = time.time() - os.path.getmtime(GTFS_CACHE_FILE)
    return age < GTFS_MAX_AGE_SECONDS

def _adjust_arrivals_by_cache_age(arrivals, cache_age_seconds):
    """Subtract cache age from arrival times to show accurate estimates"""
    adjusted = []
    for arr in arrivals:
        adjusted_minutes = arr['minutes_until'] - (cache_age_seconds / 60)
        adjusted.append({
            'line': arr['line'],
            'destination': arr['destination'],
            'minutes_until': max(0, int(adjusted_minutes))  # Don't show negative times
        })
    return adjusted

# ============================================================================
# Coordinate and Location Functions
# ============================================================================

def load_coordinates():
    """Load locations from coordinates.json"""
    coords_file = os.path.join(SCRIPT_DIR, "coordinates.json")

    if not os.path.exists(coords_file):
        raise FileNotFoundError(f"coordinates.json not found in {SCRIPT_DIR}")

    with open(coords_file, 'r') as f:
        return json.load(f)

def find_location(location_name):
    """
    Find a location by name in coordinates.json

    Args:
        location_name: Name of location (case-insensitive)

    Returns:
        dict with 'latitude' and 'longitude' keys, or None if not found
    """
    locations = load_coordinates()

    for loc in locations:
        if loc.get('name', '').lower() == location_name.lower():
            return {
                'latitude': loc.get('latitude'),
                'longitude': loc.get('longitude'),
                'name': loc.get('name')
            }

    return None

# ============================================================================
# GTFS Functions
# ============================================================================

def download_gtfs(tmpdir):
    """Download and extract regional GTFS data, using cache if available"""
    # Check if cached stops.txt exists and is fresh
    if _is_gtfs_cache_fresh():
        return GTFS_CACHE_FILE

    # Cache is stale or missing, download fresh data
    if not API_KEY:
        raise ValueError("SF_TRANSIT_API_KEY environment variable not set")

    zip_path = os.path.join(tmpdir, "regional_gtfs.zip")

    url = f"http://api.511.org/transit/datafeeds?api_key={API_KEY}&operator_id=RG"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(zip_path, 'wb') as f:
        f.write(response.content)

    # Extract stops.txt
    result = subprocess.run(
        ['unzip', '-q', '-o', zip_path, 'stops.txt', '-d', tmpdir],
        capture_output=True
    )

    stops_file = os.path.join(tmpdir, 'stops.txt')
    if not os.path.exists(stops_file):
        raise FileNotFoundError("Failed to extract stops.txt from GTFS")

    # Cache the stops.txt file in persistent location
    try:
        shutil.copy(stops_file, GTFS_CACHE_FILE)
    except Exception:
        pass  # If caching fails, continue anyway

    return GTFS_CACHE_FILE

def parse_response(response_content):
    """Parse HTTP response that may be gzip-compressed or have BOM"""
    if response_content.startswith(b'\x1f\x8b'):
        content = gzip.decompress(response_content)
    else:
        content = response_content

    text = content.decode('utf-8').lstrip('\ufeff')
    return json.loads(text)

# ============================================================================
# Stop Finding Functions
# ============================================================================

def find_stops_within_radius(location_name, radius_miles=0.25):
    """
    Find all MUNI stops within a radius of a named location

    Args:
        location_name: Name of location from coordinates.json
        radius_miles: Search radius in miles (default 0.25)

    Returns:
        list of dicts with keys: code, name, latitude, longitude, distance_km
        Sorted by distance (nearest first)
    """
    location = find_location(location_name)
    if not location:
        raise ValueError(f"Location '{location_name}' not found in coordinates.json")

    lat = location['latitude']
    lon = location['longitude']
    radius_km = radius_miles * 1.60934

    tmpdir = tempfile.mkdtemp()
    try:
        stops_file = download_gtfs(tmpdir)
        return find_stops_by_coordinates(lat, lon, radius_km, stops_file)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def find_stops_by_coordinates(latitude, longitude, radius_km, stops_file=None):
    """
    Find all stops within a radius of given coordinates

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        radius_km: Search radius in kilometers
        stops_file: Path to stops.txt (downloads GTFS if not provided)

    Returns:
        list of dicts sorted by distance
    """
    if stops_file is None:
        tmpdir = tempfile.mkdtemp()
        try:
            stops_file = download_gtfs(tmpdir)
            return _parse_stops_by_radius(latitude, longitude, radius_km, stops_file)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        return _parse_stops_by_radius(latitude, longitude, radius_km, stops_file)

def _parse_stops_by_radius(latitude, longitude, radius_km, stops_file):
    """Parse stops.txt and filter by distance"""
    stops = []

    with open(stops_file, 'r') as f:
        # Read header
        header = f.readline().strip().split(',')
        id_idx = header.index('stop_id')
        name_idx = header.index('stop_name')
        lat_idx = header.index('stop_lat')
        lon_idx = header.index('stop_lon')

        # Parse lines
        for line in f:
            fields = line.strip().split(',')

            if len(fields) <= max(id_idx, name_idx, lat_idx, lon_idx):
                continue

            try:
                stop_lat = float(fields[lat_idx])
                stop_lon = float(fields[lon_idx])
            except (ValueError, IndexError):
                continue

            # Calculate distance
            dlat = (stop_lat - latitude) * 111.32
            dlon = (stop_lon - longitude) * 111.32 * cos(latitude * pi / 180)
            dist = sqrt(dlat*dlat + dlon*dlon)

            # Check if within radius
            if dist <= radius_km:
                stops.append({
                    'code': fields[id_idx],
                    'name': fields[name_idx],
                    'latitude': stop_lat,
                    'longitude': stop_lon,
                    'distance_km': round(dist, 3)
                })

    # Sort by distance
    stops.sort(key=lambda x: x['distance_km'])
    return stops

# ============================================================================
# Arrival Functions
# ============================================================================

def get_arrivals_for_stop(stop_code, max_arrivals=3, max_retries=3):
    """
    Get next arrivals for a stop with automatic retry on rate limiting
    Uses cache to avoid hitting rate limit (60 requests/hour from 511.org)

    Args:
        stop_code: Stop code number
        max_arrivals: Maximum number of arrivals to return
        max_retries: Maximum number of retries on rate limit (429) errors

    Returns:
        list of dicts with keys: line, destination, minutes_until
        or empty list if no arrivals available
    """
    if not API_KEY:
        raise ValueError("SF_TRANSIT_API_KEY environment variable not set")

    # Check cache first
    cache = _get_cache()
    if stop_code in cache:
        cache_entry = cache[stop_code]
        cache_time = cache_entry.get('timestamp', 0)
        if _is_cache_fresh(cache_time):
            # Cache is fresh, use it
            cached_arrivals = cache_entry.get('arrivals', [])
            cache_age = time.time() - cache_time
            return _adjust_arrivals_by_cache_age(cached_arrivals, cache_age)

    # Cache is stale or missing, fetch from API
    url = f"http://api.511.org/transit/StopMonitoring?api_key={API_KEY}&agency={AGENCY}&stopCode={stop_code}&format=json"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
                else:
                    return []

            response.raise_for_status()
            data = parse_response(response.content)
            arrivals = _parse_arrivals(data, max_arrivals)

            # Save to cache
            cache[stop_code] = {
                'timestamp': time.time(),
                'arrivals': arrivals
            }
            _save_cache(cache)

            return arrivals

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return []
            # Brief backoff on other request errors
            time.sleep(0.5)

    return []

def _parse_arrivals(response_data, max_arrivals=3):
    """Parse StopMonitoring response and extract arrivals"""
    arrivals = []

    try:
        now = datetime.now(timezone.utc)

        service_delivery = response_data.get("ServiceDelivery", {})
        stop_monitoring_delivery = service_delivery.get("StopMonitoringDelivery", {})
        monitored_stops = stop_monitoring_delivery.get("MonitoredStopVisit", [])

        for visit in monitored_stops:
            journey = visit.get("MonitoredVehicleJourney", {})
            line_ref = journey.get("LineRef", "?")
            dest = journey.get("DestinationName", "?")
            monitored_call = journey.get("MonitoredCall", {})
            expected_arrival = monitored_call.get("ExpectedArrivalTime", "")

            if expected_arrival:
                arrival_time = datetime.fromisoformat(expected_arrival.replace('Z', '+00:00'))
                minutes_until = int((arrival_time - now).total_seconds() / 60)

                arrivals.append({
                    'line': line_ref,
                    'destination': dest,
                    'minutes_until': minutes_until
                })

                if len(arrivals) >= max_arrivals:
                    break
    except Exception as e:
        print(f"Error parsing arrivals: {e}")

    return arrivals

def get_stop_name(stop_code):
    """
    Get stop name from StopMonitoring response

    Args:
        stop_code: Stop code number

    Returns:
        Stop name string, or None if not available
    """
    if not API_KEY:
        raise ValueError("SF_TRANSIT_API_KEY environment variable not set")

    url = f"http://api.511.org/transit/StopMonitoring?api_key={API_KEY}&agency={AGENCY}&stopCode={stop_code}&format=json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = parse_response(response.content)

        service_delivery = data.get("ServiceDelivery", {})
        stop_monitoring_delivery = service_delivery.get("StopMonitoringDelivery", {})
        monitored_stops = stop_monitoring_delivery.get("MonitoredStopVisit", [])

        if monitored_stops:
            journey = monitored_stops[0].get("MonitoredVehicleJourney", {})
            monitored_call = journey.get("MonitoredCall", {})
            return monitored_call.get("StopPointName")
    except Exception as e:
        print(f"Error fetching stop name for {stop_code}: {e}")

    return None
