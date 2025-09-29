#!/bin/bash

docker run --rm -v /threeway/Appl_logs/python:/Appl_logs/python docker_collect

docker run --rm -v /threeway/Appl_logs/python:/Appl_logs/python docker_scraping

docker run --rm -v /threeway/Appl_logs/python:/Appl_logs/python docker_talk_send

docker run --rm -v /threeway/Appl_logs/python:/Appl_logs/python send_history
