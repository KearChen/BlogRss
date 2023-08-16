import sqlite3
import requests
import datetime
import feedparser
import argparse
from dateutil.parser import parse as date_parse
from tqdm import tqdm

API_URL_GET_BLOGGERS = "https://www.blogrss.cn/api/get_bloggers_api.php"
API_URL_WRITE_BLOG = "写入api"

class BlogRssSpider:
    def __init__(self):
        self.conn = sqlite3.connect('blog_rss_data.db')
        self.c = self.conn.cursor()

    def create_database(self):
        # 创建blogs表，包含title、content、publish_date、blogger_id、original_link、description和uploaded字段
        self.c.execute('''CREATE TABLE IF NOT EXISTS blogs
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          title TEXT,
                          content TEXT,
                          publish_date DATETIME,
                          blogger_id INTEGER,
                          original_link TEXT,
                          description TEXT,
                          uploaded INTEGER DEFAULT 0)''')

        # 提交数据库事务
        self.conn.commit()

    def parse_publish_date(self, date_str):
        try:
            publish_date = date_parse(date_str)
            return publish_date.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return ''

    def crawl_rss_data(self, bloggers_data):
        for blogger in bloggers_data:
            blogger_id = blogger['blogger_id']
            rss_url = blogger['rss_address']

            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; BlogRssSpiderV1/1.0; +https://www.blogrss.cn/bot)'
                }
                response = requests.get(rss_url, headers=headers)
                response.raise_for_status()
                feed = feedparser.parse(response.text)

                with tqdm(total=len(feed.entries), desc=f"解析 {blogger['blogger_name']} 的博文", unit="条") as pbar:
                    for entry in feed.entries:
                        title = entry.title
                        content = entry.content[0].value if 'content' in entry else entry.summary
                        publish_date_str = entry.published
                        original_link = entry.link
                        description = entry.summary

                        publish_date = self.parse_publish_date(publish_date_str)
                        if not publish_date:
                            print(f"无法解析日期: {publish_date_str}")
                            continue

                        # 将 publish_date_str 转换为正确的时间格式
                        publish_date = self.parse_publish_date(publish_date_str)

                        # 检查本地数据库中是否已存在相同标题的博文，避免重复写入
                        self.c.execute("SELECT * FROM blogs WHERE title=?", (title,))
                        existing_blog = self.c.fetchone()
                        if existing_blog is not None:
                            continue

                        # 保存数据到数据库
                        self.c.execute("INSERT INTO blogs (blogger_id, title, content, publish_date, original_link, description) VALUES (?, ?, ?, ?, ?, ?)",
                                       (blogger_id, title, content, publish_date, original_link, description))

                        pbar.update(1)

                # 提交数据库事务
                self.conn.commit()
            except requests.exceptions.HTTPError as http_err:
                print(f"HTTP请求错误: {http_err}")
            except Exception as e:
                print(f"解析RSS时发生错误：{str(e)}")
                continue

    def read_data_from_database(self):
        # 从数据库读取博文数据
        self.c.execute("SELECT * FROM blogs WHERE uploaded=0")
        blog_data = self.c.fetchall()
        return blog_data

    def mark_uploaded(self, blog_id):
        # 将指定博文的 uploaded 字段标记为已上传（1）
        self.c.execute("UPDATE blogs SET uploaded=1 WHERE id=?", (blog_id,))
        # 提交数据库事务
        self.conn.commit()

    def write_data_to_blogrss(self, blog_data):
        for data in blog_data:
            blog_id = data[0]
            title = data[1]
            content = data[2]
            publish_date = data[3]
            blogger_id = data[4]
            original_link = data[5]
            description = data[6]

            try:
                # 构建POST请求参数，注意 publish_date 使用 strftime 将时间格式化为字符串
                payload = {
                    'title': title,
                    'content': content,
                    'publish_date': publish_date,
                    'blogger_id': blogger_id,
                    'original_link': original_link,
                    'description': description
                }

                # 发送POST请求将数据写入到blogrss.cn网站
                response = requests.post(API_URL_WRITE_BLOG, data=payload)

                # 检查请求是否成功
                if response.status_code == 200:
                    print(f"成功写入博文: {title}")
                    # 标记博文为已上传
                    self.mark_uploaded(blog_id)
                else:
                    print(f"写入博文失败: {title}")
            except Exception as e:
                print(f"写入博文时发生错误：{str(e)}")
                continue

    def close_connection(self):
        # 关闭数据库连接
        self.conn.close()

def print_menu():
    print("选择要执行的操作：")
    print("1. 建立数据库")
    print("2. 获取博主列表并解析博文写入数据库")
    print("3. 查看本地数据库博文")
    print("4. 上传博文到blogrss")
    print("q. 退出")

def main():
    spider = BlogRssSpider()

    while True:
        print_menu()
        action = input("请输入要执行的操作编号 (1/2/3/4)，或输入 q 退出: ")

        if action == '1':
            # 建立数据库
            spider.create_database()
        elif action == '2':
            # 模拟从API获取博主列表数据
            response = requests.get(API_URL_GET_BLOGGERS)
            if response.status_code == 200:
                bloggers_data = response.json()
            else:
                print(f"从API获取博主列表数据失败: {response.status_code}")
                bloggers_data = []

            # 获取博主列表并解析博文写入数据库
            spider.crawl_rss_data(bloggers_data)
        elif action == '3':
            # 查看本地数据库博文
            blog_data = spider.read_data_from_database()
            for data in blog_data:
                print(data)
        elif action == '4':
            # 上传博文到blogrss
            blog_data = spider.read_data_from_database()
            spider.write_data_to_blogrss(blog_data)
        elif action.lower() == 'q':
            break
        else:
            print("无效的操作，请输入正确的操作编号：1/2/3/4 或输入 q 退出")

    # 关闭数据库连接
    spider.close_connection()

if __name__ == "__main__":
    main()
