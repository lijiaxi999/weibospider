import os
import math
import re
import requests
import sys
import traceback
import sqlite3
from time import sleep
from datetime import datetime
from datetime import timedelta
from lxml import etree
import numpy as np


class Weibo:

    def __init__(self, user_id, filters=1):

        # 及时替换cookie值
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,pl;q=0.4,zh-TW;q=0.2,ru;q=0.2',
            'Connection': 'keep-alive',
            'Cookie': "SCF=AmKlvBa_-31Qcim1a-VJVUbGdM63PpiPb0hwfg7XvHVnPuamm8ZncnV_4Jz_l1R33xq8JhnX6M8DDGQoRli93Co.; "
                      "_T_WM=9be2c805b11b9dc344fe89ca703185db; "
                      "SUB=_2A253vjYLDeRhGeNN61YR9ybFyDqIHXVVQVpDrDV6PUJbkdBeLRP-kW1NSfYZnVCaBMKM_BcPc-hHZ7qfp21n77MX; "
                      "SUHB=0wn1hm2fI0IYGh; SSOLoginState=1522157147",
            'Host': 'weibo.cn',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.132 Safari/537.36'
        }

        self.user_id = user_id
        self.filters = filters
        self.username = ''
        self.weibo_num = 0  # 此数据记录该用户发布的全部微博数，包括一些不可见的微博在内
        self.original_num = 0  # 记录可以获取的原创微博数
        self.repost_num = 0  # 记录可以获取的转发微博数
        self.following = 0
        self.followers = 0
        # 用以计算request 的次数
        self.count = 0

        self.location = '无'
        self.gender = '无'
        self.identity = '无'
        self.intro = '无'
        self.birthday = '无'
        self.age = -1
        self.img = b''
        self.education = '无'
        self.label = ''

        # 原创微博
        self.weibo_content = []
        self.publish_time = []
        self.up_num = []
        self.retweet_num = []
        self.comment_num = []
        self.topics = []  # 用于统计微博中出现的话题
        self.atUsers = []  # 微博中互动的用户

        # topicsc和atUsers均考虑转发内容和转发理由
        self.rw_content = []
        self.rw_user = []
        self.rw_reason = []
        self.rw_publish_time = []
        self.rw_up_num = []
        self.rw_retweet_num = []
        self.rw_comment_num = []
        self.rw_topics = []
        self.rw_atUsers = []

        # 记录用户关注者信息
        self.following_uid = []
        self.following_name = []
        self.following_gender = []
        self.following_age = []
        self.following_location = []
        self.following_labels = []
        self.following_v = []  # 0是非v，1是红v，2是蓝v

        # 记录用户粉丝信息
        self.followers_name = []
        self.followers_uid = []
        self.followers_gender = []
        self.followers_age = []
        self.followers_location = []
        self.followers_labels = []

    # 持续爬取会被禁止访问，request会返回403
    # 解决方法引入随机sleep, 每访问2页，sleep（3, 5）秒。模拟人的真实请求。
    # 每访问 9 页 休息(20,25)秒
    # 每调用一次requests即调用一次random_sleep函数
    def random_sleep(self):
        if self.count % 2 == 0:
            sleep(np.random.randint(1, 2))
            # print("have a nap.")
        if self.count % 11 == 0:
            sleep(np.random.randint(10, 15))
            # print("have a sleep.")
        if self.count % 250 == 0:
            sleep(300)
            print("sleep 200.")
        if self.count % 450 == 0:
            sleep(300)
            print("sleep 400")

    # 包装requests包的get函数
    # 每调用一次便打印url，同时计数加一
    # 同时进行random_sleep
    # 返回lxml对html解析后的ElementTree对象
    def get(self, url, max_try=3):
        # 处理sleep
        self.count = self.count + 1
        print(str(self.count) + ":" + url)
        self.random_sleep()

        cnt = 0
        while cnt < max_try:
            try:
                req = requests.get(url, header=self.headers)
            except:
                cnt += 1
                continue
            if req.status_code != req.status_code.ok:
                break
            html = req.content
            selector = etree.HTML(html)
            return selector
        # Should not reach here
        sys.stderr.write('Error: %s\n', url)
        exit(1)


