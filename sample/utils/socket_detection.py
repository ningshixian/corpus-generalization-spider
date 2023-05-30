# -*- coding:utf-8 -*-
import socket
import time
import os
import subprocess


while True:
    time.sleep(1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    ip = "127.0.0.1"  # ip对应服务器的ip地址
    # port = 60008
    port = 20191
    result = sock.connect_ex(("127.0.0.1", port))  # 返回状态值
    if result == 0:
        # print("Port %d is open" % port)
        pass
    else:
        print("Port %d is not open" % port)
        # os.system('python flask_test.py')
        # loader=subprocess.Popen(["python", "flask_test.py"])
        loader = subprocess.Popen(["nohup", "python", "-u", "flask_test_lock.py", ">", "log.txt", "2>&1 &"])
        returncode = loader.wait()  ######阻塞知道子进程完成
        print("returncode= %s" % (returncode))  ###打印子进程的返回码
    sock.close()

