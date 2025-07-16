import os
import os.path

bind = "0.0.0.0:8000"
workers = 2
threads = 4
worker_class = "gthread"
timeout = 120
preload_app = True
worker_tmp_dir = "/dev/shm"

CERT_DIR = "/srv/cert"
certfile = None
keyfile = None

if os.path.isfile(os.path.join(CERT_DIR, "tls.key")):
	certfile = os.path.join(CERT_DIR, "tls.crt")
	keyfile = os.path.join(CERT_DIR, "tls.key")
	ca_certs = os.path.join(CERT_DIR, "ca.crt")

