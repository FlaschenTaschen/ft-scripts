# 511.org transit API: curl guide for nearby bus stops and arrival estimates

This guide shows how to use `curl` with the 511.org transit APIs to:

1. find stop and operator data you can use for a coordinate lookup
2. get the nearest bus stops to a latitude/longitude
3. get real-time arrival estimates for a specific stop

It uses placeholders so you can drop in your own API key and coordinates later.

---

## Important note about “nearby stops”

The 511.org transit docs describe:

- an **Operators** endpoint for listing operators, with `api_key` required and `operator_id` optional
- a **Stops** endpoint for listing stops for a specific `operator_id`
- a **GTFS DataFeed** endpoint that can download a full agency feed or the regional feed by using `operator_id=RG`
- a **StopMonitoring** endpoint for real-time predictions, which requires `agency` and accepts an optional `stopCode` parameter

The published transit docs do **not** document a direct “give me stops near this latitude/longitude” query parameter on the Stops or StopPlaces endpoints. In practice, the most reliable curl-based workflow is to download stop data from 511.org and then filter it locally by coordinates. citeturn677516view0turn665353view0turn665353view1turn154208view0turn890592view0

---

## Variables you will replace

Set these shell variables first:

```bash
API_KEY="YOUR_511_API_KEY"
LAT="37.7749"
LON="-122.4194"
RADIUS_KM="0.5"
STOP_CODE="YOUR_STOP_CODE"
AGENCY="YOUR_AGENCY_CODE"
```

For 511.org transit data:

- `operator_id` is used by static endpoints like **stops** and **datafeeds**
- `agency` is used by real-time endpoints like **StopMonitoring**
- the docs show operator and agency identifiers can be discovered from 511.org operator-related endpoints, and the regional GTFS feed is available with `operator_id=RG` for GTFS download workflows. citeturn677516view0turn677516view1turn154208view0

---

## Option A: discover operators first

If you need to inspect available operators:

```bash
curl -s "http://api.511.org/transit/operators?api_key=${API_KEY}&format=json"
```

The Operators endpoint is a documented GET endpoint, defaults to JSON when `format` is omitted, and supports optional `operator_id` filtering. citeturn677516view0

If you want the GTFS operator list, including the regional feed entry `RG`:

```bash
curl -s "http://api.511.org/transit/gtfsoperators?api_key=${API_KEY}&format=json"
```

The GTFS operator list endpoint documents that `RG` represents the regional GTFS feed. citeturn677516view1

---

## Option B: get nearby bus stops from the regional GTFS feed

This is the best curl-only pattern when you want “nearby stops by coordinates” across the Bay Area.

### 1) Download the regional GTFS zip from 511.org

```bash
curl -L -o regional_gtfs.zip \
  "http://api.511.org/transit/datafeeds?api_key=${API_KEY}&operator_id=RG"
```

The GTFS DataFeed endpoint supports `operator_id`, and the docs state that `operator_id=RG` downloads the regional GTFS dataset. citeturn890592view0

### 2) Extract `stops.txt`

```bash
unzip -o regional_gtfs.zip stops.txt
```

### 3) Return the nearest bus stops to your coordinates

This example uses `awk` to compute an approximate distance in kilometers and returns the 10 closest stops. It assumes the standard GTFS `stops.txt` columns include `stop_id`, `stop_name`, `stop_lat`, and `stop_lon`.

```bash
awk -F, -v lat="$LAT" -v lon="$LON" '
BEGIN { OFS="," }
NR==1 {
  for (i=1; i<=NF; i++) {
    if ($i=="stop_id") id=i;
    if ($i=="stop_name") name=i;
    if ($i=="stop_lat") slat=i;
    if ($i=="stop_lon") slon=i;
    if ($i=="location_type") loc=i;
  }
  next
}
{
  # skip rows missing coordinates
  if ($(slat)=="" || $(slon)=="") next

  # optional: keep likely boarding stops only
  if (loc && $(loc)!="" && $(loc)!="0") next

  dlat = ($(slat)-lat) * 111.32
  dlon = ($(slon)-lon) * 111.32 * cos(lat * 3.1415926535 / 180)
  dist = sqrt(dlat*dlat + dlon*dlon)

  print dist, $(id), $(name), $(slat), $(slon)
}
' stops.txt | sort -t, -k1,1n | head -10
```

Why this works:

- the 511.org GTFS DataFeed endpoint gives you GTFS files, including stop data, for either an operator or the regional feed
- the transit spec describes stop resources as carrying WGS84 latitude and longitude values
- the StopMonitoring endpoint uses a numeric stop code for predictions, so the nearby-stop workflow usually ends by selecting a stop and then querying predictions for that stop’s code. citeturn890592view0turn665353view0turn154208view0

### 4) Keep only stops within a radius

This version filters to a radius in kilometers.

```bash
awk -F, -v lat="$LAT" -v lon="$LON" -v radius="$RADIUS_KM" '
BEGIN { OFS="," }
NR==1 {
  for (i=1; i<=NF; i++) {
    if ($i=="stop_id") id=i;
    if ($i=="stop_name") name=i;
    if ($i=="stop_lat") slat=i;
    if ($i=="stop_lon") slon=i;
    if ($i=="location_type") loc=i;
  }
  next
}
{
  if ($(slat)=="" || $(slon)=="") next
  if (loc && $(loc)!="" && $(loc)!="0") next

  dlat = ($(slat)-lat) * 111.32
  dlon = ($(slon)-lon) * 111.32 * cos(lat * 3.1415926535 / 180)
  dist = sqrt(dlat*dlat + dlon*dlon)

  if (dist <= radius) {
    print dist, $(id), $(name), $(slat), $(slon)
  }
}
' stops.txt | sort -t, -k1,1n
```

