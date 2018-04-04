from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, BooleanField
from wtforms_components import TimeField
from passlib.hash import sha256_crypt
from functools import wraps
from upload import upload_file, get_data
from datetime import datetime, timedelta

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'trugreen.crk1o9ha4m4n.us-west-2.rds.amazonaws.com'
app.config['MYSQL_USER'] = 'adritrugreendba'
app.config['MYSQL_PASSWORD'] = 't4U9r3eN!^d81'
app.config['MYSQL_DB'] = 'chatbot'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/templates')
def templates():
    cur = mysql.connection.cursor()
    result = cur.execute("select templateid, subject, clean_msg from message_template where 1=1")
    templates = cur.fetchall()

    if result > 0:
        return render_template('templates.html', templates=templates)
    else:
        msg = 'No templates Found'
        return render_template('templates.html', msg=msg)
    cur.close()

@app.route('/template/<string:id>/')
def template(id):
    cur = mysql.connection.cursor()
    result = cur.execute("select templateid, subject, clean_msg from message_template  WHERE templateid = %s", [id])
    onerow = cur.fetchone()
    return render_template('newtemplate.html', template=onerow)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(fname, emailaddress, username, encrypted2) VALUES(%s, %s, %s, %s)", (name, email, username, password))
        mysql.connection.commit()
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)



# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("select username, encrypted2 as password, userid, ismanager, isadmin from users where username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']
            userid = data['userid']
            ismanager = data['ismanager']
            isadmin = data['isadmin']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                session['userid'] = userid
                if (ismanager == 1):
                    session['ismanager'] = True
                if (isadmin == 1):
                    session['isadmin'] = True

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

