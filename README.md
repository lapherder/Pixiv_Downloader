# Pixiv_Downloader

这是一个Pixiv的多线程下载器。本来想做成爬虫的，但感觉自己用不到爬虫，就做成下载器了，有需要的话这个下载器一改就是爬虫。

喜欢的话点个star吧

### 使用说明：

1、请自行解决连接Pixiv的问题

2、虽然提供了登录功能，但绝大多数情况不需要，除非你要下载那种图片（不登陆会404那种）

3、如果ThreadAdder线程有报错强行结束的，那么ThreadDownloader线程会无法结束，因为无法判断ThreadAdder线程是否全部结束。

### 框架说明：

使用了4个Class：

Pixiv类：用来获取artworks_id，根据用户输入请求获取相对应的artworks，并放入add_list。

DownloadTask类：存储图片的信息，包括URL、请求头、保存位置。

ThreadAdder类：线程类，从add_list中取出artworks_id，处理后生成对应的DownloadTask，放入download_list。

ThreadDownloader类：线程类，从download_list中取出DownloadTask并下载。



主线程调用Pixiv类（未画出），其他线程的逻辑如下：

![Pixiv_Downloader](.\res\Pixiv_Downloader.png)



### 常量说明：

| 常量                    | 说明                                                         |
| :---------------------- | ------------------------------------------------------------ |
| ADD_THREAD_MAX_NUM      | 最大添加线程数                                               |
| DOWNLOAD_THREAD_MAX_NUM | 最大下载线程数                                               |
| MAX_TRY_TIMES           | 下载失败最大重试次数                                         |
| DIR_PATH                | 文件保存地址                                                 |
| USE_DIR_MARGIN          | 单个artworks内的图片数量超过该值时，单独保存为文件夹，否则全部放入默认路径 |


​						