---

## Option C: get stops for a specific operator

If you already know the operator and only want that operator’s stop inventory:

```bash
OPERATOR_ID="SF"

curl -s \
  "http://api.511.org/transit/stops?api_key=${API_KEY}&operator_id=${OPERATOR_ID}&format=json"
```

The Stops endpoint requires `operator_id` and `api_key`. It also supports optional `line_id`, `direction_id`, `pattern_id`, and `include_stop_areas`. The documented stop payload includes longitude and latitude in WGS84. citeturn665353view0

Because the official parameters shown for this endpoint do not include a coordinate search filter, you would still need to filter the returned stop list locally if your input is a latitude/longitude. citeturn665353view0

---

## Get real-time arrival estimates for a specific stop

511.org’s real-time prediction endpoint is **StopMonitoring**.

### Predictions for one stop

```bash
curl -s \
  "http://api.511.org/transit/StopMonitoring?api_key=${API_KEY}&agency=${AGENCY}&stopCode=${STOP_CODE}&format=json"
```

The StopMonitoring endpoint is documented as a GET endpoint with:

- `api_key` required
- `agency` required
- `stopCode` optional
- `format` optional, with JSON as the default if omitted. citeturn842768search1turn154208view0

The docs describe `stopCode` as the numeric stop code for the stop to be monitored, and note that if `stopCode` is omitted, the API returns information for all stops with location type `0`, which can be slower. citeturn154208view0

### Pretty-print the JSON response with jq

```bash
curl -s \
  "http://api.511.org/transit/StopMonitoring?api_key=${API_KEY}&agency=${AGENCY}&stopCode=${STOP_CODE}&format=json" \
  | jq
```

### Basic extraction of upcoming arrivals with jq

The exact JSON path can vary by agency feed content, but this command is a good starting point for the standard SIRI StopMonitoring response shape:

```bash
curl -s \
  "http://api.511.org/transit/StopMonitoring?api_key=${API_KEY}&agency=${AGENCY}&stopCode=${STOP_CODE}&format=json" \
  | jq '.. | objects | select(has("MonitoredVehicleJourney")) | {
      line: .MonitoredVehicleJourney.LineRef,
      destination: .MonitoredVehicleJourney.DestinationName,
      aimedArrival: .MonitoredCall.AimedArrivalTime,
      expectedArrival: .MonitoredCall.ExpectedArrivalTime,
      aimedDeparture: .MonitoredCall.AimedDepartureTime,
      expectedDeparture: .MonitoredCall.ExpectedDepartureTime
    }'
```

The transit docs explicitly identify StopMonitoring as the real-time prediction API and describe its response as a SIRI-style service-delivery payload for monitored visits at a stop. citeturn842768search1turn154208view0

---

## Fast troubleshooting

### Invalid API key

511.org documents `401 Unauthorized` for an invalid API key on these transit endpoints. citeturn677516view0turn665353view0turn665353view1turn154208view0turn890592view0

### Resource not found

511.org documents `404 Not found` when a resource cannot be identified or located. citeturn677516view0turn665353view0turn665353view1turn154208view0turn890592view0

### Slow StopMonitoring response

The StopMonitoring docs note that omitting `stopCode` can make the response take more than 5–7 seconds because the API may return all stops with location type `0`. citeturn154208view0

---

## Minimal commands to customize later

### Nearby stops from coordinates

```bash
API_KEY="YOUR_511_API_KEY"
LAT="YOUR_LATITUDE"
LON="YOUR_LONGITUDE"

curl -L -o regional_gtfs.zip \
  "http://api.511.org/transit/datafeeds?api_key=${API_KEY}&operator_id=RG"
unzip -o regional_gtfs.zip stops.txt
awk -F, -v lat="$LAT" -v lon="$LON" '
BEGIN { OFS="," }
NR==1 {
  for (i=1; i<=NF; i++) {
    if ($i=="stop_id") id=i;
    if ($i=="stop_name") name=i;
    if ($i=="stop_lat") slat=i;
    if ($i=="stop_lon") slon=i;
  }
  next
}
{
  if ($(slat)=="" || $(slon)=="") next
  dlat = ($(slat)-lat) * 111.32
  dlon = ($(slon)-lon) * 111.32 * cos(lat * 3.1415926535 / 180)
  dist = sqrt(dlat*dlat + dlon*dlon)
  print dist, $(id), $(name), $(slat), $(slon)
}
' stops.txt | sort -t, -k1,1n | head -10
```

### Arrival estimates for one stop

```bash
API_KEY="YOUR_511_API_KEY"
AGENCY="YOUR_AGENCY_CODE"
STOP_CODE="YOUR_STOP_CODE"

curl -s \
  "http://api.511.org/transit/StopMonitoring?api_key=${API_KEY}&agency=${AGENCY}&stopCode=${STOP_CODE}&format=json" \
  | jq
```

---

## When you send me your values

Send me:

- your `API_KEY`
- the target `LAT` and `LON`
- optionally a preferred radius
- optionally the operator or agency you care about most
- any stop code you already know

Then I can turn this into a fully filled-in set of ready-to-run commands.
