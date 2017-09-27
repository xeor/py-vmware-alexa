FROM alpine:3.6

LABEL maintainer="Steffen Moen <smoen@vmware.com>"

EXPOSE 443

# Do installing/building first, so we can leverage dockers layer by layer
# caching

# py3-zope-interface.
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

COPY root /

#COPY . /srv/avss/appdata
#RUN mv configs/nginx.conf /etc/nginx/nginx.conf
#RUN mv configs/avss.ini /etc/uwsgi.d/avss.ini
#RUN mv configs/alexavsphereskill.conf /etc/nginx/conf.d/alexavsphereskill.conf
#RUN mkdir -p /etc/letsencrypt/live/pyva.humblelab.com/
#RUN mv configs/*.pem /etc/letsencrypt/live/pyva.humblelab.com/
#RUN mv configs/startup.sh /srv/avss/startup.sh
#RUN rmdir /srv/avss/appdata/configs

#RUN chown uwsgi:nginx /srv/avss && \
#    chown uwsgi:nginx /etc/uwsgi.d/avss.ini && \
#    chmod 755 /srv/avss/startup.sh && chmod 777 /srv/avss/appdata/etc/config.ini && \
#    chmod 777 /srv/avss/appdata/etc/auth.ini

ENTRYPOINT ["/init"]
