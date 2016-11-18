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

class Account(ndb.Model):
    username = ndb.StringProperty()
    userid = ndb.IntegerProperty()
    email = ndb.StringProperty()
    
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
    
    
class MainPage(webapp2.RequestHandler):
    def get(self):
        t = env.get_template('html/main.html')
        self.response.write(t.render(""))
         
class MoneyRecordHandler(webapp2.RequestHandler):
    
    def get(self):         
        user = users.get_current_user()
        logging.info("*** get *** " + str(user))
        records = MoneyRecord.query_record_by_name(str(user)).fetch()
        content = []
        for record in records:
            logging.info("record // name = %s , date = %s, money = %d, category = %s, comment =%s, id = %s",
                         record.name, record.user_date, record.money, record.category, record.comment, record.key)
            content.append({
                "id":record.key.urlsafe(), 
                "date": record.user_date, 
                  "cost": record.money, 
                  "category": record.category,
                  "comment": record.comment
            })
        result = {
            "user":str(user),
            "count":len(records), 
            "content":content
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def post(self):            
        logging.info("*** post ***")        
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
        logging.info("*** delete *** " + id)  
        ndb.Key(urlsafe=id).delete()
        result = {
            "id":id, 
        }
        json_obj = json.dumps(result)
        self.response.out.write(json_obj)
        
    def put(self, id):            
        logging.info("*** put ***" + id)  
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
        
            
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/moneyHandle', MoneyRecordHandler),
    ('/moneyHandle/([^/]+)?', MoneyRecordHandler),
], debug=True)