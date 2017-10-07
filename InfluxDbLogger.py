#!/usr/bin/env python

from twisted.internet import reactor, stdio
from twisted.protocols import basic

from datetime import datetime, timedelta
from influxdb import InfluxDBClient

HOST = "localhost"
PORT = 9001
USER = "pi"
PASSWORD = "pi"
DB_NAME = "sleep_monitor"

class ProcessInput(basic.LineReceiver):
    # This seemingly unused line is necessary to over-ride the delimiter
    # property of basic.LineReceiver which by default is '\r\n'. Do not
    # remove this!
    from os import linesep as delimiter

    def __init__(self, client):
        self.client = client
        self.session = 'production'
        self.runNo = datetime.utcnow().strftime('%Y%m%d%H%M')
        self.time = datetime.min

    def lineReceived(self, line):
        nums = [int(s) for s in line.split()]
        (spo2, bpm, motion, alarm) = nums

        time = datetime.utcnow()

        shouldLogNow = (spo2 > 0) or (motion != 0) or (time - lastLogTime > timedelta(minutes=10))
        if shouldLogNow:
            json_body = [{
                "measurement": self.session,
                "tags": {
                    "run": self.runNo,
                    },
                "time": time.ctime(),
                "fields": {
                    "spo2" : spo2,
                    "bpm" : bpm,
                    "motion": motion,
                    "alarm": alarm
                    }
                }]

            # Write JSON to InfluxDB
            self.client.write_points(json_body)
            self.lastLogTime = time

def createInfluxClient():
    client = InfluxDBClient(HOST, PORT, USER, PASSWORD, DB_NAME)

    dbs = client.get_list_database()
    for db in dbs:
        if db['name'] == DB_NAME:
            break
    else:
        client.create_database(DB_NAME)

    return client

def main():
    client = createInfluxClient()
    stdio.StandardIO(ProcessInput(client))
    reactor.run()

if __name__ == "__main__":
    main()
