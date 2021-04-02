import scrapy
import json
import time
from bs4 import BeautifulSoup
from zhihuQA.items import AnswerItem, QuestionItem
import datetime
from zhihuQA.settings import cookie, DATETIME_FORMAT, DATE_FORMAT
from scrapy.loader import ItemLoader


class ZhihuSpiderSpider(scrapy.Spider):
    name = 'zhihuSpider'
    allowed_domains = ["www.zhihu.com", "api.zhihu.com"]
    # 起始用户id
    start_user = 'wangyizhi'
    # 用户信息的url
    user_url = 'https://api.zhihu.com/people/{user}'
    # 关注列表的url
    followees_url = "https://www.zhihu.com/people/{user}/following?page={page}"
    # 粉丝列表的url
    followers_url = 'https://www.zhihu.com/people/{user}/followers?page={page}'
    # 用户动态的url
    user_action_url = "https://www.zhihu.com/api/v3/moments/{user}/activities?"
    # 答案的url
    answers_url = "https://www.zhihu.com/api/v4/questions/{question_id}/answers?include=data%5B%2A%5D.is_normal%2Cadmin_closed_comment%2Creward_info%2Cis_collapsed%2Cannotation_action%2Cannotation_detail%2Ccollapse_reason%2Cis_sticky%2Ccollapsed_by%2Csuggest_edit%2Ccomment_count%2Ccan_comment%2Ccontent%2Ceditable_content%2Cattachment%2Cvoteup_count%2Creshipment_settings%2Ccomment_permission%2Ccreated_time%2Cupdated_time%2Creview_info%2Crelevant_info%2Cquestion%2Cexcerpt%2Cis_labeled%2Cpaid_info%2Cpaid_info_content%2Crelationship.is_authorized%2Cis_author%2Cvoting%2Cis_thanked%2Cis_nothelp%2Cis_recognized%3Bdata%5B%2A%5D.mark_infos%5B%2A%5D.url%3Bdata%5B%2A%5D.author.follower_count%2Cbadge%5B%2A%5D.topics%3Bdata%5B%2A%5D.settings.table_of_content.enabled&limit=5&offset=5&platform=desktop"
    # 问题的url
    questions_url = "https://www.zhihu.com/question/{question_id}"

    def start_requests(self):
        yield scrapy.Request(self.user_url.format(user=self.start_user), headers={
            'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0'},
                             callback=self.parse_user)
        # time.sleep(1)

    def parse_user(self, response):
        """
        爬取用户基本信息；
        调用parse_followees和parse_followers爬取关注者和粉丝列表
        :param response:
        :return:
        """
        result = json.loads(response.text)
        # 提取用户基本信息
        user_token = result['url_token']

        yield scrapy.Request(self.user_action_url.format(user=user_token), callback=self.parse_action,
                             cookies=cookie)

        # 判断关注者列表是否为空
        if result["following_count"] > 0:
            yield scrapy.Request(self.followees_url.format(user=user_token, page=1),
                                 callback=self.parse_followees)
            # time.sleep(1)

        # 判断粉丝列表是否为空
        if result["follower_count"] > 0:
            yield scrapy.Request(self.followers_url.format(user=user_token, page=1),
                                 callback=self.parse_followers)
            # time.sleep(1)

    def parse_action(self, response):
        """
        爬取用户动态
        :param response:
        :return:
        """
        action_json = json.loads(response.text)
        is_end = action_json['paging']['is_end']
        # 判断用户是否有动态
        if not is_end:
            next_url = action_json['paging']['next']

            # 提取用户动态
            for action in action_json['data']:
                verb = action['verb']

                # 只爬取“赞同回答”、“回答问题”、“添加问题”、“关注问题”四种情形，其余情形跳过循环
                if verb == "ANSWER_VOTE_UP" or verb == "ANSWER_CREATE":
                    # “赞同回答”与“回答问题”的数据解析方式相同，“问题提出者信息”+“问题信息”
                    # 内容的创作时间
                    question_id = action['target']['question']['id']
                    yield scrapy.Request(self.answers_url.format(question_id=question_id),
                                         callback=self.parse_answer)
                    yield scrapy.Request(self.questions_url.format(question_id=question_id),
                                         callback=self.parse_question)
                elif verb == "QUESTION_FOLLOW" or verb == "QUESTION_CREATE":
                    # “添加问题”与“关注问题”的数据解析方式相同，target_question的信息=target本身
                    # 内容的创作时间
                    question_id = action['target']['id']
                    yield scrapy.Request(self.questions_url.format(question_id=question_id),
                                         callback=self.parse_question)
                else:
                    continue

            if not is_end:
                yield scrapy.Request(next_url, callback=self.parse_action)

    def parse_followees(self, response):
        """
        解析关注者列表，得到用户url；
        调用parse_user爬取用户信息
        :param response:
        :return:
        """
        followees_list = response.xpath('//div[@class="List-item"]')
        for followee in followees_list:
            try:
                url_token = followee.xpath('./div/div/div[2]/h2//a/@href').extract_first()
                url_type = url_token.split('/')[-2]
                if str(url_type) == 'people':
                    user_token = url_token.split('/')[-1]
                    # print(user_token)
                    yield scrapy.Request(self.user_url.format(user=user_token), callback=self.parse_user)
                else:
                    continue
            except:
                continue

        zhihu_soup = BeautifulSoup(response.text, "lxml")
        page_current = zhihu_soup.find("button",
                                       class_="Button PaginationButton PaginationButton--current Button--plain")
        try:
            page_next = zhihu_soup.find("button", class_="Button PaginationButton PaginationButton-next Button--plain")
        except:
            page_next = None

        if not page_next == None:
            user = response.url.split('/')[-2]
            next_page = self.followees_url.format(
                user=user,
                page=str(int(page_current.text) + 1))
            # 获取下一页的地址然后通过yield继续返回Request请求，继续请求自己再次获取下页中的信息
            yield scrapy.Request(next_page, callback=self.parse_followers)

    def parse_followers(self, response):
        """
        爬取粉丝列表，得到用户url，调用parse_user爬取用户信息
        :param response:
        :return:
        """
        followers_list = response.xpath('//div[@class="List-item"]')
        for follower in followers_list:
            try:
                url_token = follower.xpath('./div/div/div[2]/h2//a/@href').extract_first()
                url_type = url_token.split('/')[-2]
                if str(url_type) == 'people':
                    user_token = url_token.split('/')[-1]
                    # print(user_token)
                    yield scrapy.Request(self.user_url.format(user=user_token), callback=self.parse_user)
                    yield scrapy.Request(self.user_action_url.format(user=user_token), callback=self.parse_action)
                else:
                    continue
            except:
                continue

        zhihu_soup = BeautifulSoup(response.text, "lxml")
        page_current = zhihu_soup.find("button",
                                       class_="Button PaginationButton PaginationButton--current Button--plain")
        try:
            page_next = zhihu_soup.find("button", class_="Button PaginationButton PaginationButton-next Button--plain")
        except:
            page_next = None

        if not page_next == None:
            user = response.url.split('/')[-2]
            next_page = self.followers_url.format(
                user=user,
                page=str(int(page_current.text) + 1))
            # 获取下一页的地址然后通过yield继续返回Request请求，继续请求自己再次获取下页中的信息
            yield scrapy.Request(next_page, self.parse_followers)

    def parse_question(self, response):
        """
        解析问题页面，提取问题信息
        :param response:
        :return:
        """
        question_id = response.url.split('/')[-1]
        question_id = ''.join(question_id)
        # 使用ItemLoader获取数据
        item_loader = ItemLoader(item=QuestionItem(), response=response)

        item_loader.add_css("question_title", "h1.QuestionHeader-title::text")
        try:
            item_loader.add_xpath("content", '//div[@class="css-eew49z"]/div/div/span//text()')
        except:
            item_loader.add_value("content", '无')
        item_loader.add_value("url", response.url)
        item_loader.add_value("question_id", question_id)
        try:
            item_loader.add_css("answer_num", ".List-headerText span::text")
        except:
            item_loader.add_value("answer_num", None)
        item_loader.add_css("comments_num", ".QuestionHeader-Comment button::text")
        item_loader.add_xpath("watch_user_num",
                              '//*[@id="root"]/div/main/div/div[1]/div[2]/div[1]/div[2]/div/div/div/button/div/strong/text()')
        item_loader.add_css("watch_user_num", ".NumberBoard-itemValue::text")
        item_loader.add_css("topics", ".QuestionHeader-topics .Popover div::text")

        question_item = item_loader.load_item()
        yield question_item

    def parse_answer(self, response):
        """
                解析答案页面，提取答案信息
                :param response:
                :return:
                """
        # 处理question的answer
        ans_json = json.loads(response.text)
        is_end = ans_json['paging']['is_end']
        next_url = ans_json['paging']['next']

        # 提取answer的具体字段
        for answer in ans_json['data']:
            answer_item = AnswerItem()

            answer_item["answer_id"] = answer["id"]
            answer_item["answer_url"] = answer["url"]
            answer_item["question_id"] = answer["question"]["id"]
            answer_item["question_title"] = answer["question"]["title"]
            answer_item["author_id"] = answer["author"]["id"] if "id" in answer["author"] else None
            answer_item["author_name"] = answer["author"]["name"] if "name" in answer["author"] else None
            answer_item["content"] = answer["content"] if "content" in answer else None
            answer_item["praise_num"] = answer["voteup_count"]
            answer_item["comments_num"] = answer["comment_count"]
            answer_item["create_time"] = datetime.datetime.fromtimestamp(answer["created_time"]).strftime(
                DATETIME_FORMAT)
            answer_item["update_time"] = datetime.datetime.fromtimestamp(answer["updated_time"]).strftime(
                DATETIME_FORMAT)
            answer_item["crawl_time"] = datetime.datetime.now().strftime(DATETIME_FORMAT)

            yield answer_item

        if not is_end:
            yield scrapy.Request(next_url, callback=self.parse_answer)
