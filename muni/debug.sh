#!/bin/zsh

export MUNI_AGENCY="SF"

curl -s \
  "http://api.511.org/transit/StopMonitoring?api_key=${SF_TRANSIT_API_KEY}&agency=${MUNI_AGENCY}&stopCode=14352&format=json" \
  | gunzip | jq . | head -50
