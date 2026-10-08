# Usage:  LABDEMO_SECURE_COOKIES=1 LABDEMO_TRUST_PROXY=1 gunicorn -c gunicorn.conf.py app:app
#
# Everything here is overridable from the environment so the same file works on a bare host
# (loopback bind, behind a local proxy) and in the container (0.0.0.0:8000 on a private network).
import os

import gunicorn

gunicorn.SERVER = "labdemo"        # don't advertise the gunicorn version in the Server header

bind = os.environ.get("LABDEMO_BIND", "127.0.0.1:8000")
workers = 1                        # the live terminal sandbox cache and rate limiter are in-process
threads = 8
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190
timeout = 30
graceful_timeout = 8               # must stay under docker stop's 10s SIGKILL grace; requests here finish in ms
keepalive = 5                      # proxies reuse upstream connections; the default (2s) churns them

# Containers: heartbeat files on overlayfs can stall workers; tmpfs is the documented fix.
worker_tmp_dir = "/dev/shm" if os.path.isdir("/dev/shm") else None   # nosec B108 - tmpfs is the intended heartbeat dir

errorlog = "-"                     # stderr -> `docker logs` / journald
# The proxy already writes an access log; enable this one only if you have no proxy log.
accesslog = "-" if os.environ.get("LABDEMO_ACCESS_LOG") == "1" else None
