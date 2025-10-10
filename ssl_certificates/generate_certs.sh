#!/bin/sh
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj '/CN=localhost/O=MITRE/C=US'
chmod 777 *.pem