# 获取用户姓名
def get_username(self):
    print("you are retrieving to get user's name.")
    try:
        url = "https://weibo.cn/%d/info" % self.user_id
        selector = self.get(url)

        # 获取用户昵称
        username = selector.xpath("//title/text()")[0]
        self.username = username[:-3]

        # 获取用户头像
        img_url = selector.xpath("//img[@alt='头像']")[0].attrib['src']
        self.img = self.img + requests.get(img_url).content
        # debug
        # print(img_url)

        # 获取用户基本信息
        temp = selector.xpath("//div[@class='c'][3]/text()")
        for line in temp:
            if line.startswith('认证信息'): self.identity = line[5:]
            if line.startswith('性别'): self.gender = line[3:]
            if line.startswith('地区'): self.location = line[3:]
            if line.startswith('简介'): self.intro = line[3:]
            if line.startswith('生日'): self.birthday = line[3:]

        # 判断用户生日是否合法，并计算年龄
        if len(self.birthday) == 10:
            try:
                birthday = datetime.strptime(self.birthday, "%Y-%m-%d")
            except ValueError:
                # 随便设置不合法的生日，以便下面置为-1，防止'0001-00-00'情况
                birthday = datetime(1800, 1, 1)
            left = datetime(1900, 1, 1)
            right = datetime.now()
            if left < birthday < right:
                # 计算用户年龄
                age = int((datetime.now() - birthday).days / 365)
                self.age = age
            else:
                birthday = '无'

        # 获取用户学历信息
        if len(selector.xpath("//div[@class='c']")) > 6:
            temp = selector.xpath("//div[@class='c'][4]/text()")
            sp_pos = temp[0].find('\xa0')
            self.education = temp[0][1:sp_pos]
            if len(temp) > 1:
                for i in range(1, len(temp)):
                    sp_pos = temp[i].find('\xa0')
                    self.education = self.education + '-' + temp[i][1:sp_pos]

        # 获取用户标签信息
        temp = selector.xpath("//div[@class='c'][3]/a/text()")
        s = []
        for label in temp:
            s.append(label)
        if len(s) > 1:
            if s[-1].startswith('更多'):
                s.pop()
                temp = selector.xpath("//div[@class='c'][3]/a[last()]/@href")
                m_url = 'https://weibo.cn' + temp[0]
                m_selector = self.get(m_url)
                labels = m_selector.xpath("//div[@class='c'][3]/a/text()")
                if len(labels) > 3:
                    for i in range(3, len(labels)):
                        s.append(labels[i])

        # 插入label时需要将其预处理一下
        for line in s:
            self.label = self.label + line + ','
        self.label = self.label.strip(',')
        if not self.label:
            self.label = '无'
        # debug
        # print(labels)
    except Exception as e:
        print("Error:", e)
        traceback.print_exc()


# 获取用户基本信息
def get_user_info(self):
    print("you are retrieving to get user's information.")
    try:
        url = "https://weibo.cn/u/%d?filter=%d&page=1" % (self.user_id, self.filters)
        selector = self.get(url)
        pattern = r"\[(\d+)\]"

        # V 认证
        temp = selector.xpath("//div[@class='u']//img")
        if len(temp) > 1:
            V = temp[1]
            if V.attrib['alt'] == 'V':
                if V.attrib['src'].endswith('5338.gif'):
                    self.identity = '个人认证 ' + self.identity
                elif V.attrib['src'].endswith('5337.gif'):
                    self.identity = '机构认证 ' + self.identity

        # 微博数  修改
        str_wb = selector.xpath("//div[@class='tip2']/span[@class='tc']/text()")[0]
        guid = re.findall(pattern, str_wb)
        self.weibo_num = int(guid[0])

        # 关注数
        str_gz = selector.xpath("//div[@class='tip2']/a/text()")[0]
        guid = re.findall(pattern, str_gz)
        self.following = int(guid[0])

        # 粉丝数
        str_fs = selector.xpath("//div[@class='tip2']/a/text()")[1]
        guid = re.findall(pattern, str_fs)
        self.followers = int(guid[0])

    except Exception as e:
        print("Error:", e)
        traceback.print_exc()


