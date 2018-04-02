# -*- coding: utf-8 -*-

'User类，其子类Blogger是被爬取的目标用户'

__author__ = 'lijiaxi999'

from enum import Enum, unique


@unique
class Verify(Enum):
    RED_V = '红V'
    BLUE_V = '蓝V'
    VIP = 'vip'
    ACTIVE = '活跃'
    null = '无'
    verify_table = {'http://u1.sinaimg.cn/upload/2011/07/28/5338.gif': RED_V,
                    'http://u1.sinaimg.cn/upload/2011/07/28/5337.gif': BLUE_V,
                    'http://u1.sinaimg.cn/upload/h5/img/hyzs/donate_btn_s.png': VIP,
                    'http://u1.sinaimg.cn/upload/2011/08/16/5547.gif': ACTIVE}


class User(object):
    def __init__(self):
        self.id = ''
        self.name = ''
        self.gender = ''
        self.age = ''
        self.birthday = ''
        self.location = ''
        self.labels = []
        self.intro = ''
        self.verify = ''
        self.identity = '无'
        self.fans = 0
        self.followers = 0


class Blogger(User):
    def __init__(self):
        super(Blogger, self).__init__()
        self.weibo_num = 0  # 此数据记录该用户发布的全部微博数，包括一些不可见的微博在内
        self.original_num = 0  # 记录可以获取的原创微博数
        self.repost_num = 0  # 记录可以获取的转发微博数
        self.img = b''
