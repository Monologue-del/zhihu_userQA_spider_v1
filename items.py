# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class QuestionItem(scrapy.Item):
    """
        知乎问题Item
        """
    question_id = scrapy.Field()
    topics = scrapy.Field()
    url = scrapy.Field()
    question_title = scrapy.Field()
    content = scrapy.Field()
    answer_num = scrapy.Field()
    comments_num = scrapy.Field()
    watch_user_num = scrapy.Field()
    click_num = scrapy.Field()
    crawl_time = scrapy.Field()


class AnswerItem(scrapy.Item):
    """
    答案信息
    """
    answer_id = scrapy.Field()
    answer_url = scrapy.Field()
    question_id = scrapy.Field()
    question_title = scrapy.Field()
    author_id = scrapy.Field()
    author_name = scrapy.Field()
    content = scrapy.Field()
    praise_num = scrapy.Field()
    comments_num = scrapy.Field()
    create_time = scrapy.Field()
    crawl_time = scrapy.Field()
    update_time = scrapy.Field()