# 获取长微博内容
def get_long_weibo(self, weibo_link):
    try:
        selector = self.get(weibo_link)
        info = selector.xpath("//div[@class='c']")[1]
        wb_content = info.xpath("string(div/span[@class='ctt'])").encode(sys.stdout.encoding, "ignore").decode(
            sys.stdout.encoding)
        return wb_content[1:]
    except Exception as e:
        print("Error: ", e)
        traceback.print_exc()


# 获取微博中的用户与话题,发布时间，点赞，转发,内容等
def get_weibo_info(self, node, topics, atUsers, ups, retweets, comments, contents, pub_time):
    pattern = r'\d+\.?\d*'
    temp = node.xpath(".//a")  # !!! 不加点的话就是从根开始
    u = ''
    t = ''
    for a in temp:
        href = a.attrib['href']
        # 如果是at的用户
        if href.startswith("/n/"):
            url = "https://weibo.cn" + href
            selector = self.get(url)
            # 可能用户被删除，直接忽略
            if selector is not None:
                continue
            try:
                href = selector.xpath("//div[@class='u']//a[1]/@href")[0]
            except IndexError:
                continue
            atUser_id = re.findall(pattern, href)[0]
            atUser_name = selector.xpath("string(head/title)")[:-3]
            if u.find(atUser_id) == -1:
                u += (atUser_name + ':' + atUser_id + ',')

        # 如果是出现的话题
        if href.endswith("from=feed"):
            topic = a.xpath("string(.)")[1:-1]
            t += topic + ','
    if not u:
        u = '无'
    if not t:
        t = '无'
    topics.append(t.strip(','))
    atUsers.append(u.strip(','))

    # 转发微博的内容
    temp = node.xpath("div[1]/span[@class='ctt'][1]")[0]
    content = temp.xpath("string(.)").encode(sys.stdout.encoding, "ignore").decode(
        sys.stdout.encoding)
    content = content[:-4]  # 注意微博信息后会有一个空格和三个无宽度字符
    # 判断是否是长微博
    a_link = node.xpath("div/span[@class='ctt']/a/@href")
    if a_link:
        if a_link[-1].startswith("/comment/"):
            a_url = "https://weibo.cn" + a_link[-1]
            content = self.get_long_weibo(a_url)
    contents.append(content)

    # 发布时间
    str_time_node = node.xpath("div/span[@class='ct']")
    str_time = str_time_node[0].xpath("string(.)").encode(
        sys.stdout.encoding, "ignore").decode(sys.stdout.encoding)
    publish_time = str_time.split(u'来自')[0]
    if u'刚刚' in publish_time:
        publish_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    elif u"分钟" in publish_time:
        minute = publish_time[:publish_time.find(u"分钟")]
        minute = timedelta(minutes=int(minute))
        publish_time = (datetime.now() - minute).strftime('%Y-%m-%d %H:%M')
    elif u"今天" in publish_time:
        today = datetime.now().strftime("%Y-%m-%d")
        time = publish_time[3:]
        publish_time = today + " " + time
    elif u"月" in publish_time:
        year = datetime.now().strftime("%Y")
        month = publish_time[0:2]
        day = publish_time[3:5]
        time = publish_time[7:12]
        publish_time = (
                year + "-" + month + "-" + day + " " + time)
    else:
        publish_time = publish_time[:16]
    pub_time.append(publish_time)

    # 点赞数
    str_zan = node.xpath("((div/a)|(div/span[@class='cmt']))/text()")[-4]
    guid = re.findall(pattern, str_zan, re.M)
    up_num = int(guid[0])
    ups.append(up_num)

    # 转发数
    retweet = node.xpath("div/a/text()")[-3]
    guid = re.findall(pattern, retweet, re.M)
    retweet_num = int(guid[0])
    retweets.append(retweet_num)

    # 评论数
    comment = node.xpath("div/a/text()")[-2]
    guid = re.findall(pattern, comment, re.M)
    comment_num = int(guid[0])
    comments.append(comment_num)


