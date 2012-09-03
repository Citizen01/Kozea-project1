#index.py
from flask import (Flask, request, session, g, redirect, url_for, abort,
                   render_template, flash, send_file, Response)
from flask.ext.sqlalchemy import SQLAlchemy
from functools import wraps
import os
from werkzeug import secure_filename
from datetime import datetime
from sqlalchemy.orm import deferred, relationship, backref, column_property
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from os.path import splitext

import config

# configuration

ALLOWED_EXTENSIONS = set(['.txt', '.pdf', '.iso', '.rar', '.psd', '.tiff', '.png', '.jpg', '.jpeg', '.gif', '.zip',
                          '.tar', '.tar.gz'])

# create our little application :)
app = Flask(__name__)
app.config.from_object('config')
app.config.from_envvar('APP_SETTINGS', silent=True)
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self):
        return '<User %r>' % self.username


class File(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120))
    type = db.Column(db.String(80))
    pub_date = db.Column(db.DateTime)
    data = deferred(db.Column(db.LargeBinary))

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship("User", backref=backref('files',
                                                    order_by=pub_date))

    def __init__(self, title, type, ownerid, pub_date=None):
        self.title = title
        self.type = type
        self.owner_id = ownerid
        if pub_date is None:
            pub_date = datetime.utcnow()
        self.pub_date = pub_date

    def __repr__(self):
        return '<Post %r>' % self.title

    def read(self, arg1):
        db.session.add(self)
        return self.data

    @hybrid_property
    def size(self):
        return size_to_human(len(self.data))

    @size.expression
    def size(self):
        return func.pg_size_pretty(func.octet_length(self.data))


@app.route("/")
def show_index():
    return render_template("index.html.jinja2")


@app.route('/login', methods=['GET', 'POST'])
def show_login():
    if 'logged_in' in session:
        return redirect(url_for('show_files'))
    if request.method == 'POST':
        form_username = request.form.get('username')
        member = User.query.filter_by(username=form_username).first()
        if not member or member.password != request.form.get('password'):
            flash('Invalid username/password !', "error")
        else:
            session['logged_in'] = True
            session['username'] = form_username
            session['id'] = member.id
            flash('You were logged in', "success")
            return redirect(url_for('show_files'))

    return render_template('login.html.jinja2')


@app.route('/logout')
def do_logout():
    session.pop('logged_in', None)
    flash('You were successfully logged out', "success")
    return redirect(url_for('show_index'))


def need_auth(fun):
    @wraps(fun)
    def wrapped_fun(*args, **kwargs):
        if not ('logged_in' in session):
            flash("You have to login first !", "error")
            return render_template('login.html.jinja2')
        return fun(*args, **kwargs)
    return wrapped_fun


@app.route('/register', methods=['GET', 'POST'])
def show_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        if not (username and password and password2):
            flash("You have to fill the entire form first !", "error")
        elif (is_nick_taken(request.form.get('username'))):
            flash("This username is already taken !", "error")
        elif (request.form.get('password') != request.form.get('password2')):
            flash("The 2 passwords doesn't match !", "error")
        else:
            add_member(username, password)
            session['logged_in'] = True
            session['username'] = username
            session['id'] = User.query.filter_by(username=username).first().id
            flash('Welcome on Kozupload, %s !' % username, "success")
            flash('You can use our services right now !', "success")
            return redirect(url_for('show_files'))

    return render_template('register.html.jinja2')


def is_nick_taken(username):
    return bool(User.query.filter_by(username=username).first())


def add_member(username, password):
    db.session.add(User(username, password))
    db.session.commit()
    return True

def del_member(username):
    if is_nick_taken(username):
        db.session.delete(User.query.filter_by(username=username).first())
        db.session.commit()
    return True



@app.route("/my_files")
@need_auth
def show_files():
    user = User.query.filter_by(username=session['username']).first()
    if not user.files:
        flash("Your folder is empty !", "error-files")

    return render_template("my_files.html.jinja2", files=user.files)


def size_to_human(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def allowed_file(filename):
    return splitext(filename)[1] in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
@need_auth
def show_upload():
    if request.method == 'POST':
        f = request.files['file']
        if f:
            if allowed_file(f.filename):
                dbfile = File(f.filename, f.mimetype, session['id'])
                dbfile.data = f.read()
                db.session.add(dbfile)
                db.session.commit()
                return redirect(url_for('show_files'))
            else:
                flash("Invalid file type !", "error")

    return render_template('upload.html.jinja2')


@app.route('/download/<int:file_id>')
def download_file(file_id):
    the_file = File.query.filter_by(id=file_id).first()
    if the_file:
        headers = {
            'Content-Length': the_file.size,
            'Content-Disposition': "attachment;filename=%s" % the_file.title}
        return Response(
            the_file.data, mimetype=the_file.type, headers=headers)
    else:
        flash("This file does not exist or had been deleted.", "error")
        return redirect(url_for("show_files"))


@app.route('/my_account', methods=['GET', 'POST'])
@need_auth
def show_account():
    if request.method == 'POST':
        if not (request.form.get('password')
                and request.form.get('newpassword')
                and request.form.get('newpassword2')):
            flash("You have to fill the form first !", "error")
        elif (get_password(session['username']) !=
              request.form.get('password')):
            flash("Wrong current password !", "error")
        elif (request.form.get('newpassword') !=
              request.form.get('newpassword2')):
            flash("The 2 new passwords doesn't match !", "error")
        else:
            the_user = (
                User.query
                .filter_by(username=session['username'])
                .first())
            the_user.password = request.form.get('newpassword')
            db.session.commit()
            flash("Your profile has been updated !", "success")

    return render_template("my_account.html.jinja2")


@app.route('/delete/<int:file_id>')
@need_auth
def delete_file(file_id):
    the_user = User.query.filter_by(username=session['username']).first()
    the_file = File.query.filter_by(id=file_id).first()
    if the_user and the_file and the_file.owner_id == session['id']:
        db.session.delete(the_file)
        db.session.commit()
        flash("The file has been deleted !", "success")

    return redirect(url_for('show_files'))


def get_password(username):
    return User.query.filter_by(username=username).first().password


if __name__ == '__main__':
    app.run(debug=True)
