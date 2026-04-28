#!/bin/bash

LOCAL_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if ($i=="src") print $(i+1)}')
URL="http://${LOCAL_IP:-127.0.0.1}:5000/make_measurement"

curl -s -X POST "$URL"
