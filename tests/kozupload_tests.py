# -*- coding: utf-8 -*-
#Kozupload test process which will test all features from Kozupload


import os
import sys
import unittest
import tempfile
from flask.ext.sqlalchemy import SQLAlchemy
from functools import wraps
from flask import session
from StringIO import StringIO
from re import search
from sqlalchemy import desc
import psycopg2 as ppg
from contextlib import closing

PATH = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PATH)

TEST_USERNAME = "test_user"
TEST_PASSWORD = "default"

os.putenv('APP_SETTINGS', os.path.join(PATH, 'tests', 'config.py'))

import index

def with_client(function):
    """Create the test_client."""
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        """Decorator for the client login."""
        with index.app.test_client() as client:
            client.post('login', data={'username': 'test_user',
                                        'password': 'default'})
            return function(self, client=client, *args, **kwargs)
    return wrapper


class KozuploadTestCase(unittest.TestCase):

    def setUp(self):
        self.app = index.app.test_client()
        self.reset_db()

    def reset_db(self):
        path = os.path.join(PATH, 'tests', 'sql', 'database.sql')
        database = "dbname=kozupload-test user=kozupload password="
        conn = ppg.connect(database)
        cursor = conn.cursor()
        with index.app.open_resource(path) as f:
            #'psycopg2._psycopg.cursor' object has no attribute 'executescript'
            cursor.executescript(f.read())
        cursor.commit()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def register(self, username, password, password2):
        return self.app.post('/register', data=dict(
            username=username,
            password=password,
            password2=password2
        ), follow_redirects=True)

    def test_index_page(self):
        """Test the index page."""
        r = self.app.get('/')
        assert 'Un hébergement pour tous vos fichiers!' in r.data

    def test_register_page(self):
        """Test the register page."""
        r = self.app.get('/register')
        assert 'Register form' in r.data
        assert 'Username' in r.data
        assert 'Password' in r.data
        assert 'Password again:' in r.data

    def test_register(self):
        """Test the register."""
        r = self.register("", "", "")
        assert 'You have to fill the entire form first !' in r.data
        r = self.register(TEST_USERNAME, "", "")
        assert 'You have to fill the entire form first !' in r.data
        r = self.register(TEST_USERNAME, TEST_PASSWORD, "")
        assert 'You have to fill the entire form first !' in r.data
        index.del_member(TEST_USERNAME)
        r = self.register(TEST_USERNAME, TEST_PASSWORD, TEST_PASSWORD)
        assert 'Welcome on Kozupload,' in r.data
        assert 'Your folder is empty !' in r.data
        r = self.register("Citizen", "1345", "1345")
        assert 'This username is already taken !' in r.data

    def test_login(self):
        """Test the login."""
        r = self.login("", "")
        assert 'Invalid username/password !' in r.data
        r = self.login(TEST_USERNAME + "x", "")
        assert 'Invalid username/password !' in r.data
        r = self.login(TEST_USERNAME + "x", TEST_PASSWORD)
        assert 'Invalid username/password !' in r.data
        r = self.login(TEST_USERNAME, TEST_PASSWORD + "x")
        assert 'Invalid username/password !' in r.data
        r = self.login(TEST_USERNAME, TEST_PASSWORD)
        assert 'You were logged in' in r.data
        assert 'My files' in r.data

    @with_client
    def test_logout(self, client):
        """Test the logout."""
        assert 'logged_in' in session
        r = client.get('/logout')
        assert 'logged_in' not in session

    @with_client
    def test_upload(self, client):
        """Test the upload, download and delete."""
        #Upload
        resp = client.post(
            '/upload',
            data = {
                'file': (StringIO('my file contents'), 'hello world.txt'),
            },
            follow_redirects=True
        )
        assert 'hello world.txt' in resp.data
        u_id = User.query.filter_by(owner_id=session['username']).first().id
        print u_id
        f = (File.query
            .filter_by(owner_id=u_id)
            .order_by(id.desc()).first())
#        assert
        #Download
        file_id = None
        start, end = string_find(resp.data, "/delete/")
        if start and end:
            start2, end2 = string_find(resp.data, '"', end)
            if start2 and end2:
                file_id = string_sub(resp.data, end+1, start2-1)
        resp = client.get('/download/%s' % file_id)
        assert '<Response streamed [200 OK]>' in str(resp)
        print resp.status_code
        assert resp.status_code == 200
        #Delete
        resp = client.get('/delete/%s' % file_id, follow_redirects=True)
        assert 'The file has been deleted !' in resp.data



def string_find(strg, what, offset=0):
    lenght = len(strg)
    for k in range(lenght):
        if k >= offset:
            found = True
            for i in range(len(what)):
                if not ( strg[k+i] == what[i] ):
                    found= False
                    break
            if found:
                return k, k+len(what)-1
    return False, False


def string_sub(strg, x, y=False):
    if not x:
        return False
    start = x
    end = y
    lenght = len(strg)
    if y == False or y > lenght:
        end = lenght
    s = ""
    for index in range(lenght):
        if index >= start and index <= end:
            s += strg[index]
        elif index > end:
            break
    return s




if __name__ == '__main__':
    unittest.main()
