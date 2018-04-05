# -*- coding: utf-8 -*-

'一个微博类与下面两个子类：Reposts 和 Origanls'

__author__ = 'lijiaxi999'

from enum import Enum, unique

# 枚举类型
@unique
class Weibo_type(Enum):
    txt = '短微博'
    lxt = '长微博'
    pic = '图片'
    vio = '视频'
    ari = '文章'


class Weibo(object):
    # 初始化实例属性
    def __init__(self,flag):
        self.flag = flag
        self.data = {
            'content': '',
            'publish_time': '',
            'up_num': 0,
            'repost_num': 0,
            'comment_num': 0,
            'topics': [],
            'at_users': [],
            'type': []}
        if flag:
            self.data['rw_reason'] = ''
            self.data['rw_user'] = ''

    def wirte(self, info):
        self.data.update(info)


