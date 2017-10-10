#!/usr/bin/env bash

CURDIR=`pwd`

if [ -f "/etc/init.d/influxdb" ]; then
    echo "Influx DB already seems to be installed."
else
    sudo apt-get install influxdb influxdb-client
    sudo cp influxdb.conf /etc/influxdb/influxdb.conf
    sudo systemctl enable influxdb
    sudo systemctl restart influxdb
fi

if [ -f "/etc/init.d/grafana-server" ]; then
    echo "Grafana already seems to be installed."
else
    cd /tmp
    wget https://bintray.com/fg2it/deb/download_file?file_path=main%2Fg%2Fgrafana_4.5.2_armhf.deb -O grafana_4.5.2_armhf.deb
    sudo dpkg -i grafana_4.5.2_armhf.deb

    sudo cp ${CURDIR}/grafana.ini /etc/grafana/grafana.ini
    sudo systemctl enable grafana-server
    sudo systemctl start grafana-server
fi

sudo apt-get install python3-requests python3-influxdb

cd ${CURDIR}

python3 setup_grafana.py

sudo systemctl restart influxdb