# 获取用户微博
def get_weibo(self):
    # 从微博内容第一页获取页数
    print("you are retrieving to get user's weibo info.")
    try:
        url = "https://weibo.cn/u/%d?filter=%d&page=1" % (
            self.user_id, self.filters)
        selector = self.get(url)
        if selector.xpath("//input[@name='mp']") == []:
            page_num = 1
        else:
            page_num = int(selector.xpath("//input[@name='mp']")[0].attrib["value"])
            # debug
            print('there are ' + str(page_num) + ' pages.')
        pattern = r'\d+\.?\d*'

        # 爬取所有的页数
        for page in range(1, page_num + 1):
            url2 = "https://weibo.cn/u/%d?filter=%d&page=%d" % (self.user_id, self.filters, page)
            selector2 = self.get(url2)
            info = selector2.xpath("//div[@class='c']")

            if len(info) >= 3:
                for i in range(0, len(info) - 2):
                    # 首先判断转发还是原创 True标志为转发，否则为原创
                    flag = '!!!'
                    temp = info[i].xpath("div[1]/span[1]")[0]
                    att = temp.attrib['class']
                    if att == 'kt':
                        temp = info[i].xpath("div[1]/span[2]/@class")[0]
                    if att == 'cmt':
                        a_node = temp.xpath("a")
                        if len(a_node) > 0:
                            flag = True
                        else:
                            flag = False
                    if att == 'ctt':
                        flag = False
                    # debug
                    # print(flag)

                    # 是转发微博
                    if flag:
                        temp = info[i].xpath("div[1]/span[@class='cmt'][1]")[0]
                        re_user_name = temp.xpath("string(a)")
                        re_user_url = temp.xpath("a/@href")

                        # 以防转发的微博被删除无法正确得到信息
                        if re_user_url:
                            # print(re_user_url[0])
                            temp_selector = self.get(re_user_url[0])
                            href = temp_selector.xpath("//div[@class='u']//a[1]/@href")[0]
                            re_user_id = re.findall(pattern, href)[0]
                        else:
                            re_user_name = "无法得知"
                            re_user_id = "?"

                        # 得到转发者的信息
                        self.rw_user.append(re_user_name + ":" + re_user_id)
                        # debug
                        # print(self.rw_user)

                        # 转发理由，实际上即是该条微博的内容
                        temp = info[i].xpath("div[last()]")[0]
                        rw_reson = str(temp.xpath("string(.)")).encode(sys.stdout.encoding, "ignore").decode(
                            sys.stdout.encoding)
                        right_pos = rw_reson.rfind("赞")
                        right_pos = right_pos - 2
                        rw_reason = rw_reson[5:right_pos]
                        self.rw_reason.append(rw_reason)
                        # print(rw_reason)

                        # 微博中at的用户与话题和微博的基本信息
                        self.get_weibo_info(info[i], self.rw_topics, self.rw_atUsers, self.rw_up_num,
                                            self.rw_retweet_num, self.rw_comment_num, self.rw_content,
                                            self.rw_publish_time)
                        # 成功爬取一条转发微博
                        self.repost_num += 1
                    # 是原创微博
                    else:
                        # 获取原创微博内容
                        self.get_weibo_info(info[i], self.topics, self.atUsers, self.up_num, self.retweet_num,
                                            self.comment_num, self.weibo_content, self.publish_time)
                        # 成功爬取一条原创微博
                        self.original_num += 1
        # 成功
        print(u"该用户共发布" + str(self.weibo_num) + u"条微博")
        print(u"共爬取" + str(self.original_num + self.repost_num) + u"条微博")
        print(str(self.original_num) + u"条原创微博")
        print(str(self.repost_num) + u"条转发微博")

    except Exception as e:
        print("Error: ", e)
        traceback.print_exc()


