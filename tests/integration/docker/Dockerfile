ARG CLICKHOUSE_VERSION=25.8
FROM clickhouse/clickhouse-server:${CLICKHOUSE_VERSION}

USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       openssh-server lshw sysstat iproute2 openssl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/sh chdiag \
    && install -d -m 0700 -o chdiag -g chdiag /home/chdiag/.ssh \
    && install -d -m 0755 -o root -g root /run/sshd

RUN install -d -m 0750 -o clickhouse -g clickhouse /etc/clickhouse-server/tls \
    && openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 3650 \
       -subj "/CN=127.0.0.1" \
       -addext "subjectAltName=IP:127.0.0.1,DNS:localhost,DNS:clickhouse" \
       -keyout /etc/clickhouse-server/tls/server.key \
       -out /etc/clickhouse-server/tls/server.crt \
    && chown clickhouse:clickhouse /etc/clickhouse-server/tls/server.key \
       /etc/clickhouse-server/tls/server.crt \
    && chmod 0600 /etc/clickhouse-server/tls/server.key \
    && chmod 0644 /etc/clickhouse-server/tls/server.crt

COPY tests/integration/docker/sshd_config /etc/ssh/sshd_config.d/chdiag.conf
COPY tests/integration/docker/tls.xml /etc/clickhouse-server/config.d/chdiag_tls.xml
COPY tests/integration/docker/entrypoint.sh /usr/local/bin/chdiag-test-entrypoint
RUN chmod 0755 /usr/local/bin/chdiag-test-entrypoint

EXPOSE 22 9000 9440
ENTRYPOINT ["/usr/local/bin/chdiag-test-entrypoint"]
