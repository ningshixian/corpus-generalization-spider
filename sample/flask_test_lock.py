# -*- coding:utf-8 -*-
import os, sys
import time
import numpy as np
import string
import re
import platform
import datetime

# import logging
import json
import traceback
import asyncio
import threading
from urllib.parse import quote
import codecs

from werkzeug.utils import secure_filename
from sklearn.metrics.pairwise import cosine_similarity
from bert_serving.client import BertClient
from flask import send_from_directory
from flask import Flask
from flask import url_for, request, jsonify
from flask import render_template, redirect, flash
from flask import make_response, send_file

# from flask.logging import create_logger
from flask import current_app
from web_scraper import BDZDSpider, BaiduSpider, QA360Spider, SougouSpider
from utils.log import _get_logger
from utils.utils import readExcel, writeExcel
import aiohttp
import textdistance

# from scraper_wukong import start


"""
语料泛化工具，涉及爬虫、异步IO、本相似度计算textdistance、异常处理

泛化工具映射-内网
http://10.231.9.140:20191/answer
泛化工具映射-外网（需配置Nginx）
https://aicare.longfor.com/test_generation

如何配置Nginx？
1、进入堡垒机，选择 003: nlpES01
2、执行如下命令
sudo -s
cd /etc/nginx/
cd conf.d/
vi nlp_test.conf

加入如下代码：

upstream test_generation {
    server 10.231.9.140:20191;
}
...
#test_generation
location /test_generation {
        include access_params;
        proxy_pass http://test_generation/answer;
        include proxy_params;
}
"""


app = Flask(__name__)
logger = _get_logger()  # Logger封装类
lock = threading.Lock()  # 生成锁对象
up_file = None

downUrl = "new_excel.xls"
# 上传文件的储的目录  D:\longfor_corpusGeneralizationSpider\sample\download
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "download")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
global_file_name = ""
ALLOWED_EXTENSIONS = set(["txt", "xls", "xlsx", "csv"])
DOWNLOAD_FILE_NAME = "new_excel.xls"

# print("远程连接bert服务...")
# # # https://bert-as-service.readthedocs.io/en/latest/source/client.html
# # bc = BertClient(ip='10.240.4.47', port=5555, port_out=5556, timeout=60000, check_version=False, check_token_info=False)
# # bc = BertClient(ip='10.231.135.107', port=5555, port_out=5556, timeout=60000, check_version=False, check_token_info=False)
# bc = BertClient(ip="10.231.9.140", port=5555, port_out=5556, timeout=60000, check_version=False, check_token_info=False)
# print("bert服务已开启.")


class MyThread(threading.Thread):
    """
    MyThread.py线程类

    Note that you can’t reuse one BertClient among multiple threads/processes, 
    you have to make a separate instance for each thread/process. 

    参考：
    https://bert-as-service.readthedocs.io/en/latest/section/faq.html#can-i-start-multiple-clients-and-send-requests-to-one-server-simultaneously
    https://www.cnblogs.com/hujq1029/p/7219163.html
    """

    def __init__(self, func, query, sub_titles):
        super(MyThread, self).__init__()
        self.func = func
        self.query = query
        self.sub_titles = sub_titles

    def run(self):
        with lock:
            self.result = self.func(self.query, self.sub_titles)

    def get_result(self):
        # threading.Thread.join(self) # 等待线程执行完毕
        try:
            return self.result
        except Exception:
            return None


# 判断文件是否合法
def allowed_file(filename):
    if "." in filename:
        extension = filename.rsplit(".", 1)[1].lower()
        if extension in ALLOWED_EXTENSIONS:
            return extension
    return False


def get_sim_score(query, sub_titles):
    """计算相似度得分"""
    # try:
    #     query_vec = bc.encode([str(query)])[0]
    #     doc_vecs = bc.encode(sub_titles)
    # except Exception as e:
    #     logger.info("bert-service error - query: {}".format(query))
    #     logger.error("get error Exception:" + str(e))
    #     logger.error("error traceback:" + traceback.format_exc())
    #     return []
    # score = np.sum(query_vec * doc_vecs, axis=1) / np.linalg.norm(doc_vecs, axis=1) # compute normalized dot product
    # # score = np.dot(doc_vecs, query_vec)   # 向量点乘
    # # score = [cosine_similarity([query_vec, doc_vec])[0, 1]
    # #          for doc_vec in doc_vecs]     # 余弦距离

    score = []
    for sub_t in sub_titles:
        score.append(textdistance.cosine.similarity(query, sub_t))
    return score


def recommend(query, sub_titles):
    """
    对爬取的子标题逆序排序
    """
    score = get_sim_score(query, sub_titles)
    question_list = []
    score = list(np.around(score, decimals=4))
    topk_idx = np.argsort(score)[::-1]
    for idx in topk_idx:
        question_list.append((sub_titles[idx], str(score[idx])))
    return question_list


