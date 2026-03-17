import os
import os.path

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", 2))
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_class = "gthread"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 120))
preload_app = True

# Heartbeat temp dir — /dev/shm is ideal (RAM-based, fast).
# On Kubernetes/OpenShift /dev/shm may be too small (64 MB default) or
# read-only, causing heartbeat failures → WORKER TIMEOUT errors.
# Fix: Mount an emptyDir{medium: Memory} at /dev/shm in the pod spec,
#      or override with GUNICORN_WORKER_TMP_DIR=/tmp
worker_tmp_dir = os.environ.get("GUNICORN_WORKER_TMP_DIR", "/dev/shm")

CERT_DIR = "/srv/cert"
certfile = None
keyfile = None

if os.path.isfile(os.path.join(CERT_DIR, "tls.key")):
	certfile = os.path.join(CERT_DIR, "tls.crt")
	keyfile = os.path.join(CERT_DIR, "tls.key")
	ca_certs = os.path.join(CERT_DIR, "ca.crt")

