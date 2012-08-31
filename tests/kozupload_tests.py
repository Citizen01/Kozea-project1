# -*- coding: utf-8 -*-
#Kozupload test process which will test all features from Kozupload


import os
import sys
import unittest
import tempfile
from flask.ext.sqlalchemy import SQLAlchemy
from functools import wraps
from flask import session

PATH = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PATH)

TEST_USERNAME = "test_user"
TEST_PASSWORD = "default"

import index

def with_client(function):
    """Create the test_client."""
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        """Decorator for the client login."""
        with index.app.test_client() as client:
            client.post('login', data={'username': 'test_user', 'password': 'default'})
            return function(self, client=client, *args, **kwargs)
    return wrapper


class KozuploadTestCase(unittest.TestCase):

    def setUp(self):
        test_db_uri = "postgresql://kozupload@localhost/kozupload-test"
        index.app.config['SQLALCHEMY_DATABASE_URI'] = test_db_uri
        index.app.config['TESTING'] = True
        self.app = index.app.test_client()

    def tearDown(self):
        return "nothing"

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





if __name__ == '__main__':
    unittest.main()
