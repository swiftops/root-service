#!/bin/bash
export HOST_IP=<HOST_IP>
cd <Repository_Path>			#service repository path
docker-compose scale rootservice=0
docker rm $(docker ps -q -f status=exited)
docker rmi -f <IMAGE_NAME> && docker pull <IMAGE_NAME>:latest && docker-compose up -d --remove-orphans