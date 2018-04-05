# -*- coding: utf-8 -*-

'User类，其子类Blogger是被爬取的目标用户'

__author__ = 'lijiaxi999'


class User(object):
    # some constants
    RED_V, BLUE_V, VIP, ACTIVE = '红V', '蓝V', 'VIP', '达人'
    verify_table = {'https://h5.sinaimg.cn/upload/2016/05/26/319/5338.gif': RED_V,
                    'https://h5.sinaimg.cn/upload/2016/05/26/319/5337.gif': BLUE_V,
                    'https://h5.sinaimg.cn/upload/2016/05/26/319/donate_btn_s.png': VIP,
                    'https://h5.sinaimg.cn/upload/2016/05/26/319/5547.gif': ACTIVE}

    def __init__(self, str_id):  # 对于普通用户两者相同，某些大v可能会有字符串的strid
        self.str_id = str_id
        self.data = {'id': '',  # 一般用户需要记录十一项信息
                     'name': '',
                     'verify': '',
                     'identity': '',
                     'intro': '',
                     'education': '',
                     'gender': '',
                     'birthday': '',
                     'age': -1,
                     'location': '',
                     'labels': []}  # 用一个字典来记录用户信息

    def write_data(self, info):
        self.data.update(info)


class Blogger(User):
    def __init__(self, str_id):
        super().__init__(str_id)
        self.extra_data = {  # 作为爬取对象的博主需要获取额外的信息
            'img': '',
            'wb_num': -1,  # 记录博主曾发微博的总数，但可能由于某些原因不能够全部获取
            'fans_num': -1,
            'followers_num': -1,
            'original_num': -1,  # 记录可以获取的原创微博数
            'repost_num': -1 , # 记录可以获取的转发微博数
        }
        self.data.update(self.extra_data)  # 将所有信息都放在data字典中
        del self.extra_data
        self.weibo = []  # 设计为一个字典的列表，存放用户发布的所有微博
        self.followers = []  # 博主关注的人
        self.fans = []  # 粉丝
