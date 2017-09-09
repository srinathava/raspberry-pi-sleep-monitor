#!/bin/sh

CURDIR=`pwd`

# Python requirements
sudo apt-get install -y python-imaging python-twisted \
    python-dateutil \
    python-autobahn

# Install gstreamer
sudo apt-get install gstreamer-1.0

# Build and install Janus
sudo aptitude install -y libmicrohttpd-dev libjansson-dev \
	libnice-dev libssl-dev libsrtp-dev libsofia-sip-ua-dev \
	libglib2.0-dev libopus-dev libogg-dev libini-config-dev \
	libcollection-dev pkg-config gengetopt libtool automake dh-autoreconf \
	libsrtp2-dev

mkdir -p ~/3p
cd ~/3p
mkdir -p janus && cd janus

if [ -d "janus-gateway" ]
then
	cd janus-gateway
	git pull
else
	git clone https://github.com/meetecho/janus-gateway.git
	cd janus-gateway
fi

sh autogen.sh
./configure --disable-websockets --disable-data-channels \
	--disable-rabbitmq --disable-docs --disable-mqtt --prefix=/opt/janus
make
sudo make install
sudo make configs

cd ${CURDIR}

sudo cp janus.plugin.streaming.cfg /opt/janus/etc/janus/janus.plugin.streaming.cfg

# sudo cp ./init.d/sleep-monitor /etc/init.d/
sudo sed -i "/exit 0/ i modprobe bcm2835-v4l2\n\
	${CURDIR}/init.d/sleepmonitor start\n\
	" /etc/rc.local
