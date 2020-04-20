FROM python:3-alpine

RUN apk add --no-cache --virtual .build-deps \
        g++ \
        python3-dev \
        libxml2 \
        libxml2-dev \
    && apk add \
        libxslt-dev \
        su-exec \
    && pip3 --no-cache-dir install connectbox-prometheus \
    && apk del .build-deps

COPY docker-run.sh config.yml /opt/connectbox-prometheus/
VOLUME /data
EXPOSE 9705

CMD ["/opt/connectbox-prometheus/docker-run.sh"]
