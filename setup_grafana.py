#!/usr/bin/python3

import requests
import json
import os
import sys

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
