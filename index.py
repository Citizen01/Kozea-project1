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

# configuration
DEBUG = True
SECRET_KEY = 'development key'
DB_URL = "postgresql://kozupload@localhost/kozupload"
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_ECHO'] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
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
    return render_template("index.htmljinja2")


@app.route('/login', methods=['GET', 'POST'])
def show_login():
    error = None
    if request.method == 'POST':
        form_username = request.form.get('username')
        member = User.query.filter_by(username=form_username).first()
        if (not member or member.password != request.form.get('password')):
            error = 'Invalid username/password !'
        else:
            session['logged_in'] = True
            session['username'] = form_username
            session['id'] = member.id
            flash('You were logged in', "success")
            return redirect(url_for('show_files'))

    return render_template('login.htmljinja2', error=error)


@app.route('/logout')
def do_logout():
    session.pop('logged_in', None)
    flash('You were successfully logged out', "success")
    return redirect(url_for('show_index'))


def need_auth(fun):
    @wraps(fun)
    def wrapped_fun(*args, **kwargs):
        print "Ive been decorated"
        if not ('logged_in' in session):
            return render_template('login.htmljinja2',
                                   error="You have to login first !")
        return fun(*args, **kwargs)
    return wrapped_fun


@app.route('/register', methods=['GET', 'POST'])
def show_register():
    error = None
    if request.method == 'POST':
        if not (request.form.get('username') and request.form.get('password')
                and request.form.get('password2')):
            error = 'You have to fill the form first !'
        elif (is_nick_taken(request.form.get('username'))):
            error = 'This username is already taken !'
        elif (request.form.get('password') != request.form.get('password2')):
            error = "The 2 passwords doesn't match !"
        else:
            session['logged_in'] = True
            add_member(request.form.get('username'),
                       request.form.get('password'))
            return render_template('my_files.htmljinja2')

        return render_template('register.htmljinja2', error=error)

    return render_template('register.htmljinja2')


def is_nick_taken(username):
    result = User.query.filter_by(username=username).first()
    if result:
        return True
    else:
        return False


def add_member(username, password):
    user = User(username, password)
    db.session.add(user)
    db.session.commit()
    return True


@app.route("/my_files")
@need_auth
def show_files():
    user = User.query.filter_by(username=session['username']).first()
    db.session.add(user)
    files = user.files

    if len(files) > 0:
        return render_template("my_files.htmljinja2", files=files)
    else:
        flash("Your folder is empty !", "error-files" )
        return render_template("my_files.htmljinja2")


def size_to_human(size, unit=1024, round=True):
    unit_name = 'bytes'
    size = int(size)
    if size > unit:
        size = size / float(unit)
        unit_name = 'KB'
    if size > unit:
        size = size / float(unit)
        unit_name = 'MB'
    if size > unit:
        size = size / float(unit)
        unit_name = 'GB'
    size = str(size)
    if round:
        if len(size) > 4:
            size = "%d" % float(size)
    return size + ' ' + unit_name


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
@need_auth
def show_upload():
    error = None
    if request.method == 'POST':
        file = request.files['file']
        if file:
            if allowed_file(file.filename):
                dbfile = File(file.filename, file.mimetype, session['id'])
                dbfile.data = file.read()
                db.session.add(dbfile)
                db.session.commit()
                return redirect(url_for('show_files'))
            else:
                flash("Invalid file type !", "error")
                return render_template('upload.htmljinja2')

    return render_template('upload.htmljinja2')

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
            error = 'You have to fill the form first !'
        elif (get_password(session['username']) !=
              request.form.get('password')):
            error = 'Wrong current password !'
        elif (request.form.get('newpassword') !=
              request.form.get('newpassword2')):
            error = "The 2 new passwords doesn't match !"
        else:
            the_user = User.query\
                           .filter_by(username=session['username']).first()
            the_user.password = request.form.get('newpassword')
            db.session.commit()
            flash("Your profile has been updated !", "success")
            return render_template('my_account.htmljinja2')

        return render_template('my_account.htmljinja2', error=error)

    return render_template("my_account.htmljinja2")


@app.route('/delete/<int:file_id>')
@need_auth
def delete_file(file_id):
    the_user = User.query.filter_by(username=session['username']).first()
    the_file = File.query.filter_by(id=file_id).first()

    if the_file.owner_id == session['id']:
        db.session.delete(the_file)
        db.session.commit()
        flash("The file has been deleted !", "success")

    return redirect(url_for('show_files'))


def get_password(username):
    if not username:
        return False

    the_user = User.query.filter_by(username=username).first()
    if not the_user:
        return False

    return the_user.password


if __name__ == '__main__':
    app.run(debug=True)