def is_manager(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            if 'ismanager' in session or 'isadmin' in session:
                #flash('Manager privileges verified', 'success')

                return f(*args, **kwargs)
            else:
                flash('Manager privileges required to view page', 'danger')
                return redirect(url_for('about'))
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            if 'isadmin' in session:
                #flash('Admin privileges verified', 'success')
                return f(*args, **kwargs)
            else:
                flash('Admin privileges required to view page', 'danger')
                return redirect(url_for('about'))
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()
    result = cur.execute("select interviewid, interview_title, managerid, startdate, enddate, roleid from interview where managerid = %s", [session['userid']])

    if result > 0:
        return render_template('dashboard.html', interviews=result)
    else:
        msg = 'No Interviews Found'
        return render_template('dashboard.html', msg=msg)
    cur.close()

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


class AddTime(Form):
    weekday = StringField('Day of Week', [validators.Length(min=1, max=50)], default='Monday')
    stime = TimeField(label='Start time',validators=[validators.InputRequired()],format = "%H:%M")
    etime = TimeField(label='End time',validators=[validators.InputRequired()],format = "%H:%M")
    bfield = BooleanField('Apply these times from Monday through Friday')

# User Register
@is_manager
@app.route('/add_time', methods=['GET', 'POST'])
def add_time():
    form = AddTime(request.form)
    if request.method == 'POST' and form.validate():
        weekday = form.weekday.data
        stime = form.stime.data
        etime = form.etime.data
        bfield = form.bfield.data
        userid = session['userid']

        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        cur = mysql.connection.cursor()
        if bfield:
            for theweekday in weekdays:
                cur.execute("insert into available (personid, starttime, endtime, weekday) VALUES(%s, %s, %s, %s)", (userid, stime, etime, theweekday))
        else:
            cur.execute("insert into available (personid, starttime, endtime, weekday) VALUES(%s, %s, %s, %s)", (userid, stime, etime, weekday))
        mysql.connection.commit()
        cur.close()

        flash('Time Added', 'success')

        return redirect(url_for('available_times'))

    return render_template('add_time.html', form=form)



@app.route('/upload_candidates', methods=['GET', 'POST'])
@is_logged_in
def upload_candidates():
    if request.method == 'POST':
        #uploaded_file will save the file to local filesystem
        # and then load to mysql
        upload_file(request, session, mysql)
        flash('Candidates Added', 'success')
        return redirect(url_for('uploaded_file'))

    return render_template('upload_candidates.html')

def printstuff(arr):
    for a in arr:
        print a

# uploaded_file
@app.route('/uploaded_file')
@is_logged_in
def uploaded_file():

    cur = mysql.connection.cursor()
    result = cur.execute("select userid, fname, lname, emailaddress, mobilenumber,rolename, batchid from users where batchid = %s", [session['batchid']])
    candidates = cur.fetchall()
    if result > 0:
        return render_template('uploaded_file.html', candidates=candidates)
    else:
        msg = 'No Candidates in file'
        return render_template('uploaded_file.html', msg=msg)
    cur.close()


"""
call api_mgr_lack_avail(2)
call api_get_avail(92990)
call api_get_interview(92990)
call api_get_interview_info_null(92990)
call api_get_interview(?) [ [ 'C00831124-99841928-R2853' ] ]
"""
# all_times
@app.route('/available_times')
@is_manager
def available_times():

    cur = mysql.connection.cursor()
    cur.execute("select availableid, personid, starttime, endtime, weekday from available where personid = %s", [session['userid']])
    times = cur.fetchall()

    if len(times) > 0:
        return render_template('available_times.html', times=times)
    else:
        msg = 'Availablity not setup yet'
        return render_template('available_times.html', msg=msg)
    cur.close()


# unscheduled_prospects
@app.route('/unscheduled_prospects')
@is_logged_in
def unscheduled_prospects():

    cur = mysql.connection.cursor()
    result = get_data(mysql, 'api_get_interview_info_null', ['92990'])

    if len(result) > 0:
        return render_template('unscheduled_prospects.html', candidates=result)
    else:
        msg = 'No Unscheduled Prospects'
        return render_template('unscheduled_prospects.html', msg=msg)
    cur.close()

# all_uploads
@app.route('/all_uploads')
@is_logged_in
def all_uploads():

    cur = mysql.connection.cursor()
    result = cur.execute("select userid, fname, lname, emailaddress, mobilenumber,rolename, batchid from users where upload_user = %s order by userid desc", [session['userid']])
    candidates = cur.fetchall()
    if result > 0:
        return render_template('all_uploads.html', candidates=candidates)
    else:
        msg = 'No Candidates in file'
        return render_template('all_uploads.html', msg=msg)
    cur.close()

# Add Article
@app.route('/add_interview', methods=['GET', 'POST'])
@is_logged_in
def add_interview():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username']))
        mysql.connection.commit()
        cur.close()

        flash('Interview Created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_interview.html', form=form)

# Edit Article
@app.route('/edit_time/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_time(id):
    cur = mysql.connection.cursor()
    cur.execute("select availableid, personid, starttime, endtime, weekday from available where availableid = %s ", [int(id)])
    time = cur.fetchone()
    form = AddTime(request.form)

    thestarttime = time['starttime']
    theendtime = time['endtime']
    form.weekday.data = time['weekday']

    if request.method == 'POST' and form.validate():
        weekday = form.weekday.data
        stime = form.stime.data
        etime = form.etime.data
        userid = session['userid']

        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        cur = mysql.connection.cursor()
        cur.execute("update available set starttime = %s, endtime = %s, weekday = %s where availableid = %s", [stime, etime, weekday, int(id)])
        mysql.connection.commit()
        cur.close()
        flash('Time Added', 'success')
        return redirect(url_for('available_times'))

    return render_template('edit_time.html', form=form)

# Delete Article
@app.route('/delete_time/<string:id>', methods=['POST'])
@is_manager
def delete_time(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM available WHERE availableid = %s", [id])
    mysql.connection.commit()
    cur.close()

    flash('Available time deleted', 'success')
    return redirect(url_for('available_times'))

if __name__ == '__main__':
    app.secret_key='duckdivewaves_summer'
    app.run(debug=True)
