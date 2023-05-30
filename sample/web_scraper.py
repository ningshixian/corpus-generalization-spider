#!/usr/bin/python3
# -*- coding: utf-8 -*-
import re
import os, sys
import time
import aiohttp
import asyncio
import async_timeout
import requests
from bs4 import BeautifulSoup  # 解析网址模块
import traceback
from utils.log import _get_logger

sem = asyncio.Semaphore(10)  # 信号量，控制协程数，防止爬的过快
logger = _get_logger(log_to_file=True)  # Logger封装类


class Spider(object):
    def __init__(self, kw):
        self.encoding = "utf-8"
        self.title_tag = []
        self.page_range = []
        self.kw = kw
        self.base_url = ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        self.sub_titles = []

    def get_url_list(self):
        """
        获取 url 列表
        :return: 
        """
        return [self.base_url.format(self.kw, pn) for pn in self.page_range]

    # async def get_content(self, session, url):
    #     """
    #     发送请求获取响应内容
    #     :param url:
    #     :return:
    #     """
    #     with async_timeout.timeout(10):
    #         async with session.get(url, headers=self.headers) as resp:  # 提出请求
    #             assert resp.status == 200  # 查看响应状态码
    #             return await resp.content

    async def get_titles(self, session, url):
        """
        从响应内容中提取数据-子标题
        """
        sub_title = []
        try:
            with async_timeout.timeout(20):
                # print('url: ', url)
                async with session.get(url, headers=self.headers, verify_ssl=False) as resp:  # 提出请求
                    assert resp.status == 200  # 查看响应状态码
                    html = await resp.text(encoding=self.encoding, errors="ignore")
                    soup = BeautifulSoup(html, "lxml")
                    for r in soup.find_all(self.title_tag[0], self.title_tag[1]):
                        for item in self.title_tag[2:]:
                            r = r.find(item)
                        title = re.split(r"-_", r.text)[0].strip()
                        sub_title.append(title)  # (source + '__' + title)
        except aiohttp.client_exceptions.ServerDisconnectedError:
            logger.error("请求失败，{} 服务器无法连接，抛出错误，错误信息如下：\n{}".format(url, traceback.format_exc()))
        except Exception as e:
            logger.error("解析出现错误!")
        return sub_title

    async def run(self, loop):
        jar = aiohttp.CookieJar(unsafe=True)  # 安全cookies
        with (await sem):
            # async with是异步上下文管理器
            async with aiohttp.ClientSession(cookie_jar=jar) as session:  # 获取session
                # 1. 获取 url 列表
                url_list = self.get_url_list()
                # 2. 发送请求获取响应，并从中提取数据
                tasks = [loop.create_task(self.get_titles(session, url)) for url in url_list]
                finished, unfinished = await asyncio.wait(tasks)
                # all_results = [r.result() for r in finished]  # 获取所有结果
                for r in finished:
                    self.sub_titles.extend(r.result())  # 3. 保存数据


class BDZDSpider(Spider):
    def __init__(self, kw, max_pn):
        super(BDZDSpider, self).__init__(kw)
        self.encoding = "GB2312"
        self.title_tag = ["a", {"class": "ti"}]
        self.page_range = range(0, max_pn * 10, 10)
        self.base_url = "http://zhidao.baidu.com/search?word={}&ie=gbk&pn={}"


class BaiduSpider(Spider):
    def __init__(self, kw, max_pn):
        super(BaiduSpider, self).__init__(kw)
        self.encoding = "utf-8"
        self.title_tag = ["h3", {"class": "t"}, "a"]
        self.page_range = range(0, max_pn * 10, 10)
        self.base_url = "http://www.baidu.com/s?wd={}&pn={}&ie=utf-8"


class QA360Spider(Spider):
    def __init__(self, kw, max_pn):
        super(QA360Spider, self).__init__(kw)
        self.encoding = "utf-8"
        self.title_tag = ["div", {"class": "qa-i-hd"}, "h3", "a"]
        self.page_range = range(0, max_pn, 1)
        self.base_url = "http://wenda.so.com/search/?q={}&pn={}&ie=utf-8"


class SougouSpider(Spider):
    def __init__(self, kw, max_pn):
        super(SougouSpider, self).__init__(kw)
        self.encoding = "utf-8"
        self.title_tag = ["h3", {"class": "vrTitle"}, "a"]
        self.page_range = range(1, max_pn + 1, 1)
        self.base_url = "http://www.sogou.com/sogou?query={}&page={}&ie=utf8"


def test_aio_spider():
    kw = "英雄联盟"
    max_pn = 2

    t1 = time.time()
    spider = BDZDSpider(kw, max_pn)  #
    # spider = BaiduSpider(kw, max_pn)
    # spider = QA360Spider(kw, max_pn)
    # spider = SougouSpider(kw, max_pn)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.run(loop))
    loop.close()
    print(spider.sub_titles)
    print("Async total time:", time.time() - t1)


if __name__ == "__main__":
    test_aio_spider()
