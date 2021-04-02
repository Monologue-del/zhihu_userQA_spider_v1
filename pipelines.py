# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from pymongo import MongoClient
from zhihuQA.items import AnswerItem, QuestionItem
from zhihuQA.util.common import extract_num
import datetime
from zhihuQA.settings import DATETIME_FORMAT, DATE_FORMAT


class ZhihuQAPipeline:
    def __init__(self, mongo_uri):
        self.mongo_uri = mongo_uri

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI')
        )

    def open_spider(self, spider):
        # 连接到数据库
        self.client = MongoClient(self.mongo_uri)
        # 连接到指定的数据库
        zhihu_DB = self.client['zhihuQA_DB']
        # 连接到指定表

        self.question_collection = zhihu_DB['questions']
        self.answer_cllection = zhihu_DB['answers']

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        # 存储用户基本信息到MongoDB
        if isinstance(item, AnswerItem):
            self.answer_cllection.update({'id': item['answer_id']}, {'$set': item}, True)
            print('answer', item['answer_id'], '爬取成功')
        elif isinstance(item, QuestionItem):
            question_id = item['question_id'][0]
            try:
                topics = ','.join(item['topics'])
            except:
                topics = None
            url = item['url'][0]
            question_title = item['question_title'][0]
            try:
                content = ''.join(item['content'])
            except:
                content = None
            answer_num = item['answer_num'][0]
            comments_num = extract_num(item['comments_num'][0])
            crawl_time = datetime.datetime.now().strftime(DATETIME_FORMAT)

            if len(item["watch_user_num"]) == 2:
                watch_user_num = int(item["watch_user_num"][0].replace(',', ''))
                click_num = int(item["watch_user_num"][1].replace(',', ''))
            else:
                watch_user_num = int(item["watch_user_num"][0].replace(',', ''))
                click_num = 0

            que_dic = {
                'question_id': question_id,
                'topics': topics,
                'url': url,
                'question_title': question_title,
                'content': content,
                'answer_num': answer_num,
                'comments_num': comments_num,
                'watch_user_num': watch_user_num,
                'click_num': click_num,
                'crawl_time': crawl_time
            }
            self.question_collection.update({'id': que_dic['question_id']}, {'$set': que_dic}, True)
            print('question', question_id, '爬取成功')
