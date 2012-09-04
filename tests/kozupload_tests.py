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

os.environ['APP_SETTINGS'] = os.path.join(PATH, 'tests', 'config.py')

import index


def update_account(client, passw, newpassw, newpassw2):
    return client.post('/my_account', data=dict(
        username=TEST_USERNAME,
        password=passw,
        newpassword=newpassw,
        newpassword2=newpassw2
    ), follow_redirects=True)


def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)


def register(client, username, password, password2):
    return client.post('/register', data=dict(
        username=username,
        password=password,
        password2=password2
    ), follow_redirects=True)


def with_client(connected=True):
    """Create the test_client."""
    def wrapper_wrapper(function):
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            """Decorator for the client login."""
            with index.app.test_client() as client:
                if connected:
                    login(client, 'test_user', 'default')
                return function(self, client=client, *args, **kwargs)
        return wrapper
    return wrapper_wrapper


class KozuploadTestCase(unittest.TestCase):

    def setUp(self):
        path = os.path.join(PATH, 'tests', 'sql', 'database.sql')
        database = "dbname=kozupload-test user=kozupload password="
        with closing(ppg.connect(database)) as db:
            with index.app.open_resource(path) as f:
                db.cursor().execute(f.read())
            db.commit()

    @with_client(connected=False)
    def test_index_page(self, client):
        """Test the index page."""
        r = client.get('/')
        assert 'Un hébergement pour tous vos fichiers!' in r.data

    @with_client(connected=False)
    def test_register_page(self, client):
        """Test the register page."""
        r = client.get('/register')
        assert 'Register form' in r.data
        assert 'Username' in r.data
        assert 'Password' in r.data
        assert 'Password again:' in r.data

    @with_client(connected=False)
    def test_register(self, client):
        """Test the register."""
        r = register(client, "", "", "")
        assert 'You have to fill the entire form first !' in r.data
        r = register(client, TEST_USERNAME, "", "")
        assert 'You have to fill the entire form first !' in r.data
        r = register(client, TEST_USERNAME, TEST_PASSWORD, "")
        assert 'You have to fill the entire form first !' in r.data
        r = register(client, "Citizen", TEST_PASSWORD, TEST_PASSWORD + 'x')
        assert "The 2 passwords doesn't match !" in r.data
        r = register(client, TEST_USERNAME, TEST_PASSWORD, TEST_PASSWORD)
        assert 'This username is already taken !' in r.data
        r = register(client, "Citizen", "1345", "1345")
        assert 'Welcome on Kozupload,' in r.data
        assert 'Your folder is empty !' in r.data

    @with_client(connected=False)
    def test_login(self, client):
        """Test the login."""
        r = login(client, "", "")
        assert 'Invalid username/password !' in r.data
        r = login(client, TEST_USERNAME + "x", "")
        assert 'Invalid username/password !' in r.data
        r = login(client, TEST_USERNAME + "x", TEST_PASSWORD)
        assert 'Invalid username/password !' in r.data
        r = login(client, TEST_USERNAME, TEST_PASSWORD + "x")
        assert 'Invalid username/password !' in r.data
        r = login(client, TEST_USERNAME, TEST_PASSWORD)
        assert 'You were logged in' in r.data
        assert 'My files' in r.data
        r = login(client, TEST_USERNAME, TEST_PASSWORD)
        assert 'You were logged in' not in r.data
        assert 'My files' in r.data

    @with_client()
    def test_logout(self, client):
        """Test the logout."""
        r = client.get('/')
        assert 'logged_in' in session
        r = client.get('/logout')
        assert 'logged_in' not in session

    @with_client()
    def test_upload(self, client):
        """Test the upload process."""
        resp = client.post(
            '/upload',
            data={
                'file': (StringIO('my file contents'), 'hello world.txt'),
            },
            follow_redirects=True
        )
        assert 'hello world.txt' in resp.data
        resp = client.post(
            '/upload',
            data={
                'file': (StringIO('my file contents'), 'fake.lol'),
            },
            follow_redirects=True
        )
        assert "Invalid file type !" in resp.data

    @with_client()
    def test_download(self, client):
        """Test the download process."""
        resp = client.get('/download/1', follow_redirects=True)
        assert resp.status_code == 200
        resp = client.get('/download/0', follow_redirects=True)
        assert "This file does not exist or had been deleted." in resp.data

    @with_client()
    def test_delete(self, client):
        """Test the delete process."""
        resp = client.get('/delete/1', follow_redirects=True)
        assert 'The file has been deleted !' in resp.data

    @with_client(connected=False)
    def test_guest(self, client):
        """Test the guest access."""
        r = client.get('/download/1', follow_redirects=True)
        assert "You have to login first !" not in r.data
        assert r.status_code == 200
        r = client.get('/delete/1', follow_redirects=True)
        assert "You have to login first !" in r.data
        r = client.get('/my_account', follow_redirects=True)
        assert "You have to login first !" in r.data
        r = client.get('/delete/1', follow_redirects=True)
        assert "You have to login first !" in r.data
        r = client.get('/upload', follow_redirects=True)
        assert "You have to login first !" in r.data
        r = client.get('/logout', follow_redirects=True)
        assert "You have to login first !" in r.data

    @with_client()
    def test_my_account(self, client):
        """Test the account feature."""
        r = client.get('/my_account', follow_redirects=True)
        assert "My account" in r.data
        password = TEST_PASSWORD
        r = update_account(client, "", "", "")
        assert "You have to fill the form first !" in r.data
        r = update_account(client, password, "", "")
        assert "You have to fill the form first !" in r.data
        r = update_account(client, password, password, "")
        assert "You have to fill the form first !" in r.data
        r = update_account(client, password, "", password)
        assert "You have to fill the form first !" in r.data
        r = update_account(client, password + 'x', password, password)
        assert "Wrong current password !" in r.data
        r = update_account(client, password, password + 'x', password)
        assert "The 2 new passwords doesn't match !" in r.data
        r = update_account(client, password, password, password)
        assert "Your profile has been updated !" in r.data

    def test_size2human(self):
        """Testing the size_to_human function."""
        num = 500
        r = index.size_to_human(num)
        assert r == "500.0bytes"
        num = 1024
        r = index.size_to_human(num)
        assert r == "1.0KB"
        num *= 1024
        r = index.size_to_human(num)
        assert r == "1.0MB"
        num *= 1024
        r = index.size_to_human(num)
        assert r == "1.0GB"
        num *= 1024
        r = index.size_to_human(num)
        assert r == "1.0TB"
        num *= 1024
        r = index.size_to_human(num)
        assert r == "1024.0TB"


def string_find(strg, what, offset=0):
    lenght = len(strg)
    for k in range(lenght):
        if k >= offset:
            found = True
            for i in range(len(what)):
                if not (strg[k + i] == what[i]):
                    found = False
                    break
            if found:
                return k, k + len(what) - 1
    return False, False


def string_sub(strg, x, y=False):
    if not x:
        return False
    start = x
    end = y
    lenght = len(strg)
    if not y or y > lenght:
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
