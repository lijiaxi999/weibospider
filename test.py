#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Spider import *

if __name__ == '__main__':
    try:
        uid = 'wlop'  # 可以改成任意合法的用户id（爬虫的微博id除外）,字符串id和数字id均可
        spider = Spider(
            cookie="")  # 换成你自己的cookie
        # 输入你想获取的微博数，粉丝数，关注者数，输入-1则为全部爬取
        spider.start(uid, num_weibo=-1, num_fans=20, num_followers=20)
    except Exception as e:
        traceback.print_exc()
