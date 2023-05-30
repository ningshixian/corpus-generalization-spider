#!/bin/bash

# su ningshixian
# sudo git clone http://ningshixian@git.longhu.net/ningshixian/corpus-generalization-spider.git
# # or
# sudo git pull origin 

# mkdir -m 777 sample/logs
# touch logs/flask_request8090.log
# printf "日志文件已创建\n"

# # 这个命令得加 sudo 自己来！！！
# sudo chown -R ningshixian:ningshixian .

# # 从虚拟环境启动bert-as-service服务（保证 tensorflow==1.13.1）
# conda activate bertenv
# pip install tensorflow==1.13.1
# pip install tensorflow-estimator==1.13.1
# nohup python bert_server.py > log.txt 2>&1 &
# lsof -i:5555

# # 先测试一下是否报20191端口被占用，没问题再往下执行脚本
# # 一定得保证通过才能kill掉之前的进程！！！
# python flask_test_lock.py

pkill -f "socket_detection.py"
pkill -f "flask_test_lock"
# pkill -f "flask_slot.py"

nohup python -u utils/socket_detection.py > socket.log 2>&1 &
printf "20191端口监控程序已启用\n"

nohup python -u flask_test_lock.py > log.txt 2>&1 &
printf "语料泛化（加锁）服务已启用\n"

lsof -i:20191
printf "\n"
ps -ef | grep socket
printf "脚本启动完毕\n"
