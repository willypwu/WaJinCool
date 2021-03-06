# coding=utf-8
# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
from jinja2 import Environment, FileSystemLoader

from google.appengine.ext import ndb
from google.appengine.api import users
from datetime import datetime

import uuid
import time
import json
import logging
import sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

env = Environment(loader=FileSystemLoader('./'))


class Token(ndb.Model):
    uuid = ndb.StringProperty()
    account_id = ndb.StringProperty()


class UserAccount(ndb.Model):
    name = ndb.StringProperty()
    gmail = ndb.StringProperty()
    categories = ndb.StringProperty()


class MoneyRecord(ndb.Model):
    gen_date = ndb.DateTimeProperty(auto_now_add=True)
    user_date = ndb.StringProperty()
    category = ndb.StringProperty()
    money = ndb.IntegerProperty()  
    comment = ndb.StringProperty()
    user_account_key = ndb.KeyProperty(kind=UserAccount)

    @classmethod
    def query_record_by_name(cls, user_account_key):
        return cls.query(MoneyRecord.user_account_key == user_account_key).order(cls.user_date)

    @classmethod
    def query_record_by_name_and_category(cls, user_account_key, cate):
        return cls.query(ndb.AND(MoneyRecord.user_account_key == user_account_key, MoneyRecord.category == cate)).order(cls.user_date)


class BaseHandler(webapp2.RequestHandler):
    original_locale = "en"

    def __init__(self, request, response):
        self.initialize(request, response)

    def valid_user(self):
        # get user_id by cookie
        token_uuid = self.request.cookies.get('user_id')
        token = Token.query(Token.uuid == str(token_uuid)).fetch(1)[0]
        logging.info("valid_user // uuid : " + str(token_uuid) + ", token : " + str(token))
        if token is None:
            self.error(403)
            return None
        user_id = token.account_id
        if user_id is None:
            self.error(403)
            return None
        user_account = ndb.Key(UserAccount, long(user_id)).get()
        if user_account is None:
            self.error(403)
            return None
        return user_account


class MainPage(webapp2.RequestHandler):
    def get(self):
        user_gmail = users.get_current_user()
        logging.info("*** MainPage *** " + str(user_gmail) + ", " + str(users.is_current_user_admin()))
        if users.is_current_user_admin() is False:
            self.response.write('You are not an administrator.')

        results = UserAccount.query(UserAccount.gmail == str(user_gmail)).fetch(1)
        user_account = results[0] if len(results) > 0 else None
        token = Token.query(Token.account_id == str(str(user_account.key.integer_id()))).fetch(1)[0] if len(results) > 0 else None
        if user_account is None or token is None:
            # new user account
            user_account = UserAccount(
                name=str(user_gmail),
                gmail=str(user_gmail),
                categories="in.薪資;in.其他收入;out.餐飲;out.其他支出;out.交通"
            )
            user_account.put()
            # gen token
            random_id = uuid.uuid4()
            token = Token(
                uuid=str(random_id),
                account_id=str(user_account.key.integer_id())
            )
            token.put()

            # waiting db create
            time.sleep(3)
        logging.info("*** MainPage *** cookie value (user id) // " + str(user_account.key.integer_id()) + ", " + str(token.uuid))
        self.response.set_cookie('user_id', str(token.uuid), max_age=360, path='/',
                                 domain='localhost', secure=False)
        t = env.get_template('html/main.html')
        self.response.write(t.render(""))


