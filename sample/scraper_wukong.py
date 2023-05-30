import sqlite3  # 数据模块
import re  # 正则
import time
import datetime
import time  # 时间模块
from bs4 import BeautifulSoup  # 解析网址模块
from selenium import webdriver  # 浏览器模块
from selenium.webdriver.chrome.options import Options
from utils.utils import setLogger


# 创建一个模拟滚动条滚动到页面底部函数
def scroll(driv):
    driv.execute_script(
        """   
    (function () {   
        var y = document.body.scrollTop;   
        var step = 100;   
        window.scroll(0, y);   


        function f() {   
            if (y < document.body.scrollHeight) {   
                y += step;   
                window.scroll(0, y);   
                setTimeout(f, 50);   
            }  
            else {   
                window.scroll(0, y);   
                document.title += "scroll-done";   
            }   
        }   
        setTimeout(f, 1000);   
    })();   
    """
    )


def start(query, pages):

    # # 仅用于Centos服务器？
    # from pyvirtualdisplay import Display
    # display = Display(visible=0, size=(800, 800))
    # display.start()

    # 关键词对应的网址
    urls = "https://www.wukong.com/search/?keyword={}".format(query)
    # 不弹出浏览器
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driv = webdriver.Chrome(chrome_options=chrome_options)  # 启动谷歌浏览器
    driv.get(urls)  # 在谷歌浏览器中打开网址
    driv.set_page_load_timeout(30)  # 设定时间，然后捕获timeout异常

    print("开始模拟鼠标拉到文章底部")
    b = 0
    c = 0

    try:
        while b < pages:  # 设置循环，可替换这里值来选择你要滚动的次数，滚动1次大概8篇内容左右
            scroll(driv)  # 滚动一次
            b = b + 1
            print("拉动{}次".format(b))
            c = c + 1
            time.sleep(c)  # 休息c秒的时间\
            soup_is_more = BeautifulSoup(driv.page_source, "html.parser")  # 解析当前网页
            is_more_content = (
                soup_is_more.find("div", class_="w-feed-loadmore").find("span", class_="w-feed-loadmore-w").text
            )  # 获得最后滚动的加载文字是否为“没有更多内容”
            # print(is_more_content)
            if is_more_content == "没有更多内容":  # 如果没有下一页直接结束拉动滑条
                break

        # 这个时候页面滚动了多次，是你最终需要解析的网页了
        soup = BeautifulSoup(driv.page_source, "html.parser")  # 解析当前网页

        sub_titles = []
        for div in soup.find_all("div", class_="question-title"):
            title = div.find("h2").find("a").text
            # 给每个title前面加上来源标签
            title = re.split(r"--_", title)[0].strip()
            sub_titles.append(title)
            # sub_titles.append('悟空问答' + '__' + title)
    except:
        logger = setLogger()
        logger.exception("Exception Logged")
    finally:
        # print("关闭浏览器")
        driv.quit()

    return sub_titles


if __name__ == "__main__":
    word = input()  # 手动输入关键词，如果你有固定的关键词可以替换成‘word='keyword'’
    pages = 2
    sub_titles = start(word, pages)
    # print(sub_titles)
