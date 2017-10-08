#!/usr/bin/env bash

curl -s -u admin:admin -X GET \
    http://localhost:3000/api/dashboards/db/sleep-monitor \
    | json_pp  --json_opt=canonical,pretty > grafana_dashboard.json
