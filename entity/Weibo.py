# -*- coding: utf-8 -*-

'一个微博类与下面两个子类：Reposts 和 Origanls'

__author__ = 'lijiaxi999'


class Weibo(object):
    # some constants
    txt = '短微博'
    lxt = '长微博'
    pic = '图片'
    vio = '短视频'
    ari = '头条文章'

    # 初始化实例属性
    def __init__(self, flag):
        self.flag = flag
        self.data = {
            'content': '',
            'publish_time': '',
            'up_num': 0,
            'repost_num': 0,
            'comment_num': 0,
            'from': '',
            'topics': [],
            'at_users': [],
            'type': []}
        if flag:
            self.data['rw_reason'] = ''
            self.data['rw_user'] = ''

    def wirte(self, info):
        self.data.update(info)
