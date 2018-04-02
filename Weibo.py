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
    def __init__(self):
        self.content = ''
        self.publish_time = ''
        self.up_num = 0
        self.repost_num = 0
        self.comment_num = 0
        self.topics = []
        self.at_users = []
        self.type = []


class Reposts(Weibo):
    def __init__(self):
        super(Reposts, self).__init__()
        self.reason = ''
        self.repost_user = ''


class Origanls(Weibo):
    # 直接调用父类__init__()
    pass
