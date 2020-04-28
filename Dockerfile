FROM python:3-alpine

RUN apk add --no-cache --virtual .build-deps \
        g++ \
        python3-dev \
        libxml2 \
        libxml2-dev \
    && apk add \
        libxslt-dev \
        su-exec

WORKDIR /opt/connectbox-prometheus
COPY resources/requirements/production.txt requirements.txt
RUN pip3 --no-cache-dir install -r requirements.txt \
    && apk del .build-deps

COPY . .
RUN python3 setup.py install

VOLUME /data
EXPOSE 9705

CMD ["/opt/connectbox-prometheus/docker-run.sh"]
