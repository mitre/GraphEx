# SSL Certificates

When serving GraphEx, the connection between the client and the server is secured using the HTTPS protocol. This protocol requires certificate use to work with GraphEx. By default, GraphEx will **automatically create** a new self-signed certificate using pyopenssl if you don't provide the path to one to use. This certificate will be *reused* as long as you are serving from the *same directory* each time. Should your certificate change (e.g. you serve from a new directory and aren't providing a static path to the certificates you want to use), the client browser will warn you that your connection "may be unsafe" (it isn't, your browser just doesn't recognize self-signed certificates).

This page describes information on how to provide certificates to GraphEx and one example of how you might go about manually generating (simple, self-signed) reusable certificates.

## Providing Certificates
You can tell the GraphEx where your certificate files are with the "-s" flag:
```
python3 -m graphex serve -s /path/to/certificate/directory
```

Or by providing the key+value pair in your configuration file:
```
# YML example
ssl_certificates_path: "/path/to/certificate/directory"
```

Certificates for SSL must be provided to that directory with the names: cert.pem and key.pem 

These filenames are the only ones recognized by GraphEx. If your certificates are named anything else, GraphEx will not be able to find them in the provided directory.

## Generating Self-Signed Certificates (Manual Way)
On Unix systems one way of generating self-signed certificates is to use the script included in the Graphex directory. Under the sub-directory "ssl_certificates", run the script:
```
./generate_certs.sh
```

The command 'openssl' must be available on the system. Use your system package manager to install it. The generated certificates do not have to remain in this directory, feel free to move them to an easier path to provide to GraphEx.

[Return to Main Page](../index.md)