#!/bin/sh

# Creates a TLS cert for 7f000001.nip.io (which is a fancy domain that points
# to 127.0.0.1).
# It's self-signed, but Gemini should work with self-signed certs.

openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
  -keyout localhost.key -out localhost.crt -subj "/CN=7f000001.nip.io" \
  -addext "subjectAltName=DNS:7f000001.nip.io"
