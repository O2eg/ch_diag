ARG CLICKHOUSE_VERSION=25.8.28.1
FROM clickhouse/clickhouse-server:${CLICKHOUSE_VERSION}

USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       openssh-server lshw sysstat iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/sh chdiag \
    && install -d -m 0700 -o chdiag -g chdiag /home/chdiag/.ssh \
    && install -d -m 0755 -o root -g root /run/sshd

COPY tests/integration/docker/sshd_config /etc/ssh/sshd_config.d/chdiag.conf
COPY tests/integration/docker/entrypoint.sh /usr/local/bin/chdiag-test-entrypoint
RUN chmod 0755 /usr/local/bin/chdiag-test-entrypoint

EXPOSE 22 9000
ENTRYPOINT ["/usr/local/bin/chdiag-test-entrypoint"]
