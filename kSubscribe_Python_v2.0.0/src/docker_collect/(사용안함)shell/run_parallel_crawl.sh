#!/bin/bash

for i in {1..3}
do
  docker run -d --name crawl_$i -p $((8080 + $i)):80 nginx
done



for i in {1..3}
do
  docker run -d --name docker_collect$i  docker_collect:latest $i
done