# 获取基本信息页面
def get_info(self, uid=1, gen=[], age=[], loc=[], label=[], names=[]):
    url = "https://weibo.cn/%d/info" % uid
    selector = self.get(url)

    # 获取用户基本信息
    temp = selector.xpath("//div[@class='c'][3]/text()")
    birthday = ''
    location = ''
    gender = ''
    name = ''
    for line in temp:
        if line.startswith('性别'): gender = (line[3:])
        if line.startswith('昵称'): name = (line[3:])
        if line.startswith('地区'): location = (line[3:])
        if line.startswith('生日'): birthday = line[3:]
    if len(location) == 0:
        loc.append('无')
    else:
        loc.append(location)
    if len(gender) == 0:
        gen.append('无')
    else:
        gen.append(gender)
    names.append(name)
    # debug
    # print(gen)
    # print(loc)

    # 判断用户生日是否合法，并计算年龄
    if len(birthday) == 10:
        try:
            birthday = datetime.strptime(birthday, "%Y-%m-%d")
        except ValueError:
            # 随便设置不合法的生日，以便下面置为-1，防止'0001-00-00'情况
            birthday = datetime(1800, 1, 1)
        left = datetime(1900, 1, 1)
        right = datetime.now()
        if left < birthday < right:
            # 计算用户年龄
            age_ = int((datetime.now() - birthday).days / 365)
            age.append(age_)
        else:
            age.append(-1)
    else:
        age.append(-1)
    # debug
    # print(age)

    # 获取用户标签信息
    temp = selector.xpath("//div[@class='c'][3]/a/text()")
    temp_label = []
    for lab in temp:
        temp_label.append(lab)

    if len(temp_label) > 1:
        if temp_label[-1].startswith('更多'):
            temp_label.pop()
            f_temp = selector.xpath("//div[@class='c'][3]/a[last()]/@href")
            m_url = 'https://weibo.cn' + f_temp[0]
            m_selector = self.get(m_url)
            labels = m_selector.xpath("//div[@class='c'][3]/a/text()")
            if len(labels) > 3:
                for i in range(3, len(labels)):
                    temp_label.append(labels[i])
    label_str = ''
    if len(temp_label) > 1:
        for line in temp_label:
            label_str = label_str + line + ','
        label_str = label_str.strip(',')
    else:
        label_str = '无'
    label.append(label_str)
    # debug
    # print(label)


