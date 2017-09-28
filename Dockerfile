FROM alpine:3.6

LABEL maintainer="Steffen Moen <smoen@vmware.com>"

EXPOSE 443

# Do installing/building first, so we can leverage dockers layer by layer caching
COPY root/requirements.txt /
RUN set -ex \
    && apk update \
    && apk add python3 nginx git curl \
    && mkdir /run/nginx \

    # Installing build dependencies, then python packages, last cleanup.
    && apk add --no-cache --virtual .build-deps \
        gcc musl-dev linux-headers python3-dev libffi-dev libressl-dev \
    && pip3 install -r /requirements.txt \
    && apk del .build-deps \

    # Installing s6 init (pid 1)
    && curl -L -s https://github.com/just-containers/s6-overlay/releases/download/v1.18.1.5/s6-overlay-amd64.tar.gz | tar xvzf - -C /

# Copy over the rest, this will be quick, and the previous RUN layer wont run unless we change the requirements.txt as well
COPY root /

ENTRYPOINT ["/init"]
