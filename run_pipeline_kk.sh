#!/bin/bash
export CUDA_VISIBLE_DEVICES=0,1
cd kSubscribe_Python_v2.0.0/src/docker_shell
python main_collect_and_scrapping.py "$@"