# 从评论中获取 100 名关注者的信息
def get_followers_info(self):
    print("you are retrieving to get followers info.")
    try:
        # 若用户的关注人数小于3000，直接从关注者列表抓取100人
        # debug
        if self.followers < 3000:
            url = "https://weibo.cn/%d/fans" % self.user_id
            selector = self.get(url)
            # 获取希望爬去的页数
            total_page = selector.xpath("//div[@class='c'][1]/div[@class='pa']//input[@name='mp']/@value")[0]
            total_page = int(total_page)

            count = 0
            for page in range(1, total_page + 1):
                if page != 1:
                    url = "https://weibo.cn/%d/fans?page=%d" % (self.user_id, page)
                    selector = self.get(url)
                temp = selector.xpath("//div[@class='c'][1]//tr")

                for tr_node in temp:
                    # 为防止该关注者，本账号已经关注
                    try:
                        node = tr_node.xpath(".//a")[2]
                    except IndexError:
                        node = tr_node.xpath(".//a")[0]
                        url = node.attrib['href']
                        temp_selector = self.get(url)
                        node = temp_selector.xpath("//div[@class='u']//a")[0]
                    href = node.attrib['href']
                    f_uid = int(re.findall("\d*\d", href)[0])

                    # 记录关注者的id
                    self.followers_uid.append(f_uid)
                    # 获取每个关注者的基本信息页面
                    self.get_info(uid=f_uid, gen=self.followers_gender, age=self.followers_age,
                                  loc=self.followers_location, label=self.followers_labels,
                                  names=self.followers_name)
                    count += 1
                if count >= 100:
                    break
        # 从用户的微博中抓取 100个点赞的人数
        else:
            url = "https://weibo.cn/%d/profile" % self.user_id
            selector = self.get(url)
            temp = selector.xpath("//div[@class='c']")

            # 遍历profile页面的所有微博，进入每条微博的点赞页面
            for i in range(0, len(temp) - 2):
                href = temp[i].xpath("div/a")[-1].attrib['href']
                w_str = re.findall('/([^/]+)\?', href)[0]
                f_url = "https://weibo.cn/attitude/%s?#attitude" % w_str
                f_selector = self.get(f_url)
                page_num = f_selector.xpath("//div[@class='pa'][last()]//input[@name='mp']/@value")[0]
                page_num = int(page_num)

                count = 0  # 记录已抓取的粉丝人数
                page = 1  # 记录遍历的页面
                while count < 100 and page <= page_num:
                    if page != 1:
                        f_url = "https://weibo.cn/attitude/%s?&page=%d" % (w_str, page)
                        f_selector = self.get(f_url)
                    followers_node = f_selector.xpath("//div[@class='c']")
                    # 遍历关注者节点
                    for j in range(3, len(followers_node) - 1):
                        href = followers_node[j].xpath("./a/@href")[0]
                        f_uid = int(re.findall('/u/(\d*)', href)[0])

                        # 添加关注者的id,首先确认是否已经记录
                        if self.followers_uid.count(f_uid) == 0:
                            self.followers_uid.append(f_uid)
                            # 获取每个关注者的基本信息页面
                            self.get_info(uid=f_uid, gen=self.followers_gender, age=self.followers_age,
                                          loc=self.followers_location, label=self.followers_labels,
                                          names=self.followers_name)
                            count = count + 1
                    # 遍历完某一页后，换到下一页
                    page = page + 1
                # 仅一条微博就爬取100 fan
                if page < page_num:
                    break
    except Exception as e:
        print("error ", e)
        traceback.print_exc()


# 获取用户关注的人的信息
def get_followings_info(self):
    print("You are retrieving to get followings info.")
    try:
        # 如果关注者超过100就读取前10页，否则就全部读取
        if self.following <= 100:
            page_num = math.ceil(self.following / 10)
        else:
            page_num = 10

        # 开始遍历前n页
        for i in range(1, page_num + 1):
            url = "https://weibo.cn/%d/follow?page=%d" % (self.user_id, i)
            selector = self.get(url)
            temp = selector.xpath("//table")

            # 遍历每一页的n条关注者
            for j in range(len(temp)):
                # 记录关注者的认证信息
                # print("--------------------------")
                img_nodes = temp[j].xpath(".//img")
                if len(img_nodes) > 1:
                    V = img_nodes[1]
                    if V.attrib['alt'] == 'V':
                        if V.attrib['src'].endswith('5338.gif'):
                            self.following_v.append(1)
                        elif V.attrib['src'].endswith('5337.gif'):
                            self.following_v.append(2)
                        else:
                            self.following_v.append(0)
                    else:
                        self.following_v.append(0)
                else:
                    self.following_v.append(0)
                # debug
                # print(self.following_v)

                # 获取关注者的id
                # 若遇到该关注者已被本账户关注的情况
                try:
                    node = temp[j].xpath(".//a")[2]
                except IndexError:
                    node = temp[j].xpath(".//a")[1]
                    url = node.attrib['href']
                    temp_selector = self.get(url)
                    node = temp_selector.xpath("//div[@class='u']//a")[0]

                href = node.attrib['href']
                f_uid = int(re.findall('(\d*\d)', href)[0])
                self.following_uid.append(f_uid)
                # debug
                # print(self.following_uid)

                # 获取info页面的基本信息
                self.get_info(uid=f_uid, gen=self.following_gender, age=self.following_age,
                              loc=self.following_location, label=self.following_labels, names=self.following_name)

    except Exception as e:
        print("Error: ", e)
        traceback.print_exc()


