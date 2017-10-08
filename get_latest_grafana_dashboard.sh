#!/usr/bin/env bash

curl -s -u admin:admin -X GET \
    http://localhost:3000/api/dashboards/db/sleep-monitor | json_pp > grafana_dashboard.json
