#!/bin/sh

if [ ! -f /data/config.yml ]; then
    echo "Config file not found. Copying example to /data/config.yml..."
    cp /opt/connectbox-prometheus/config.yml /data/config.yml
    echo "Done. Please modify the config file to your liking and restart the container."
    exit
fi

chown -R nobody /data
exec su-exec nobody connectbox_exporter /data/config.yml