def get_subtitles(sources, max_pn, key_word=None, up_file=None):
    """
    通过爬虫获取搜索结果子标题列表
    
    sources: 网站链接
    max_pn: 爬取页数
    key_word：句子
    up_file: 文件
    """
    result_cos_list = []  # 余弦值
    # 通过文件上传方式，则覆盖 key_word
    if up_file:
        # 判断是否是允许上传的文件类型，返回后缀
        extension = allowed_file(up_file.filename)
        filename = secure_filename(up_file.filename).replace("xlsx", "xls")  # 写入xlsx文件无法读取？
        # 保存文件到本地 download 目录
        up_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        # 读取上传文件的内容，并逐个查询
        if extension and extension in ["xls", "xlsx", "csv"]:
            df = readExcel(os.path.join(app.config["UPLOAD_FOLDER"], filename), ["INPUT"])
            key_word = [x[0] for x in df]
        elif extension and extension in ["txt"]:
            with codecs.open(os.path.join(app.config["UPLOAD_FOLDER"], filename), "r", "utf-8") as f:
                key_word = [x.strip("\n") for x in f]
        else:
            pass

    # 异步爬取网页aiohttp
    t1 = time.time()
    loop = asyncio.new_event_loop()  # 给汽车打火
    # loop = asyncio.get_event_loop()  # 给汽车打火 RuntimeError
    for kw in key_word:
        sub_titles = []
        if "百度知道" in sources:
            bdzd_spider = BDZDSpider(kw, max_pn)
            loop.run_until_complete(bdzd_spider.run(loop))
            sub_titles.extend(bdzd_spider.sub_titles)

        if "百度" in sources:
            bd_spider = BaiduSpider(kw, max_pn)
            loop.run_until_complete(bd_spider.run(loop))
            sub_titles.extend(bd_spider.sub_titles)

        if "360问答" in sources:
            qa360_spider = QA360Spider(kw, max_pn)
            loop.run_until_complete(qa360_spider.run(loop))
            sub_titles.extend(qa360_spider.sub_titles)

        if "搜狗问答" in sources:
            sougou_spider = SougouSpider(kw, max_pn)
            loop.run_until_complete(sougou_spider.run(loop))
            sub_titles.extend(sougou_spider.sub_titles)

        # if "悟空问答" in sources:
        #     sub_titles = start(kw, max_pn)

        t2 = time.time()
        print("Async total time: {}".format(t2 - t1))  # 2.88s

        # 对爬取结果进行处理(去重、过滤长句)
        tmp_sub_titles = []
        sub_titles = list(set(sub_titles))
        for i in range(len(sub_titles) - 1, -1, -1):
            if "..." in sub_titles[i]:  # 去掉过长的title
                continue
            sub_titles[i] = re.split(r"[？?。_-]", sub_titles[i])[0]  # 按标点切分，取第一句
            if sub_titles[i].strip():
                tmp_sub_titles.append(sub_titles[i])
        tmp_sub_titles = list(set(tmp_sub_titles))

        # # 计算相似度并保存
        # with lock:
        #     result_cos = recommend(kw, tmp_sub_titles)
        result_cos = recommend(kw, tmp_sub_titles)
        result_cos_list.append(result_cos if result_cos else [])
        print("textdistance.cosine.similarity cost time: {}".format(time.time() - t2))  # 6.55s

    loop.close()
    return result_cos_list, key_word


# @app.route("/answer", methods=["GET", "POST"])
# def upload():
#     if request.method == "POST":
#         try:
#             key_word = request.form["question"]
#             key_word = re.sub("[’!\"#$%&'()*+,-./:;<=>?@，。?★、…【】《》？“”‘’！[\\]^_`{|}~]+", "", key_word)
#             key_word = re.sub(
#                 "[\001\002\003\004\005\006\007\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a]+",
#                 "",
#                 key_word,
#             )
#             key_word = [key_word.strip()]  # 以列表形式存储，便于文件和字符串的查询
#             up_file = request.files.get("file")  # 从表单的file字段获取文件，file为该表单的name值
#             sources = request.form.getlist("category")  # 设置爬取源
#             max_pn = int(request.form.get("pages"))  # 设置抓取页数
#             if not (key_word[0] or up_file):
#                 return render_template("index.html", sources="")  # 渲染模板
#             if not sources:
#                 return render_template("index.html", sources="")  # 渲染模板

