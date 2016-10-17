#!/bin/sh

# Python requirements
sudo apt-get install -y python-imaging python-twisted \
    python-dateutil \
    python-autobahn

# Build and install Janus
mkdir -p ~/3p
cd ~/3p

sudo aptitude install -y libmicrohttpd-dev libjansson-dev \
	libnice-dev libssl-dev libsrtp-dev libsofia-sip-ua-dev \
	libglib2.0-dev libopus-dev libogg-dev libini-config-dev \
	libcollection-dev pkg-config gengetopt libtool automake dh-autoreconf

mkdir janus && cd janus
git clone https://github.com/meetecho/janus-gateway.git
cd janus-gateway
sh autogen.sh
./configure --disable-websockets --disable-data-channels \
	--disable-rabbitmq --disable-docs --disable-mqtt --prefix=/opt/janus
make
sudo make install
sudo make configs

sudo cp janus.plugin.streaming.cfg /opt/janus/etc/janus/janus.plugin.streaming.cfg
