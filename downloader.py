import requests
import os
import threading
import time
import re

ADD_THREAD_MAX_NUM = 10                 # 最大添加线程数
DOWNLOAD_THREAD_MAX_NUM = 10             # 最大下载线程数
MAX_TRY_TIMES = 3           # 下载失败最大重试次数
DIR_PATH = r".\album"        # 文件保存地址
USE_DIR_MARGIN = 10         # 单个artworks内的图片数量超过该值时，单独保存为文件夹，否则全部放入默认路径

add_list = list()
download_list = list()
fail_list = list()
adder_num = 0                       # 添加线程数量，为0且download_list空时下载进程才可结束
add_lock = threading.Lock()         # for add_list
download_lock = threading.Lock()    # for download_list
fail_lock = threading.Lock()        # for fail_list
adder_lock = threading.Lock()       # for adder_num
add_finish_flag = False

# 不加以下这些会报错，因为eval()不能处理布尔型数据
false = 'False'
null = 'None'
true = 'True'

DefaultHeader = {"User-Agent": "ozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
                 "Cookie": ""}


class DownloadTask:
    def __init__(self, url, path, header=None):
        self.url = url
        self.header = header
        self.path = path
        self.fail_times = 0
        if self.header is None:
            global DefaultHeader
            self.header = DefaultHeader


class ThreadAdder(threading.Thread):
    def __init__(self, thread_id):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.artworks_id = ""
        self.adder_counter(1)

    def run(self):
        global add_list
        while True:
            add_lock.acquire()
            if not add_list and add_finish_flag:
                add_lock.release()
                self.adder_counter(-1)
                return
            elif not add_list:
                add_lock.release()
                time.sleep(5)
                continue

            self.artworks_id = add_list.pop(0)
            add_lock.release()

            self.add_task()

    def adder_counter(self, change):
        adder_lock.acquire()
        global adder_num
        adder_num += change
        adder_lock.release()

    # def get_artworks_info(self, img_id):  # 传入图片ID，返回该图片ID下的信息，具体信息见注释
    #     '''
    #     img_dic = {
    #         'illustID' : 插画ID
    #         'illustTitle' : 插画标题
    #         'illustDescription' : 插画简介
    #         'createDate' : 插画创建时间
    #         'uploadDate' : 插画更新时间
    #         'tags' : 插画tag,值为列表
    #         'authorID' : 作者ID
    #         'authorName' : 作者昵称
    #     }
    #     '''
    #     img_dic = {}
    #
    #     header = DefaultHeader.copy()
    #     header["Referer"] = "https://www.pixiv.net/member_illust.php?mode=medium&illust_id={}".format(img_id)
    #     url = 'https://www.pixiv.net/ajax/illust/' + str(img_id)
    #     response_raw = requests.get(url, headers=header)
    #
    #     global false, null, true
    #     response = eval(response_raw.content)['body']
    #     img_dic['illustID'] = response['illustId']  # 图片ID
    #     img_dic['illustTitle'] = response['illustTitle']  # 图片标题
    #     img_dic['illustDescription'] = response['illustComment']  # 图片简介
    #     img_dic['createDate'] = response['createDate']  # 创建时间
    #     img_dic['uploadDate'] = response['uploadDate']  # 更新时间
    #     img_dic['tags'] = []  # 因为有多个tag，所以'tags'的值用列表形式保存
    #     for tag in response['tags']['tags']:
    #         img_dic['tags'].append(tag['tag'])
    #     img_dic['authorID'] = response['tags']['tags'][0]['userId']
    #     img_dic['authorName'] = response['tags']['tags'][0]['userName']
    #
    #     return img_dic

    def get_artworks_url(self, img_id):
        header = DefaultHeader.copy()
        header["Referer"] = "https://www.pixiv.net/member_illust.php?mode=medium&illust_id={}".format(img_id)
        url = 'https://www.pixiv.net/ajax/illust/{}/pages'.format(img_id)
        try:
            response_raw = requests.get(url, headers=header)
        except Exception as e:
            print(e)
            return []

        # print(response_raw.status_code)

        if response_raw.status_code != 200:
            print(response_raw.text)
            return []

        response = eval(response_raw.content)['body']
        img_url = []  # 因为存在好几个插画在同一页面的情况，所以'imgUrl'的值用列表形式保存
        for img in response:
            img_url.append(img['urls']['original'].replace('\\', ''))

        return img_url

    def add_task(self):
        global DefaultHeader
        header = DefaultHeader.copy()
        header["Referer"] = "https://www.pixiv.net/member_illust.php?mode=medium&illust_id={}".format(self.artworks_id)
        url = self.get_artworks_url(self.artworks_id)
        if url is []:
            print(str(self.artworks_id) + "url获取失败")
            return
        # print(url)
        if len(url) >= USE_DIR_MARGIN:
            folder = os.path.join(DIR_PATH, str(self.artworks_id))
        else:
            folder = DIR_PATH

        if not os.path.exists(folder):
            os.mkdir(folder)

        for i in range(len(url)):
            path = os.path.join(folder, str(str(url[i]).rsplit('/', 1)[-1]))
            global download_list
            download_list.append(DownloadTask(url[i], path, header))


