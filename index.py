#index.py
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'


# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)



@app.route("/")
def show_index():
    return render_template("index.htmljinja2")
    
    
@app.route('/login', methods=['GET', 'POST'])
def show_login():
    error = None
    if request.method == 'POST' :
        if (request.form['username'] != "Citizen") or (request.form['password'] != "1345"):
            error = 'Invalid username/password !'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_files'))
            
    return render_template('login.htmljinja2', error=error)

@app.route('/logout')
def do_logout():
    session.pop('logged_in', None)
    flash('You were successfully logged out')
    return redirect(url_for('show_index'))

@app.route('/register')
def show_register():
    return render_template('register.htmljinja2')


@app.route("/my_files")
def show_files():
    return render_template("my_files.htmljinja2")
    
@app.route("/my_account")
def show_account():
    return render_template("my_account.htmljinja2")

if __name__ == '__main__':
    app.run(debug=True)
