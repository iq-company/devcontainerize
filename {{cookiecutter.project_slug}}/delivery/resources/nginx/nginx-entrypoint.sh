#!/bin/bash

# Set variables that do not exist
if [[ -z "$BACKEND" ]]; then
    echo "BACKEND defaulting to 0.0.0.0:8000"
    export BACKEND=0.0.0.0:8000
fi
if [[ -z "$SOCKETIO" ]]; then
    echo "SOCKETIO defaulting to 0.0.0.0:9000"
    export SOCKETIO=0.0.0.0:9000
fi
if [[ -z "$UPSTREAM_REAL_IP_ADDRESS" ]]; then
    echo "UPSTREAM_REAL_IP_ADDRESS defaulting to 127.0.0.1"
    export UPSTREAM_REAL_IP_ADDRESS=127.0.0.1
fi
if [[ -z "$UPSTREAM_REAL_IP_HEADER" ]]; then
    echo "UPSTREAM_REAL_IP_HEADER defaulting to X-Forwarded-For"
    export UPSTREAM_REAL_IP_HEADER=X-Forwarded-For
fi
if [[ -z "$UPSTREAM_REAL_IP_RECURSIVE" ]]; then
    echo "UPSTREAM_REAL_IP_RECURSIVE defaulting to off"
    export UPSTREAM_REAL_IP_RECURSIVE=off
fi

if [[ -n "$IQ_SITE_NAME_HEADER" ]]; then
    export FRAPPE_SITE_NAME_HEADER="$IQ_SITE_NAME_HEADER"
elif [[ -n "$FRAPPE_SITE_NAME_HEADER" ]]; then
    export FRAPPE_SITE_NAME_HEADER="$FRAPPE_SITE_NAME_HEADER"
else
    echo 'Site-Name defaulting to $host'
    export FRAPPE_SITE_NAME_HEADER="$host"
fi

if [[ -z "$PROXY_READ_TIMEOUT" ]]; then
    echo "PROXY_READ_TIMEOUT defaulting to 120"
    export PROXY_READ_TIMEOUT=120
fi

if [[ -z "$CLIENT_MAX_BODY_SIZE" ]]; then
    echo "CLIENT_MAX_BODY_SIZE defaulting to 50m"
    export CLIENT_MAX_BODY_SIZE=50m
fi

# port/listener settings with opt TLS Settings #################
export LISTENER_PLACEHOLDER="listen 8080;"

TLS_PATH="/opt/nginx/conf/tls"

if [ -f "$TLS_PATH/tls.key" ]; then
  echo "Activating TLS"

  export LISTENER_PLACEHOLDER="
  listen 8080 ssl;
  ssl_certificate           $TLS_PATH/tls.crt;
  ssl_certificate_key       $TLS_PATH/tls.key;
  ssl_trusted_certificate   $TLS_PATH/ca.crt;

  proxy_ssl_trusted_certificate   $TLS_PATH/ca.crt;

  # Optional: Weitere SSL-Parameter
  # ssl_protocols TLSv1.2 TLSv1.3;
  # ssl_ciphers   HIGH:!aNULL:!MD5;
  # ...
  "
fi
# End of Optional TLS Settings #################################

# shellcheck disable=SC2016
envsubst '${BACKEND}
  ${SOCKETIO}
  ${UPSTREAM_REAL_IP_ADDRESS}
  ${UPSTREAM_REAL_IP_HEADER}
  ${UPSTREAM_REAL_IP_RECURSIVE}
  ${FRAPPE_SITE_NAME_HEADER}
  ${PROXY_READ_TIMEOUT}
  ${LISTENER_PLACEHOLDER}
  ${CLIENT_MAX_BODY_SIZE}' \
    </templates/nginx/{{ cookiecutter.project_slug }}.conf.template >/opt/nginx/conf/conf.d/{{ cookiecutter.project_slug }}.conf


if [ -f "$TLS_PATH/tls.key" ]; then
  sed -i 's|http://backend-server|https://backend-server|g' /opt/nginx/conf/conf.d/{{ cookiecutter.project_slug }}.conf
fi

/opt/nginx/sbin/nginx -g 'daemon off;'
