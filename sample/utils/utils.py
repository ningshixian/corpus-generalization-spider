import logging
import os
import pandas as pd
import xlwt
import pymysql
import time
import math
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy import spatial


"""
日志记录、Excel读写、相似度计算方法
"""


def setLogger():
    # 创建一个logger,可以考虑如何将它封装
    logger = logging.getLogger("mylogger")
    logger.setLevel(logging.DEBUG)

    # 创建一个handler，用于写入日志文件
    fh = logging.FileHandler(os.path.join(os.getcwd(), "log.txt"))
    fh.setLevel(logging.DEBUG)

    # 再创建一个handler，用于输出到控制台
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # 定义handler的输出格式
    formatter = logging.Formatter("%(asctime)s - %(module)s.%(funcName)s.%(lineno)d - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # 给logger添加handler
    logger.addHandler(fh)
    logger.addHandler(ch)

    # 记录一条日志
    # logger.info('hello world, i\'m log helper in python, may i help you')
    return logger


# 读取EXCEL文件
def readExcel(excel_file, cols=[]):
    """
    pd.read_excel()参数解释
    sheet_name : str, int, list, or None, default 0
    names : array-like, default None, List of column names to use. 
    usecols : int, str, list-like, or callable default None
    skiprows : list-like. Rows to skip at the beginning (0-indexed).
    """
    io = pd.io.excel.ExcelFile(excel_file)
    df = pd.read_excel(io, names=cols, sheet_name=0)
    # print(df.head(5))
    io.close()

    df_li = df.values.tolist()
    return df_li


#  将数据写入EXCEL文件
def writeExcel(file_path, datas):
    f = xlwt.Workbook()
    sheet1 = f.add_sheet(u"sheet1", cell_overwrite_ok=True)  # 创建sheet
    for i in range(len(datas)):
        data = datas[i]
        for j in range(len(data)):
            sheet1.write(i, j, str(data[j]))  # 将数据写入第 i 行，第 j 列
    f.save(file_path)  # 保存文件


def euclidean_distance(data1, data2):
    points = zip(data1, data2)
    diffs_squared_distance = [pow(a - b, 2) for (a, b) in points]
    return math.sqrt(sum(diffs_squared_distance))


def Standardized_Euclidean(vec1, vec2, v):
    npvec = np.array([np.array(vec1), np.array(vec2)])
    return spatial.distance.pdist(npvec, "seuclidean", V=None)


def cosine_sim(vec1, vec2):
    sim = cosine_similarity([vec1, vec2])[0, 1]
    return sim


def cosine_sim2(vec1, vec2):
    # fenzi = np.dot(doc_vecs, query_vec)
    # score = [fenzi[i] / (norm(doc_vecs[i]) * norm(query_vec)) for i in range(len(doc_vecs))]

    sim = vec1.dot(vec2.T)
    norms = np.array([np.sqrt(np.diagonal(sim))])
    sim = sim / norms / norms.T
    return sim


def Manhattan(vec1, vec2):
    npvec1, npvec2 = np.array(vec1), np.array(vec2)
    return np.abs(npvec1 - npvec2).sum()


def Chebyshev(vec1, vec2):
    npvec1, npvec2 = np.array(vec1), np.array(vec2)
    return max(np.abs(npvec1 - npvec2))


if __name__ == "__main__":
    score = cosine_sim(np.array([3, 4]), np.array([3, 4]))
    print(score)
