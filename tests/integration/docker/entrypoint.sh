#!/bin/sh
set -eu

if [ -f /test-ssh/authorized_keys ]; then
  install -m 0600 -o chdiag -g chdiag /test-ssh/authorized_keys /home/chdiag/.ssh/authorized_keys
fi
/usr/sbin/sshd
exec /entrypoint.sh "$@"
