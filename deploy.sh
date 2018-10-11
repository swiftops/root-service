#!/bin/bash
export HOST_IP=<HOST_IP>
cd /home/ubuntu/microservice
docker-compose scale rootservice=0
docker rm $(docker ps -q -f status=exited)
docker rmi -f swiftops/rootservice && docker pull swiftops/rootservice:latest && docker-compose up -d --remove-orphans