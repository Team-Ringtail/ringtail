#!/bin/sh
/usr/local/bin/sandbox-api &

echo "Waiting for sandbox API..."
while ! nc -z 127.0.0.1 8080; do
  sleep 0.1
done
echo "Sandbox API ready"

wait