class ThreadDownloader(threading.Thread):
    def __init__(self, thread_id):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.download_num = 0
        self.task = DownloadTask("", {}, "")

    def run(self):
        global download_list
        while True:
            download_lock.acquire()
            global adder_num
            if not download_list and adder_num == 0:
                print("线程" + str(self.thread_id) + "下载完成，本线程下载文件" + str(self.download_num))
                download_lock.release()
                return
            elif not download_list:
                download_lock.release()
                time.sleep(5)
                continue

            self.task = download_list.pop(0)
            download_lock.release()

            if not self.download_pic():
                print("[fail]"+self.task.path)
                self.task.fail_times += 1
                if self.task.fail_times <= MAX_TRY_TIMES:
                    download_lock.acquire()
                    download_list.append(self.task)
                    download_lock.release()
                else:
                    fail_lock.acquire()
                    fail_list.append(self.task)
                    fail_lock.release()
            else:
                self.download_num += 1
                # print("[OK] "+self.task.path)

    def download_pic(self):
        try:
            pic = requests.get(self.task.url, headers=self.task.header)
        except Exception as e:
            print(e)
            return False

        # print(pic.status_code)
        if pic.status_code == 200:
            with open(self.task.path, 'wb') as f:
                f.write(pic.content)
            return True
        else:
            return False


class Pixiv:
    def __init__(self):
        self.folder = 'PixivImage'
        self.web_coding = 'utf-8'
        self.data_low = []
        self.num = 0

    def login(self, session_raw):
        session = re.search(r"\d{8}_.{32}", session_raw).group()
        if session is None:
            print("无法识别PHPSESSID")
        DefaultHeader["Cookie"] = "PHPSESSID=" + str(session) + ";"
        print("Login Success", session)

    def get_user_dic(self, user_id, if_download=(False, False)):
        global DefaultHeader
        header = DefaultHeader
        url = "https://www.pixiv.net/ajax/user/{}/profile/all".format(str(user_id))
        page = requests.get(url, headers=header)

        if page.status_code != 200:
            raise Exception("Pixiv Page:", page.status_code)

        global false, null, true
        author_img_dic = eval(page.content)['body']
        # print(author_img_dic)

        if author_img_dic['illusts'] and if_download[0]:
            illusts_list = [key for key, value in author_img_dic['illusts'].items()]
            for item in illusts_list:
                add_list.append(item)
        if author_img_dic['manga'] and if_download[1]:
            manga_list = [key for key, value in author_img_dic['manga'].items()]
            for item in manga_list:
                add_list.append(item)

    def get_recommend_by_artworks(self, artworks_id, recommend_num=100):
        global DefaultHeader
        header = DefaultHeader
        url = "https://www.pixiv.net/ajax/illust/{}/recommend/init?limit=18".format(str(artworks_id))
        page = requests.get(url, headers=header)

        if page.status_code != 200:
            raise Exception("Pixiv Page:", page.status_code)

        global false, null, true
        recommend_list = eval(page.content)['body']
        print(recommend_list)

        for item in recommend_list["nextIds"][:min(recommend_num, len(recommend_list["nextIds"]))]:
            add_list.append(item)

    # 直接获取推荐似乎需要cookies，暂未研究
    # def get_recommend(self, recommend_type="illust", recommend_num = 100, recommend_mode="all"):
    #     if recommend_type not in ["illust"] or recommend_mode not in ["all", "safe", "r18"]:
    #         print("type error")
    #         return
    #     global DefaultHeader
    #     header = DefaultHeader
    #     url = "https://www.pixiv.net/rpc/recommender.php?type={}&sample_illusts=auto&num_recommendations={}&page=discovery&mode={}".format(recommend_type, str(recommend_num), recommend_mode)
    #     page = requests.get(url, headers=header)
    #
    #     if page.status_code != 200:
    #         raise Exception("Pixiv Page:", page.status_code)
    #
    #     global false, null, true
    #     recommend_list = eval(page.content)['body']
    #     print(recommend_list)


def main():
    thread_list = list()
    for i in range(ADD_THREAD_MAX_NUM):
        t = ThreadAdder(i)
        t.start()
        thread_list.append(t)
    for i in range(DOWNLOAD_THREAD_MAX_NUM):
        t = ThreadDownloader(i)
        t.start()
        thread_list.append(t)

    p = Pixiv()

    while(True):
        target_type = input("""
请选择数字：
1.下载单个artworks
2.下载某user的全部artworks(包括illusts和manga)
3.下载某user的全部illusts
4.下载某user的全部manga
5.下载某artworks的相关推荐
6.登录(仅支持输入PHPSESSID登录)
7.退出(选择后不会立刻退出，会等当前下载任务完成后自动退出)
""")

        if target_type == "1":
            target_data = input("请输入artworks_id:")
            global add_list
            add_list.append(target_data)
        elif target_type == "2":
            target_data = input("请输入user_id:")
            p.get_user_dic(target_data, (True, True))
        elif target_type == "3":
            target_data = input("请输入user_id:")
            p.get_user_dic(target_data, (True, False))
        elif target_type == "4":
            target_data = input("请输入user_id:")
            p.get_user_dic(target_data, (False, True))
        elif target_type == "5":
            target_data = input("请输入artworks_id:")
            target_num = input("请输入下载相关的artworks数量:")
            p.get_recommend_by_artworks(target_data, int(target_num))
        elif target_type == "6":
            target_data = input("请输入PHPSESSID:")
            p.login(target_data)
        elif target_type == "7":
            break
        else:
            print("输入无法识别，请输入数字")

    global add_finish_flag
    add_finish_flag = True
    for t in thread_list:
        t.join


if __name__ == "__main__":
    main()


