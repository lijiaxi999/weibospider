#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''爬虫主体'''

__author__ = 'lijiaxi999'
import requests
import traceback
import json
import re
import os
from pymongo import MongoClient
from entity.User import User, Blogger
from entity.Weibo import Weibo
from time import sleep
from lxml import etree
from datetime import datetime
from datetime import timedelta


# 类装饰器，用来装饰类中的函数
def catch_exception(func):
    def wrapper(*args, **kwargs):
        try:
            begin = datetime.now()
            print('Now it\'s %s,let\'s call %s().' % (begin.strftime("%H:%M:%S"), func.__name__))
            f = func(*args, **kwargs)
            end = datetime.now()
            seconds = int((end - begin).total_seconds())
            print("%s() ends at %s,and it runs %d:%d:%d." %
                  (func.__name__, end.strftime("%H:%M:%S"), seconds / 3600, seconds % 3600 / 60, seconds % 60))
            return f
        except Exception as e:
            raise e

    return wrapper


class Spider(object):
    # 类变量headers
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,pl;q=0.4,zh-TW;q=0.2,ru;q=0.2',
        'Connection': 'keep-alive',
        'Cookie': "",
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.132 Safari/537.36'
    }

    pattern1 = r'\[(\d+)\]'  # 用于抽取中括号中的数字
    pattern2 = r'\/(\d+)\/'  # 用于抽取两个顺斜杠/间的数字

    def __init__(self, cookie):
        # 记录该spider已经发起了几次requests访问
        self.count = 0
        self.headers['Cookie'] = cookie

    # 持续爬取会被禁止访问，request会返回403
    # 解决方法引入sleep, 每访问2页，sleep 1.5秒。
    # 每访问 250 页 休息300秒
    # 每调用一次requests即调用一次_sleep函数
    def __sleep(self):
        sleep(1.5)
        if self.count % 250 == 0:
            print("sleep 300.")
            sleep(300)

    # 包装requests类的get方法
    # 每调用一次便print url
    # 同时self.count++ 便于控制访问频率
    def __get(self, url, max_try=3):
        self.count += 1
        print(str(self.count) + ':' + url)
        self.__sleep()
        cnt = 0
        while cnt < max_try:
            try:
                req = requests.get(url, headers=Spider.headers)
            except:
                print('sleep for 100')
                sleep(100)
                cnt += 1
                continue
            if req.status_code != requests.codes.ok:
                break
            return req
        # should not reach here if everything is ok
        print("Error: %s" % url)

    # 1.id
    @staticmethod
    def __parse_user_id(soup):
        href = soup.xpath("//div[@class='u']//a/@href")
        guid = re.findall(Spider.pattern2, href[0])
        id = int(guid[0])
        return id

    # 2.name
    @staticmethod
    def __parse_user_name(soup):
        username = ''
        temp = soup.xpath("//div[@class='c'][3]/text()")
        for line in temp:
            if line.startswith('昵称'):
                username = line[3:]
                break
        assert username is not None
        return username

    # 3.gender
    @staticmethod
    def __parse_user_gender(soup):
        gender = ''
        temp = soup.xpath("//div[@class='c'][3]/text()")
        for line in temp:
            if line.startswith('性别'):
                gender = line[3:]
                break
        assert gender is not None
        return gender

    # 4.birthday 5.age
    @staticmethod
    def __parse_user_age(soup):
        birthday_str = '无'
        age = -1
        temp = soup.xpath("//div[@class='c'][3]/text()")
        for line in temp:
            if line.startswith('生日'):
                birthday_str = line[3:]

        # 判断用户生日是否合法，并计算年龄
        if len(birthday_str) == 10:
            try:
                birthday = datetime.strptime(birthday_str, "%Y-%m-%d")
            except ValueError:
                # 随便设置不合法的生日，以便下面置为-1，防止'0001-00-00'情况出现
                birthday = datetime(1800, 1, 1)
            left = datetime(1918, 1, 1)
            right = datetime.now()
            if left < birthday < right:
                # 计算用户年龄
                age = int((datetime.now() - birthday).days // 365)
            else:  # 非法的生日信息
                birthday_str = '无'

        return birthday_str, age

    # 6.location
    @staticmethod
    def __parse_user_location(soup):
        location = '无'
        temp = soup.xpath("//div[@class='c'][3]/text()")
        for line in temp:
            if line.startswith('地区'):
                location = line[3:]
                break
        return location

    # 7.intro
    @staticmethod
    def __parse_user_intro(soup):
        intro = '无'
        temp = soup.xpath("//div[@class='c'][3]/text()")
        for line in temp:
            if line.startswith('简介'):
                intro = line[3:]
                break
        return intro

    # 8.label
    # 内部调用了Spider类的实例方法__get(),故不能定义为静态方法
    def __parse_user_label(self, soup):
        s = []
        temp = soup.xpath("//div[@class='c'][3]/a/text()")
        for label in temp:
            s.append(label)
        if len(s) > 1:
            if s[-1].startswith('更多'):
                s.pop()
                temp = soup.xpath("//div[@class='c'][3]/a[last()]/@href")
                # 访问‘更多’页面，以获取更多label
                t_url = 'https://weibo.cn' + temp[0]
                t_html = self.__get(t_url).content
                t_soup = etree.HTML(t_html)
                labels = t_soup.xpath("//div[@class='c'][3]/a/text()")
                if len(labels) > 3:
                    for i in range(3, len(labels)):
                        s.append(labels[i])
        return s

    # 9.identity
    # 获取用户认证信息
    @staticmethod
    def __parse_user_identity(soup):
        identity = '无'
        temp = soup.xpath("//div[@class='c'][3]/text()")
        for line in temp:
            if line.startswith('认证信息'):
                identity = line[5:]
                break
        return identity

    # 10.education
    @staticmethod
    def __parse_user_education(soup):
        education = '无'
        # 获取用户学历信息
        if len(soup.xpath("//div[@class='c']")) > 6:
            temp = soup.xpath("//div[@class='c'][4]/text()")
            sp_pos = temp[0].find('\xa0')
            if sp_pos == -1:
                education = temp[0][1:]
            else:
                education = temp[0][1:]
            if len(temp) > 1:
                for i in range(1, len(temp)):
                    sp_pos = temp[i].find('\xa0')
                    if sp_pos == -1:
                        edu2 = temp[0][1:]
                    else:
                        edu2 = temp[0][1:]
                    education = education + '-' + edu2

        return education

    # 11.verify
    @staticmethod
    def __parse_user_verify_type(soup):
        res = '无'
        r = soup.xpath("//div[@class='u']//span[@class='ctt']//img")
        if len(r) == 0:
            return res
        temp = []
        for i in r:
            src = i.attrib['src']
            if src in User.verify_table:
                temp.append(User.verify_table[src])
        if temp is not None:
            res = ''
            for t in temp:
                res = res + t + ","
            res = res.strip(",")
        return res

    # 获取blogger需要的四项信息，头像，微博数，粉丝数，关注数
    # 内部调用了Spider类的实例方法__get(),故不能定义为静态方法
    def __parse_blogger_info(self, soup):
        # 存放info的字典
        info = {}

        # 获取博主头像
        img_node = soup.xpath("//div[@class='u']/table//img[@alt='头像']")[0]
        img_url = img_node.attrib['src']
        img = self.__get(img_url).content
        # 记录当前博主的name
        name = soup.xpath("string(//head/title)")[:-3]
        # 将其保存在 pic 文件夹
        file_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "pic"
        if not os.path.isdir(file_dir):
            os.mkdir(file_dir)
        file_path = file_dir + os.sep + "%s" % name + ".jpg"
        with open(file_path, 'wb') as f:
            f.write(img)
        info['img'] = file_path

        # 获取博主微博数
        str_wb = soup.xpath("//div[@class='tip2']/span[@class='tc']/text()")[0]
        guid = re.findall(Spider.pattern1, str_wb)
        wb_num = int(guid[0])
        info['wb_num'] = wb_num

        # 关注数
        str_gz = soup.xpath("//div[@class='tip2']/a/text()")[0]
        guid = re.findall(Spider.pattern1, str_gz)
        followers = int(guid[0])
        info['followers_num'] = followers

        # 粉丝数
        str_fs = soup.xpath("//div[@class='tip2']/a/text()")[1]
        guid = re.findall(Spider.pattern1, str_fs)
        fans = int(guid[0])
        info['fans_num'] = fans

        return info

    # 获取长微博内容
    def __parse_long_weibo(self, weibo_link):
        html = self.__get(weibo_link).content
        soup = etree.HTML(html)
        info = soup.xpath("//div[@class='c']")[1]
        wb_content = info.xpath("string(div/span[@class='ctt'])")
        return wb_content[1:]

    # 解析一个微博节点，返回一个Weibo对象
    def __parse_weibo_node(self, node):
        info = {}

        # 首先判断转发还是原创 True标志为转发，否则为原创
        flag = False
        temp = node.xpath("div[1]/span")[0]
        att = temp.attrib['class']
        if att == 'kt':
            temp = node.xpath("div[1]/span")[1]
            att = temp.attrib['class']
        if att == 'cmt':
            a_node = temp.xpath("a")
            if len(a_node) > 0:
                flag = True
            else:
                flag = False
        if att == 'ctt':
            flag = False

        # 是转发微博，需要额外的获取转发人name，转发人id，转发理由等3个信息
        if flag:
            # 获取转发者姓名和id
            temp = node.xpath("div[1]/span[@class='cmt'][1]")[0]
            re_user_name = temp.xpath("string(a)")
            re_user_url = temp.xpath("a/@href")
            # 以防转发的微博被删除无法正确得到信息
            # 或由于作者设置，你暂时没有这条微博的查看权限
            if re_user_url and re_user_url[0] != 'https://weibo.cn/':
                href = re_user_url[0]
                # 获取该用户的str_id
                left_pos = href.rfind('/')
                re_user_id = href[left_pos + 1:]
            else:
                re_user_name = "无法得知"
                re_user_id = "?"
            # 转发理由，实际上即是该条微博的内容
            temp = node.xpath("div[last()]")[0]
            rw_reson = str(temp.xpath("string(.)"))
            right_pos = rw_reson.rfind("赞")
            right_pos = right_pos - 2
            rw_reason = rw_reson[5:right_pos]
            info['rw_reason'] = rw_reason
            info['rw_user'] = re_user_name + ':' + str(re_user_id)

        # 微博中at的用户与话题和内容,微博发布时间，点赞数，转发数,评论数,6项信息
        # 1.获取微博中at的用户与话题。
        # 找到当前微博节点下的所有a节点
        temp = node.xpath(".//a")  # !!! 不加点的话就是从根开始
        users = []
        topics = []
        for a in temp:
            href = a.attrib['href']
            # 如果是at的用户
            if href.startswith("/n/"):
                user = a.xpath("string(.)")[1:]
                users.append(user)
            # 如果是出现的话题
            if href.endswith("from=feed"):
                topic = a.xpath("string(.)")[1:-1]
                topics.append(topic)
        info['at_users'] = users
        info['topics'] = topics

        # 2.获取微博内容。
        # 判断是否是长微博,是的话获取全文
        a_link = node.xpath("div/span[@class='ctt']/a/@href")
        content = ''
        if a_link and a_link[-1].startswith("/comment/"):
            # 添加type信息，长微博
            a_url = "https://weibo.cn" + a_link[-1]
            content = self.__parse_long_weibo(a_url)
        # 否则正常获取
        else:
            # 添加type信息，短微博
            temp = node.xpath("div[1]/span[@class='ctt']")[0]
            content = temp.xpath("string(.)")
            content = content[:-4]  # 注意微博信息后会有一个空格和三个无宽度字符
        info['content'] = content

        # 3.获取发布时间 , 获取发布设备信息
        str_time_node = node.xpath("div/span[@class='ct']")
        str_time = str_time_node[0].xpath("string(.)")
        publish_time = str_time.split('来自')[0]
        try:
            from_str = str_time.split('来自')[1]
        except IndexError:
            from_str = 'null'
        info['from'] = from_str
        if '刚刚' in publish_time:
            publish_time = datetime.now()
        elif '分钟' in publish_time:
            minute = publish_time[:publish_time.find(u"分钟")]
            minute = timedelta(minutes=int(minute))
            publish_time = datetime.now() - minute
        elif "今天" in publish_time:
            today = datetime.now().strftime("%Y-%m-%d")
            time = publish_time[3:]
            publish_time = today + " " + time
            publish_time = publish_time.strip('\xa0')  # !!!
            publish_time = datetime.strptime(publish_time, "%Y-%m-%d %H:%M")
        elif "月" in publish_time:
            year = datetime.now().strftime("%Y")
            month = publish_time[0:2]
            day = publish_time[3:5]
            time = publish_time[7:12]
            publish_time = (year + "-" + month + "-" + day + " " + time)
            publish_time = datetime.strptime(publish_time, "%Y-%m-%d %H:%M")
        else:
            publish_time = publish_time[:16]
            publish_time = datetime.strptime(publish_time, "%Y-%m-%d %H:%M")
        info['publish_time'] = publish_time
        # 4.点赞数
        str_zan = node.xpath("((div/a)|(div/span[@class='cmt']))/text()")[-4]
        guid = re.findall(self.pattern1, str_zan, re.M)
        up_num = int(guid[0])
        info['up_num'] = up_num

        # 5.转发数
        retweet = node.xpath("div/a/text()")[-3]
        guid = re.findall(self.pattern1, retweet, re.M)
        retweet_num = int(guid[0])
        info['repost_num'] = retweet_num

        # 6.评论数
        comment = node.xpath("div/a/text()")[-2]
        guid = re.findall(self.pattern1, comment, re.M)
        comment_num = int(guid[0])
        info['comment_num'] = comment_num

        # 7.获取微博类型。
        info['type'] = []
        a_link = node.xpath("div/span[@class='ctt']/a/@href")
        if a_link and a_link[-1].startswith("/comment/"):
            info['type'].append(Weibo.lxt)  # 添加type信息，长微博
        else:
            info['type'].append(Weibo.txt)  # 添加type信息，短微博

        img_nodes = node.xpath(".//img")  # 添加type信息，图片
        if len(img_nodes) > 0:
            info['type'].append(Weibo.pic)

        if info['content'].startswith('发布了头条文章：'):
            info['type'].append(Weibo.ari)  # 添加type信息，头条文章
            info['type'].remove(Weibo.txt)

        a_nodes = node.xpath(".//a/text()")
        for n in a_nodes:
            if n.endswith("的秒拍视频"):
                info['type'].append(Weibo.vio)
                break

        # 返回一个weibo实例
        weibo = Weibo(flag)
        weibo.wirte(info)
        return weibo

    # 返回一个记录了信息的User对象
    # 获取用户信息
    def __get_user_info(self, user):
        info = {}  # 存放信息

        count = 3
        while count != 0:
            # 首先访问用户首页
            url = "https://weibo.cn/%s" % user.str_id
            html = self.__get(url).content
            soup = etree.HTML(html)
            # 新浪会不定时的返回错误页面
            if soup.xpath("string(//head/title)") != '我的首页':
                break
            count = count - 1
            print('!!!!!!')

        # 获取一般用户需要记录的十一项信息
        # 1.id 11.verify在用户首页获取，其余信息项均在用户info页面获取
        info['id'] = self.__parse_user_id(soup)
        info['verify'] = self.__parse_user_verify_type(soup)

        # 访问用户info页面
        url = "https://weibo.cn/%d/info" % info['id']
        html = self.__get(url).content
        soup = etree.HTML(html)

        info['gender'] = self.__parse_user_gender(soup)
        info['name'] = self.__parse_user_name(soup)
        info['location'] = self.__parse_user_location(soup)
        info['intro'] = self.__parse_user_intro(soup)
        info['identity'] = self.__parse_user_identity(soup)
        info['education'] = self.__parse_user_education(soup)
        info['birthday'], info['age'] = self.__parse_user_age(soup)
        info['labels'] = self.__parse_user_label(soup)

        user.write_data(info)

    # 获取博主信息
    @catch_exception
    def get_blogger_info(self, blogger):
        # 访问主页
        url = "https://weibo.cn/%s" % blogger.str_id
        html = self.__get(url).content
        soup = etree.HTML(html)

        # 获取博主的各项信息
        blogger_info = self.__parse_blogger_info(soup)
        blogger.write_data(blogger_info)
        self.__get_user_info(blogger)

        # 在MongoDB写入博主信息
        db_name = blogger.data['name']
        coll_name = 'blogger'
        data = [blogger.data]
        self.store(db_name, coll_name, data)

    # 获取粉丝信息
    @catch_exception
    def get_fans_info(self, blogger, num):
        uid = blogger.data['id']
        fans_num = blogger.data['fans_num']
        data = []

        # 写入MongoDB
        def store_fans():
            db_name = blogger.data['name']
            coll_name = 'fans'
            print()
            self.store(db_name, coll_name, data)
            data.clear()

        count = 0  # 用于控制爬取的粉丝数量
        if fans_num < 3000:
            url = "https://weibo.cn/%d/fans" % uid
            html = self.__get(url).content
            soup = etree.HTML(html)
            # 获取希望爬去的页数
            total_page = soup.xpath("//div[@class='c'][1]/div[@class='pa']//input[@name='mp']/@value")[0]
            total_page = int(total_page)

            flag = False  # 何时跳出第二层循环
            # 遍历粉丝列表的每一页
            for page in range(1, total_page + 1):
                if page != 1:
                    url = "https://weibo.cn/%d/fans?page=%d" % (uid, page)
                    html = self.__get(url).content
                    soup = etree.HTML(html)
                temp = soup.xpath("//div[@class='c'][1]//tr")

                # 遍历每一页的每一个粉丝节点
                for tr_node in temp:
                    node = tr_node.xpath(".//a")[0]
                    href = node.attrib['href']
                    # 获取该用户的str_id
                    left_pos = href.rfind('/')
                    str_id = href[left_pos + 1:]
                    fan = User(str_id)
                    # 注意有可能爬取到自己！！！ 因为页面不同，会出现Indexerror
                    try:
                        self.__get_user_info(fan)
                    except IndexError:
                        continue
                    blogger.fans.append(fan)
                    data.append(fan.data)
                    count += 1
                    if count % 50 == 0:
                        store_fans()
                    if count >= num:
                        if count % 50 != 0:
                            store_fans()
                        flag = True
                        break
                if flag:
                    break
        # 从用户的微博中抓取 num个点赞的人数
        else:
            # 在这种情况下，抽取的点赞用户可能会重复，所以需要一个list来记录，以便查询
            followers_id = []
            url = "https://weibo.cn/%d/profile" % uid
            html = self.__get(url).content
            soup = etree.HTML(html)
            temp = soup.xpath("//div[@class='c']")

            # 遍历profile页面的所有微博，进入每条微博的点赞页面
            flag = False
            for i in range(0, len(temp) - 2):
                href = temp[i].xpath("div/a")[-1].attrib['href']
                w_str = re.findall('/([^/]+)\?', href)[0]  # 抽取（/.....?)之间的微博id
                url = "https://weibo.cn/attitude/%s?#attitude" % w_str
                html = self.__get(url).content
                soup = etree.HTML(html)
                page_num = soup.xpath("//div[@class='pa'][last()]//input[@name='mp']/@value")[0]
                page_num = int(page_num)

                page = 1  # 记录遍历的页面
                while count < num and page <= page_num:
                    if page != 1:
                        url = "https://weibo.cn/attitude/%s?&page=%d" % (w_str, page)
                        html = self.__get(url).content
                        soup = etree.HTML(html)
                    followers = soup.xpath("//div[@class='c']")
                    # 遍历关注者节点
                    for j in range(3, len(followers) - 1):
                        href = followers[j].xpath("./a/@href")[0]
                        str_id = href[3:]
                        # 添加关注者的id,首先确认是否已经记录
                        if followers_id.count(str_id) == 0:
                            followers_id.append(str_id)
                            # 获取每个关注者的基本信息页面
                            fan = User(str_id)
                            self.__get_user_info(fan)
                            blogger.fans.append(fan)
                            data.append(fan.data)
                            count = count + 1
                        if count % 50 == 0:
                            store_fans()
                        if count >= num:
                            if data:
                                store_fans()
                            flag = True
                            break
                    # 遍历完某一页后，换到下一页
                    page = page + 1
                # 仅一条微博就爬取num个fan
                if flag:
                    break

        print('=============共抓取%d位粉丝的信息。=================' % count)

    # 获取关注者信息
    @catch_exception
    def get_followers_info(self, blogger, num):
        uid = blogger.data['id']
        count = 0
        data = []

        # 写入MongoDB
        def store_followers():
            db_name = blogger.data['name']
            coll_name = 'followers'
            self.store(db_name, coll_name, data)
            data.clear()

        url = "https://weibo.cn/%d/follow?page=1" % uid
        html = self.__get(url).content
        soup = etree.HTML(html)
        temp = soup.xpath("//div[@id='pagelist']//div/input[@name='mp']")[0]
        page_num = int(temp.attrib['value'])

        # 开始遍历前n页
        flag = False
        for i in range(1, page_num + 1):
            if i != 1:
                url = "https://weibo.cn/%d/follow?page=%d" % (uid, i)
                html = self.__get(url).content
                soup = etree.HTML(html)
            temp = soup.xpath("//table")
            # 遍历每一页的每一个粉丝节点
            for tr_node in temp:
                node = tr_node.xpath(".//a")[0]
                href = node.attrib['href']
                # 获取该用户的str_id
                left_pos = href.rfind('/')
                str_id = href[left_pos + 1:]
                follower = User(str_id)
                # 注意有可能爬取到自己！！！ 因为页面不同，会出现Indexerror
                try:
                    self.__get_user_info(follower)
                except IndexError:
                    continue
                blogger.followers.append(follower)
                data.append(follower.data)
                count += 1
                if count % 50 == 0:
                    store_followers()
                if count >= num:
                    if data:
                        store_followers()
                    flag = True
                    break
            if flag:
                break

        print('=============共抓取%d位关注者的信息的信息。=================' % count)

    # 获取Blogger的全部微博
    @catch_exception
    def get_weibo_info(self, blogger, num):
        uid = blogger.data['id']
        data = []

        # 写入MongoDB
        def store_weibo():
            db_name = blogger.data['name']
            coll_name = 'weibo'
            self.store(db_name, coll_name, data)
            data.clear()

        # 首先访问用户首页
        url = "https://weibo.cn/u/%d?filter=0&page=1" % uid
        html = self.__get(url).content
        soup = etree.HTML(html)

        count = 0
        # 获取全部页数，一一遍历
        if not soup.xpath("//input[@name='mp']"):
            page_num = 1
        else:
            page_num = int(soup.xpath("//input[@name='mp']")[0].attrib["value"])
            # debug
            print('there are ' + str(page_num) + ' pages.')

        # 爬取所有的页数
        for page in range(1, page_num + 1):
            page_url = "https://weibo.cn/u/%d?filter=0&page=%d" % (uid, page)
            if page != 1:
                html = self.__get(page_url).content
                soup = etree.HTML(html)
            info = soup.xpath("//div[@class='c']")

            # 在每个页面判断是否存在微博
            if len(info) >= 3:
                for i in range(0, len(info) - 2):
                    # 依次解析每个微博节点
                    # 注意，不定时新浪会返回错误网页！！！！！！需要再次访问
                    try:
                        wb = self.__parse_weibo_node(info[i])
                    except IndexError:
                        wb = self.__parse_weibo_node(info[i])
                    blogger.weibo.append(wb)
                    # 数据放入一个字典内
                    wb_data = wb.data
                    wb_data['flag'] = wb.flag
                    data.append(wb_data)
                    count = count + 1
                    if count % 100 == 0:
                        store_weibo()
                    if wb.flag:
                        blogger.data['repost_num'] += 1
                    else:
                        blogger.data['original_num'] += 1
            if count >= num:
                break
        if data:
            store_weibo()

        # 成功
        print("该用户共发布" + str(blogger.data['wb_num']) + "条微博")
        print("共爬取" + str(blogger.data['original_num'] + blogger.data['repost_num']) + "条微博")
        print(str(blogger.data['original_num']) + "条原创微博")
        print(str(blogger.data['repost_num']) + "条转发微博")

    @catch_exception
    def show(self, blogger):
        print("============blogger information==============")
        for key, val in blogger.data.items():
            print(key + ":", val)
        print("==============fans information===============")
        for fan in blogger.fans:
            print(fan.__dict__)

    @catch_exception
    def store(self, db_name, coll_name, info):
        client = MongoClient()
        db = client[db_name]
        collection = db[coll_name]
        collection.insert_many(info)
        print("写入<" + db_name + "." + coll_name + ">成功！")

    @catch_exception
    def write_json(self, blogger):
        file_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "weibo"
        if not os.path.isdir(file_dir):
            os.mkdir(file_dir)
        file_path = file_dir + os.sep + "%s" % blogger.data['name'] + ".json"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(blogger, default=lambda obj: obj.__dict__, ensure_ascii=False))

    @catch_exception
    def start(self, uid, num_weibo=10, num_fans=10, num_followers=10):
        # 处理一下要爬取的数量
        INF = 10 ** 9
        if num_weibo < 0:
            num_weibo = INF
        else:
            num_weibo = num_weibo
        if num_fans < 0:
            num_fans = INF
        else:
            num_fans = num_fans
        if num_followers < 0:
            num_followers = INF
        else:
            num_followers = num_followers
        # 开始运行
        blogger = Blogger(uid)
        self.get_blogger_info(blogger)
        self.get_weibo_info(blogger, num_weibo)
        # self.get_fans_info(blogger, num_fans)
        # self.get_followers_info(blogger, num_followers)
        # self.show(blogger)
        # self.write_json(blogger)


def main():
    try:
        # 使用实例,输入一个用户id，所有信息都会存储在Blogger实例中
        uid = ''  # 可以改成任意合法的用户id（爬虫的微博id除外）
        spider = Spider(
            cookie="")
        spider.start(uid, num_weibo=5, num_fans=5, num_followers=5)
    except Exception as e:
        traceback.print_exc()


if __name__ == "__main__":
    main()
