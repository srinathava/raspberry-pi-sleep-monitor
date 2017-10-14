#!/usr/bin/python3

import requests
import json
import os
import sys

from influxdb import InfluxDBClient

HOST = "localhost"
PORT = 9001
USER = "pi"
PASSWORD = "pi"
DB_NAME = "sleep_monitor"

def get(req):
    return requests.get('http://localhost:3000%s' % req, auth=('admin', 'admin'))

def post(req, **kwargs):
    return requests.post('http://localhost:3000%s' % req, auth=('admin', 'admin'), **kwargs)

def printResponse(prefix, r):
    if r.status_code == 200:
        print('%s: success!' % prefix)
    else:
        print('%s: failed! (%d)' % (prefix, r.status_code))
    json.dump(r.json(), sys.stdout, indent=2)

def setupGrafana():
    if not get('/api/datasources/name/sleep_monitor'):
        print('Creating sleep_monitor datasource for grafana')
        s = open('grafana_datasource.json').read()
        s = s % {'hostname': os.uname().nodename}
        js = json.loads(s)
        r = post('/api/datasources', json=js)
        printResponse('Datasource creation', r)
    else:
        print('Data source is already set up.')

    print('Creating sleep_monitor dashboard for grafana')
    js = json.load(open('grafana_dashboard.json'))
    js['inputs'] = []
    js['overwrite'] = True
    if 'meta' in js:
        del js['meta']
    js['dashboard']['id'] = None
    r = post('/api/dashboards/import', json=js)
    printResponse('Dashboard creation', r)

def setupInfluxDb():
    client = InfluxDBClient(HOST, PORT, USER, PASSWORD, DB_NAME)

    client.create_database('sleep_monitor')
    client.create_retention_policy('four_weeks', '4w', '1', default=True)

    client.create_database('_internal')
    retention_policies = client.get_list_retention_policies('_internal')
    for rp in retention_policies:
        if rp['name'] == 'monitor':
            client.drop_retention_policy('monitor', database='_internal')
            break

    client.create_retention_policy('monitor', '2h', '1', database='_internal', default=True)


setupGrafana()
setupInfluxDb()