# 将爬取的信息写入文件
def write_txt(self):
    try:
        file_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "weibo"
        if not os.path.isdir(file_dir):
            os.mkdir(file_dir)
        file_path = file_dir + os.sep + "%s" % self.username + ".txt"
        f = open(file_path, "wb")

        if self.filters:
            result_header = u"\n\n原创微博内容：\n"
        else:
            result_header = u"\n\n微博内容：\n"
        result_header = (u"用户信息\n用户昵称：" + self.username +
                         u"\n用户id：" + str(self.user_id) +
                         u"\n微博数：" + str(self.weibo_num) +
                         u"\n关注数：" + str(self.following) +
                         u"\n粉丝数：" + str(self.followers) +
                         result_header
                         )
        f.write(result_header.encode(sys.stdout.encoding))

        for i in range(1, self.original_num + 1):
            text = (str(i) + ":" + self.weibo_content[i - 1] + "\n" +
                    u"发布时间：" + self.publish_time[i - 1] + "\n" +
                    u"点赞数：" + str(self.up_num[i - 1]) +
                    u"	 转发数：" + str(self.retweet_num[i - 1]) +
                    u"	 评论数：" + str(self.comment_num[i - 1]) + "\n\n"
                    )
            f.write(text.encode(sys.stdout.encoding))
        f.close()
        print(u"微博写入文件完毕，保存路径:" + file_path)
    except Exception as e:
        print("Error: ", e)
        traceback.print_exc()


