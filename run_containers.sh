#!/bin/bash

docker-compose up container_1 -d
echo "Running container_1..."
sleep 30

docker-compose up container_2 -d
echo "Running container_2..."

