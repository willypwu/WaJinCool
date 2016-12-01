#coding=utf-8
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

import json
import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

env = Environment(loader=FileSystemLoader('./'))
    
class MoneyRecord(ndb.Model):
    name = ndb.StringProperty()
    gen_date = ndb.DateTimeProperty(auto_now_add=True)
    user_date = ndb.StringProperty()
    category = ndb.StringProperty()
    money = ndb.IntegerProperty()  
    comment = ndb.StringProperty()
    
    @classmethod
    def query_record_by_name(cls, user_name):
        return cls.query(MoneyRecord.name==user_name).order(cls.user_date)    
    @classmethod
    def query_record_by_name_and_category(cls, user_name, cate):
        return cls.query(ndb.AND(MoneyRecord.name==user_name, MoneyRecord.category==cate)).order(cls.user_date)

class CategoryOptions(ndb.Model):
    name = ndb.StringProperty()
    categories = ndb.StringProperty()
    
    @classmethod
    def query_categories_by_name(cls, user_name):
        return cls.query(CategoryOptions.name==user_name)
    
class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        logging.info("*** MainPage *** " + str(user) + ", " + str(users.is_current_user_admin()))
        if users.is_current_user_admin() == False:
            self.response.write('You are not an administrator.')
        user_cat = CategoryOptions.query_categories_by_name(str(user)).fetch()
        if len(user_cat) == 0:
            r = CategoryOptions(
                name=str(user),
                categories = "in.薪資;in.其他收入;out.餐飲;out.其他支出;out.交通"
            )
            rk = r.put()
            
        t = env.get_template('html/main.html')
        self.response.write(t.render(""))
         
class MoneyRecordHandler(webapp2.RequestHandler):
    def get(self):         
        user = users.get_current_user()
        select_year = self.request.get('select_year')
        select_month = self.request.get('select_month')
        logging.info("*** MoneyRecordHandler get *** " + str(user) + ", " + select_year + ", " + select_month)
        records = MoneyRecord.query_record_by_name(str(user)).fetch()
        content = []
        count = 0
        filter_year_and_month = str(select_year+"-"+select_month)
        for record in records:
            logging.info("record // name = %s , date = %s, money = %d, category = %s, comment =%s, id = %s",
                         record.name, record.user_date, record.money, record.category, record.comment, record.key)
            if filter_year_and_month in record.user_date :
                logging.info("matched data : " + record.user_date)
                content.append({
                    "id":record.key.urlsafe(), 
                    "date": record.user_date, 
                      "cost": record.money, 
                      "category": record.category,
                      "comment": record.comment
                })
                count = count + 1
        result = {
            "user":str(user),
            "count":count, 
            "content":content
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def post(self):            
        logging.info("*** MoneyRecordHandler post ***")        
        logging.info("post // user_date : %s , cost : %s , category : %s , comment : %s", 
                     self.request.get('date'), self.request.get('cost'), self.request.get('category'), self.request.get('comment'))
        
        user = users.get_current_user()
        r = MoneyRecord(
            name=str(user),
            user_date = self.request.get('date'),
            money = int(self.request.get('cost')), 
            category= self.request.get('category'), 
            comment = self.request.get('comment'))
        rk = r.put()

        result = {
            "id":rk.urlsafe(),
            "date": self.request.get('date'), 
            "cost": self.request.get('cost'), 
            "category": self.request.get('category'),
            "comment": self.request.get('comment')} 
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def delete(self, id):            
        logging.info("*** MoneyRecordHandler delete *** " + id)  
        ndb.Key(urlsafe=id).delete()
        result = {
            "id":id, 
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def put(self, id):            
        logging.info("*** MoneyRecordHandler put ***" + id)  
        logging.info("put // user_date : %s , cost : %s , category : %s , comment : %s", 
                     self.request.get('date'), self.request.get('cost'), self.request.get('category'), self.request.get('comment'))
        updateItem = ndb.Key(urlsafe=id).get()
        updateItem.user_date = self.request.get('date')
        updateItem.money = int(self.request.get('cost'))
        updateItem.category = self.request.get('category')
        updateItem.comment = self.request.get('comment')
        updateItem.put()
        
        result = {
            "date": self.request.get('date'), 
            "cost": self.request.get('cost'), 
            "category": self.request.get('category'),
            "comment": self.request.get('comment')} 
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
        
class CategoryHandler(webapp2.RequestHandler):
    def get(self): 
        user = users.get_current_user()
        logging.info("*** CategoryHandler get *** " + str(user))
        user_cat = CategoryOptions.query_categories_by_name(str(user)).fetch()
                
        split_categories = user_cat[0].categories.split(";")
        categories = []
        for c in split_categories:
            categories.append({
                "cate":c.encode('utf-8')
            })
        result = {
            "user":str(user),
            "count":len(split_categories),
            "categories":categories
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def post(self):            
        user = users.get_current_user()
        logging.info("*** CategoryHandler post *** " + str(user))
        logging.info("post // cate name : %s , cate type : %s", self.request.get('cate_name'), self.request.get('cate_type'))
        addCate = self.request.get('cate_type') + "." + self.request.get('cate_name')
        user_cat = CategoryOptions.query_categories_by_name(str(user)).fetch()
        updateItem = user_cat[0]
        updateItem.categories = updateItem.categories + ";" + addCate        
        updateItem.put()
        
        user_cat = CategoryOptions.query_categories_by_name(str(user)).fetch()                
        split_categories = user_cat[0].categories.split(";")
        categories = []
        for c in split_categories:
            categories.append({
                "cate":c.encode('utf-8')
            })
            
        result = {
            "user":str(user),
            "count":len(split_categories),
            "categories":categories
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
class MoneyStatisticsHandler(webapp2.RequestHandler):
    def get(self): 
        user = users.get_current_user()
        logging.info("*** MoneyStatisticsHandler get *** " + str(user))
        # year+month
        select_year = self.request.get('select_year')
        select_month = self.request.get('select_month')
        filter_year_and_month = str(select_year+"-"+select_month)        
        # get all cates
        user_cat = CategoryOptions.query_categories_by_name(str(user)).fetch()        
        split_categories = user_cat[0].categories.split(";")
        # get corresponding record
        categories_data = []
        in_count = 0
        out_count = 0
        for c in split_categories:
            split_cate = c.encode('utf-8').split(".")
            records = MoneyRecord.query_record_by_name_and_category(str(user), c.encode('utf-8')).fetch()
            money_count = 0
            for record in records :
                if filter_year_and_month in record.user_date :
                    money_count = money_count + record.money 
                    # in or out
                    if split_cate[0]=='in' :
                        in_count = in_count + record.money 
                    else :
                        out_count = out_count + record.money 
            # save as categories_data
            categories_data.append({
                "cate":c.encode('utf-8'),
                "money_count":money_count
            })
                
                         
        result = {
            "user":str(user),
            "in_count":in_count,
            "out_count":out_count,
            "count":len(split_categories),
            "categories_data":categories_data
        }
        logging.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~" + str(result))
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
        

        
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/moneyHandle', MoneyRecordHandler),
    ('/moneyHandle/([^/]+)?', MoneyRecordHandler),
    ('/categories', CategoryHandler),
    ('/statistics', MoneyStatisticsHandler),
], debug=True)