#             if up_file:
#                 logger.info(
#                     str(
#                         {
#                             "file": os.path.join(app.config["UPLOAD_FOLDER"], up_file.filename),
#                             "source": sources,
#                             "pages": max_pn,
#                         }
#                     )
#                 )
#                 result_cos_list, key_word = get_subtitles(sources, max_pn, key_word=None, up_file=up_file)
#                 # 组装用户问题
#                 sim_questions = ["###".join([x[0] for x in item]) for item in result_cos_list]
#                 # save泛化结果
#                 datas = list(zip(key_word, sim_questions))
#                 datas.insert(0, ("INPUT", "泛化结果"))  # 插入表头
#                 # 将结果文件保存在本地UPLOAD_FOLDER目录下
#                 filename = secure_filename(up_file.filename).replace("xlsx", "xls")  # 写入xlsx文件无法读取？
#                 DOWNLOAD_FILE_NAME = "new_excel.xls"
#                 writeExcel(os.path.join(app.config["UPLOAD_FOLDER"], DOWNLOAD_FILE_NAME), datas)
#                 # # UPLOAD_FOLDER是下载目录, as_attachment=True 一定要写，不然会变成打开，而不是下载
#                 # # TypeError: Object of type Response is not JSON serializable
#                 # response = make_response(send_from_directory(app.config['UPLOAD_FOLDER'],'new_'+filename, as_attachment=True))
#                 # response.headers["Content-Disposition"] = "attachment; filename={}".format('new_'+filename)
#                 # return response
#                 logger.info(os.path.join(app.config["UPLOAD_FOLDER"], DOWNLOAD_FILE_NAME))
#                 return render_template("index.html", sources=sources, downUrl=DOWNLOAD_FILE_NAME)
#             elif key_word[0]:
#                 logger.info(str(key_word[0]) + "\t" + str(sources) + "\t" + str(max_pn))
#                 result_cos_list, key_word = get_subtitles(sources, max_pn, key_word=key_word, up_file=None)
#                 key_score = result_cos_list[0] if result_cos_list[0] else [("很抱歉，未查询到任何结果o(╥﹏╥)o", "")]
#                 return render_template("index.html", sources=sources, result_cos=key_score)  # 针对界面查询一个句子的情况
#         except Exception as e:
#             logger.warning("get error msg:" + str(e) + str(request))
#             logger.warning("error traceback:" + traceback.format_exc())

#     return render_template("index.html", sources="")  # 渲染模板


def clean(sen):
    """request预处理"""
    sen = sen.replace("\r\n", "").replace("\n", "").replace("\r", "")
    sen = re.sub(
        r"[\001\002\003\004\005\006\007\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a]+",
        "",
        sen,
    )
    return sen


@app.route("/answer", methods=["GET", "POST"])
def crawl():
    """
    API调用接口地址:
    localhost:60008/crawl
    请求参数:
    {
    "key_word": ["火车丢失无法确认费用", "我在北京工作"],
    "sources": ["百度", "百度知道", "360问答", "搜狗问答"],
    "max_pn":2
    }
    """
    if request.method == "GET":
        # return app.send_static_file('index.html')  # 默认 /static
        return render_template("index_new.html")  # 默认 /templates

    elif request.method == "POST":
        try:
            d = request.get_data(as_text=True)
            d = clean(d)  # 避免请求数据中带有'\r' '\n'的情况
            json_data = json.loads(d)  # strict=False 控制字符将允许出现在json字符串里面
            key_word = json_data.get("key_word")
            sources = json_data.get("sources")
            max_pn = int(json_data.get("max_pn"))

            result_cos_list, key_word = get_subtitles(sources, max_pn, key_word=key_word, up_file=None)
            key_score = result_cos_list[0] if result_cos_list[0] else [("很抱歉，未查询到任何结果o(╥﹏╥)o", "")]
            data = {"sub_titles": key_score, "ret_code": 0}
            logger.info(
                "\n\t[POST] " + str(request) + "\n\t[Data] " + str(json_data) + "\n\t[Slot Response] " + str(data)
            )  # 成功日志记录
            return jsonify(data)
        except Exception as e:
            error_message = (
                "\n\t[POST] "
                + str(request)
                + "\n\t[Data] "
                + str(json_data)
                + "\n\t[Error traceback] "
                + str(traceback.format_exc())
            )
            logger.warning(error_message)
            data = {"sub_titles": [], "ret_code": -1}
            return jsonify(data)


# # @app.route('/gateway/fanhua/download/<downUrl>', methods=['GET'])
# @app.route("/answer/<downUrl>", methods=["GET"])
# # @app.route("/answer", methods=["GET"])
# def download(downUrl):
#     """
#     下载文件
#     disabled="disabled"

#     url_for操作对象是函数，而不是route里的路径
#     # https://aicare.longfor.com/gateway/fanhua/new_a.xls  ×
#     # http://10.240.4.47:60008/gateway/fanhua/new_a.xls    √
#     """
#     try:
#         response = send_from_directory(app.config["UPLOAD_FOLDER"], downUrl, as_attachment=True)
#         # response = make_response(send_from_directory(app.config["UPLOAD_FOLDER"], downUrl, as_attachment=True))
#         response.headers["Content-Disposition"] = "attachment; filename={}; filename*=utf-8".format(quote(downUrl))
#         response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#         return response
#     except Exception as e:
#         logger.warning("get error msg:" + str(e) + str(request))
#         logger.warning("error traceback:" + traceback.format_exc())
#         return render_template("index.html", sources="")  # 渲染模板


# import atexit
# from signal import signal, SIGTERM


# @atexit.register
# def exit_handle():
#     bc.close()  # 关闭MySQL连接


# # 使用signal捕获关闭信号，保证被kill时退出前执行
# signal(SIGTERM, lambda signum, stack_frame: exit(1))


if __name__ == "__main__":
    port = 20191

    # 不能在生产环境中使用调试器
    # 局域网可见的服务器，端口设置，在服务器部署
    app.debug = False
    app.secret_key = "super secret key"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.run(host="0.0.0.0", port=port, threaded=True)