class MoneyRecordHandler(BaseHandler):
    def get(self):
        user_account = self.valid_user()
        if user_account is None:
            logging.info("invalid user")
            return

        select_year = self.request.get('select_year')
        select_month = self.request.get('select_month')
        logging.info("*** MoneyRecordHandler get *** " + select_year + ", " + select_month)

        records = MoneyRecord.query_record_by_name(user_account.key).fetch()
        content = []
        count = 0
        filter_year_and_month = str(select_year+"-"+select_month)
        for record in records:
            logging.info("record // name = %s , date = %s, money = %d, category = %s, comment =%s, id = %s",
                         record.user_account_key.get().name, record.user_date, record.money,
                         record.category, record.comment, record.key)
            if filter_year_and_month in record.user_date:
                logging.info("matched data : " + record.user_date)
                content.append({
                    "id": record.key.urlsafe(),
                    "date": record.user_date, 
                    "cost": record.money,
                    "category": record.category,
                    "comment": record.comment
                })
                count = count + 1
        result = {
            "user": str(user_account.name),
            "count": count,
            "content": content
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def post(self):
        user_account = self.valid_user()
        if user_account is None:
            logging.info("invalid user")
            return

        logging.info("*** MoneyRecordHandler post ***")        
        logging.info("post // user_date : %s , cost : %s , category : %s , comment : %s", 
                     self.request.get('date'), self.request.get('cost'),
                     self.request.get('category'), self.request.get('comment'))

        r = MoneyRecord(
            user_date=self.request.get('date'),
            money=int(self.request.get('cost')),
            category=self.request.get('category'),
            comment=self.request.get('comment'),
            user_account_key=user_account.key)
        rk = r.put()

        result = {
            "id": rk.urlsafe(),
            "date": self.request.get('date'), 
            "cost": self.request.get('cost'), 
            "category": self.request.get('category'),
            "comment": self.request.get('comment')} 
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def delete(self, id):
        user_account = self.valid_user()
        if user_account is None:
            logging.info("invalid user")
            return

        logging.info("*** MoneyRecordHandler delete *** " + id)  
        ndb.Key(urlsafe=id).delete()
        result = {
            "id": id,
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def put(self, id):
        user_account = self.valid_user()
        if user_account is None:
            logging.info("invalid user")
            return

        logging.info("*** MoneyRecordHandler put ***" + id)  
        logging.info("put // user_date : %s , cost : %s , category : %s , comment : %s", 
                     self.request.get('date'), self.request.get('cost'),
                     self.request.get('category'), self.request.get('comment'))
        update_item = ndb.Key(urlsafe=id).get()
        update_item.user_date = self.request.get('date')
        update_item.money = int(self.request.get('cost'))
        update_item.category = self.request.get('category')
        update_item.comment = self.request.get('comment')
        update_item.put()
        
        result = {
            "date": self.request.get('date'), 
            "cost": self.request.get('cost'), 
            "category": self.request.get('category'),
            "comment": self.request.get('comment')} 
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
        
class CategoryHandler(BaseHandler):
    def get(self):
        user_account = self.valid_user()
        if user_account is None:
            logging.info("invalid user")
            return

        logging.info("*** CategoryHandler get *** " + str(user_account.name))

        split_categories = user_account.categories.split(";")
        categories = []
        for c in split_categories:
            categories.append({
                "cate": c.encode('utf-8')
            })
        result = {
            "user": str(user_account.name),
            "count": len(split_categories),
            "categories": categories
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def post(self):
        user_account = self.valid_user()
        if user_account is None:
            logging.info("invalid user")
            return

        logging.info("*** CategoryHandler post *** " + str(user_account.name))
        logging.info("post // cate name : %s , cate type : %s",
                     self.request.get('cate_name'), self.request.get('cate_type'))
        add_cate = self.request.get('cate_type') + "." + self.request.get('cate_name')

        update_item = user_account
        update_item.categories = update_item.categories + ";" + add_cate
        update_item.put()

        split_categories = user_account.categories.split(";")
        categories = []
        for c in split_categories:
            categories.append({
                "cate": c.encode('utf-8')
            })
            
        result = {
            "user": str(user_account.name),
            "count": len(split_categories),
            "categories": categories
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)


class MoneyStatisticsHandler(BaseHandler):
    def get(self):
        user_account = self.valid_user()
        if user_account is None:
            logging.info("invalid user")
            return

        logging.info("*** MoneyStatisticsHandler get *** " + str(user_account.name))
        # year+month
        select_year = self.request.get('select_year')
        select_month = self.request.get('select_month')
        filter_year_and_month = str(select_year+"-"+select_month)        
        # get all cates
        split_categories = user_account.categories.split(";")
        # get corresponding record
        categories_data = []
        in_count = 0
        out_count = 0

        for c in split_categories:
            split_cate = c.encode('utf-8').split(".")
            records = MoneyRecord.query_record_by_name_and_category(user_account.key, c.encode('utf-8')).fetch()
            money_count = 0
            for record in records:
                if filter_year_and_month in record.user_date:
                    money_count = money_count + record.money 
                    # in or out
                    if split_cate[0] == 'in':
                        in_count = in_count + record.money 
                    else:
                        out_count = out_count + record.money 
            # save as categories_data
            categories_data.append({
                "cate": c.encode('utf-8'),
                "money_count": money_count
            })

        result = {
            "user": str(user_account.name),
            "in_count": in_count,
            "out_count": out_count,
            "count": len(split_categories),
            "categories_data": categories_data
        }
        logging.info("MoneyStatisticsHandler // all categories : " + str(result))
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/moneyHandle', MoneyRecordHandler),
    ('/moneyHandle/([^/]+)?', MoneyRecordHandler),
    ('/categories', CategoryHandler),
    ('/statistics', MoneyStatisticsHandler),
], debug=True)
