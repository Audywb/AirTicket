from flask import Flask, render_template, redirect, request, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pathlib
import os
import logging
import bcrypt
import humanize
import random

app = Flask(__name__)
app.secret_key = "AirTicket.com"

app.config['FILE_UPLOADS'] = os.getcwd()+'/static/uploads'

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

client = MongoClient('localhost', 27017)
db = client.ticket_db
airline = db.airline
testdb = db.test
users = db.users
admins = db.admin
flights = db.flights
tickets = db.tickets

logging.basicConfig(level=logging.DEBUG)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "name" not in session:
            warning = "กรุณาเข้าสู่ระบบ"
            # Auth required
            return render_template('login.html', warning=warning)
        else:
            return function()
    wrapper.__name__ = function.__name__
    return wrapper


def login_is_required_admin(function):
    def wrapper(*args, **kwargs):
        if "name" not in session:
            warning = "กรุณาเข้าสู่ระบบ"
            # Auth required
            return render_template('login.html', warning=warning)
        elif session["is_user"] != "admin":
            warning = "กรุณาเข้าสู่ระบบ ด้วยบัญชีผู้ดูแลระบบ"
            return render_template('login.html', warning=warning)
        else:
            return function()
    wrapper.__name__ = function.__name__
    return wrapper


def login_is_required_airline(function):
    def wrapper(*args, **kwargs):
        if "name" not in session:
            warning = "กรุณาเข้าสู่ระบบ"
            return render_template('login.html', warning=warning)
        elif session["is_user"] != "airline":
            warning = "กรุณาเข้าสู่ระบบ ด้วยบัญชีผู้ดูแลสายการบิน"
            return render_template('login.html', warning=warning)
        else:
            return function()
    wrapper.__name__ = function.__name__
    return wrapper


@app.route("/")
def index():
    if "name" in session:
        name = session['name']
    else:
        name = "not_login"

    all_flight = flights.find()
    return render_template('index.html', username=name, flights=all_flight)

@app.route("/about/me")
def about_me():
    if "name" in session:
        name = session['name']
    else:
        name = "not_login"

    return render_template('about_me.html', username=name)


@app.route("/ticeket")
def ticket():
    if "name" in session:
        name = session['name']
    else:
        name = "not_login"
    all_flight = flights.find()
    return render_template('ticket.html', username=name, flights=all_flight)


@app.route("/ticeketSelect/<id>", methods=['GET', 'POST'])
def ticeketSelect(id):
    if "name" in session:
        name = session['name']
    else:
        name = "not_login"
        # warning = "กรุณาเข้าสู่ระบบ"
        # return render_template('login.html', warning=warning)

    flight = flights.find_one({"_id": ObjectId(id)})
    return render_template('ticket_select.html', username=name, flight=flight)


@app.route("/payment/<id>", methods=['GET', 'POST'])
def payment(id):
    ticket_no = random.randint(0, 10000000000)
    print(ticket_no)
    if "name" in session:
        name = session['name']
        email = session['email']
    else:
        name = "not_login"
        email = "กรุณากรอกอีเมล"
        # warning = "กรุณาเข้าสู่ระบบ"
        # return render_template('login.html', warning=warning)
    flight = flights.find_one({"_id": ObjectId(id)})
    if request.method == 'POST':
        payment = request.form['payment']
        user_name = request.form['name']
        user_email = request.form['email']
        phone = request.form['phone']
        tickets.insert_one(
            {
                'payment': payment,
                'name': user_name,
                'email': user_email,
                'phone': phone,
                'ticket_no': ticket_no,
                'created': datetime.now(),
                'flight_id': id,
                'airline': flight['name'],
                'flight_time': flight['flight_date']

            })
        return render_template('paymented.html', username=name, flight=flight, ticket_no=ticket_no, name=user_name)
    return render_template('payment.html', username=name, flight=flight, email=email, ticket_no=ticket_no)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        # name = request.form['name']
        # logging.info(name)
        signin_user = users.find_one({"name": request.form['name']})
        if signin_user:
            pass
        else:
            warning = "ชื่อผู้ใช้ไม่ถูกต้อง"
            return render_template('login.html', warning=warning)
        passw = signin_user['password']
        # logging.info("user", request.form['password'], passw)
        # logging.info("hash", bcrypt.hashpw(
        #     request.form['password'].encode('utf-8'), passw))

        if signin_user:
            if bcrypt.hashpw(request.form['password'].encode('utf-8'), passw) == passw:
                session['name'] = request.form['name']
                session['is_user'] = signin_user['is_user']
                session['email'] = signin_user['email']
                if session['is_user'] == "admin":
                    return redirect(url_for('admin'))
                elif session['is_user'] == "airline":
                    return redirect(url_for('airline'))
                else:
                    return redirect(url_for('index'))
            else:
                warning = "รหัสผ่านไม่ถูกต้อง"
                return render_template('login.html', warning=warning)

        flash('Username and password combination is wrong')
        return render_template('login.html')

    return render_template('login.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(14))
        is_user = "user"
        is_admin = False
        users.insert_one(
            {
                'name': name,
                'email': email,
                'password': hashed,
                'is_user': is_user,
                'is_admin': is_admin
            })
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('name', None)
    return redirect(url_for('login'))


@app.route('/airline', methods=['POST', 'GET'])
@login_is_required_airline
def airline():
    if "name" in session:
        name = session['name']
    else:
        name = "not_login"
    now = datetime.now()
    promo_date = now+relativedelta(days=+7)
    if request.method == 'POST':
        name = request.form['name']
        start = request.form['start']
        end = request.form['end']
        price = request.form['price']
        time_h = request.form['time']
        to_date = request.form.get('flightdate')
        to_time = request.form.get('flighttime')
        date_time = datetime.strptime(
            to_date + " " + to_time, '%Y-%m-%d %H:%M')
        today = date_time - datetime.now()
        dayago = humanize.naturaltime(today)
        print(date_time)
        print(type(date_time))
        flights.insert_one(
            {
                'name': name,
                'start': start,
                'end': end,
                'price': price,
                'time_fly': time_h,
                'flight_date': date_time,
                'dayago': dayago
            })
        return redirect('airline')
    all_ticket = tickets.find({"airline": name})
    return render_template('airline/home.html', username=name, now=now, date=promo_date, tickets=all_ticket)


@app.route('/admin', methods=['POST', 'GET'])
@login_is_required_admin
def admin():
    message = "not"
    if "name" in session:
        name = session['name']
    else:
        name = "not_login"
    if request.method == 'POST':
        name = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(14))
        is_user = "admin"
        is_admin = True
        users.insert_one(
            {
                'name': name,
                'email': email,
                'password': hashed,
                'is_user': is_user,
                'is_admin': is_admin
            })
        message = "success"
        # return render_template('admin/home.html', username=name, message=message)
    return render_template('admin/home.html', username=name, message=message)


@app.route('/addAirline', methods=['POST', 'GET'])
@login_is_required_admin
def addAirline():
    if request.method == 'POST':
        name = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(14))
        is_user = "airline"
        is_admin = False
        users.insert_one(
            {
                'name': name,
                'email': email,
                'password': hashed,
                'is_user': is_user,
                'is_admin': is_admin
            })
        return redirect('admin')
    return redirect('admin')


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/test', methods=['POST', 'GET'])
def test():
    if request.method == 'GET':
        return "Login via the login Form"

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        testdb.insert_one(
            {
                'name': name,
                'age': age,
            })
        return redirect(url_for('test'))
    else:
        return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=7000)