# 将爬取的信息写入sqlite数据库
def write_db(self):
    try:
        file_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "weibo"
        if not os.path.isdir(file_dir):
            os.mkdir(file_dir)
        file_path = file_dir + os.sep + "%s" % self.username + ".sqlite"
        conn = sqlite3.connect(file_path)
        cur = conn.cursor()

        # 写入用户信息
        cur.execute('''CREATE TABLE IF NOT EXISTS User 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        u_id INTEGER UNIQUE,
                        u_name TEXT UNIQUE,
                        identity TEXT,
                        birthday TEXT,
                        age INTEGER,
                        gender TEXT,
                        location TEXT,
                        img BLOB,
                        education TEXT,
                        intro TEXT,
                        label TEXT,
                        weibo_num INTEGER,
                        followers INTEGER,
                        following INTEGER)''')
        cur.execute('''INSERT OR IGNORE INTO User
                        (u_id,u_name,identity,birthday,age,gender,location,
                        img,education,intro,label,weibo_num,followers,following)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (self.user_id, self.username, self.identity, self.birthday, self.age,
                     self.gender, self.location, self.img, self.education, self.intro, self.label,
                     self.weibo_num, self.followers, self.following))
        conn.commit()

        # 写入微博信息
        cur.execute('''CREATE TABLE IF NOT EXISTS Originals
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         content TEXT,
                         up_num INTEGER,
                         retweet_num INTEGER,
                         comment_num INTEGER,
                         topics TEXT,
                         at TEXT,
                         time TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS Reposts
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT,
                        re_user TEXT,
                        reason TEXT,
                        up_num INTEGER,
                        retweet_num INTEGER,
                        comment_num INTEGER,
                        topics TEXT,
                        at TEXT,
                        time TEXT)''')
        for i in range(1, self.original_num + 1):
            # debug
            # print('写入第%d条。' % i)
            cur.execute('''INSERT OR IGNORE INTO Originals
                            (content,up_num,retweet_num,comment_num,topics,at,time)
                            VALUES (?,?,?,?,?,?,?)''',
                        (self.weibo_content[i - 1], self.up_num[i - 1], self.retweet_num[i - 1],
                         self.comment_num[i - 1], self.topics[i - 1], self.atUsers[i - 1],
                         self.publish_time[i - 1]))
        for i in range(1, self.repost_num + 1):
            # debug
            # print('写入第%d条。' % i)
            cur.execute('''INSERT OR IGNORE INTO Reposts
                            (content,re_user,reason,up_num,retweet_num,comment_num,topics,at,time)
                            VALUES (?,?,?,?,?,?,?,?,?)''',
                        (self.rw_content[i - 1], self.rw_user[i - 1], self.rw_reason[i - 1], self.rw_up_num[i - 1],
                         self.rw_retweet_num[i - 1], self.rw_comment_num[i - 1], self.rw_topics[i - 1],
                         self.rw_atUsers[i - 1], self.rw_publish_time[i - 1]))
        conn.commit()

        # 写入关注者信息
        cur.execute('''CREATE TABLE IF NOT EXISTS Followings
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        u_id INTEGER,
                        u_name TEXT,
                        location TEXT,
                        gender TEXT,
                        label TEXT,
                        age INTEGER,
                        V INTEGER)''')
        for i in range(0, len(self.following_uid)):
            cur.execute('''INSERT OR IGNORE INTO Followings
                            (u_id,u_name,V,location,gender,age,label)
                            VALUES (?,?,?,?,?,?,?)''',
                        (self.following_uid[i], self.following_name[i], self.following_v[i],
                         self.following_location[i],
                         self.following_gender[i], self.following_age[i], self.following_labels[i]))
        conn.commit()

        # 写入粉丝信息
        cur.execute('''CREATE TABLE IF NOT EXISTS Followers
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        u_id INTEGER,
                        u_name TEXT,
                        location TEXT,
                        gender TEXT,
                        label TEXT,
                        age INTEGER)''')
        for i in range(0, len(self.followers_uid)):
            cur.execute('''INSERT OR IGNORE INTO Followers
                            (u_id,u_name,location,gender,age,label)
                            VALUES (?,?,?,?,?,?)''',
                        (self.followers_uid[i], self.followers_name[i], self.followers_location[i],
                         self.followers_gender[i], self.followers_age[i], self.followers_labels[i]))
        conn.commit()

        conn.close()
        print(u"微博写入数据库完毕，保存路径:" + file_path)
    except Exception as e:
        print("Error: ", e)
        traceback.print_exc()


# print 爬取的信息
def show(self):
    print("用户名：" + self.username)
    print('用户id：' + str(self.user_id))
    print("用户简介：" + self.intro)
    print('用户认证：' + self.identity)
    print('用户生日：' + self.birthday)
    print('用户年龄：' + str(self.age))
    print('用户位置：' + self.location)
    print('用户性别：' + self.gender)
    print('用户学历：' + self.education)
    print('用户标签:' + self.label)

    print("全部微博数：" + str(self.weibo_num))
    print("关注数：" + str(self.following))
    print("粉丝数：" + str(self.followers))

    print("总共访问：", self.count)
    # print("最新一条原创微博为：" + self.weibo_content[0])
    # print("最新一条原创微博发布时间：" + self.publish_time[0])
    # print("最新一条原创微博获得的点赞数：" + str(self.up_num[0]))
    # print("最新一条原创微博获得的转发数：" + str(self.retweet_num[0]))
    # print("最新一条原创微博获得的评论数：" + str(self.comment_num[0]))


# 运行爬虫
def start(self):
    try:
        begin = datetime.now()
        print("begin:", begin.strftime("%H:%M:%S"))

        self.get_username()
        self.get_user_info()
        self.get_followers_info()
        self.get_followings_info()
        self.get_weibo()
        # self.write_txt()
        self.write_db()
        self.show()
        print(u"信息抓取完毕")

        end = datetime.now()
        seconds = int((end - begin).total_seconds())
        print("end:", end.strftime("%H:%M:%S"))
        print("Program running time: %d:%d:%d" % (seconds / 3600, seconds % 3600 / 60, seconds % 60))
        print("===========================================================================")
    except Exception as e:
        print("Error: ", e)
        traceback.print_exc()


def main():
    try:
        # 使用实例,输入一个用户id，所有信息都会存储在wb实例中
        user_id = 1826792401  # 可以改成任意合法的用户id（爬虫的微博id除外）
        filter = 0  # 值为0表示爬取全部微博（原创微博+转发微博），值为1表示只爬取原创微博
        wb = Weibo(user_id, filter)  # 调用Weibo类，创建微博实例wb
        wb.start()  # 爬取微博信息

    except Exception as e:
        print("Error: ", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
