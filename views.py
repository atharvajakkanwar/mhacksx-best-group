from app import app, db
from flask import render_template, redirect, url_for, session, request
from forms import LoginForm, RegisterForm, BuySellBitcoin
from models import *
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from coinbase.wallet.client import Client


import time
import config
import datetime
import requests
import json
# import numpy as np

import plotly.plotly as py
import plotly.graph_objs as go
import plotly.tools as tls
py.plotly.tools.set_credentials_file(username=config.PL_KEY, api_key=config.PL_SECRET)

from game_logic import *
import compute_logic as compute


client = Client(config.CB_API_KEY, config.CB_API_SECRET, api_version='2017-09-22')

login_manager = LoginManager()
login_manager.init_app(app)
GDAX_ENDPOINT = 'https://api.gdax.com'
login_manager.login_view = 'login'
currency_code = 'USD'
accuracy = 5
digital_type ='BTC-USD'
month = 570
month_in_sec = 2629746
interval = 200
income = 2000 #$
# = 39450

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    #history stats
    all_history = get_history_stats()
    generate_graph(all_history[0])

    #what could have been gained/lost
    investment = compute.bit_coin_value(income, all_history[0])
    savings = compute.saving_acc(income, all_history[0])
    generate_graph_duo(investment, savings, 'prev-investment')

    aroon_high = compute.aroon_high(all_history[2])
    aroon_low = compute.aroon_low(all_history[1])
    generate_graph_duo(aroon_low, aroon_high, 'aroon-indicator')

    sma = compute.twenty_days_SMA(all_history[0])
    generate_graph_duo(sma, all_history[0],'moving-avg')

    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    #Check if the form is submitted,
    if form.validate_on_submit():
        #usernames are unique so it's okay to return the first query we find
        user = User.query.filter_by(username=form.username.data).first()

        # if user exists
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('dashboard'))

        return '<h1>Invalid username or password</h1>'
        #return '<p>{}</p><p>{}</p>'.format(form.username.data,
        #                                   form.password.data)

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET','POST'])
def signup():
    form = RegisterForm()

    #Check if the form is submited
    if form.validate_on_submit():

        #shaw256 generates a password that's 80 characters long, models should reflect that
        hashed_password = generate_password_hash(form.password.data, method='sha256')

        #we're passing the data without hashing for testing purposes
        new_user = User(email=form.email.data,
                        username=form.username.data,
                        password=hashed_password,
                        pic_url =form.pic_url.data,
                        game_bit_balance = 0.00,
                        game_usd_balance = 100000.00)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('signup.html', form=form)



def generate_graph(inp_y):
    samples = 200
    inp_x =list(range(0,samples))
    trace = go.Scatter(x = inp_x, y = inp_y, fill='tozeroy', mode ='none')
    data = [trace]
    py.plot(data, filename='bit-history', auto_open=False)

def generate_graph(inp_y):
    samples = 200
    inp_x =list(range(0,samples))
    trace = go.Scatter(x = inp_x, y = inp_y, fill='tozeroy', mode ='none')
    data = [trace]
    py.plot(data, filename='bit-history', auto_open=False)

def generate_graph_duo(inp_y, inp_y2, name):
    samples = 200
    inp_x =list(range(0,samples))
    trace = go.Scatter(x = inp_x, y = inp_y, fill='tozeroy', mode ='none')
    trace2 = go.Scatter(x = inp_x, y = inp_y2, fill='tonexty', mode ='none')
    data = [trace, trace2]
    py.plot(data, filename=name, auto_open=False)

def get_todays_stats():
    return requests.get(GDAX_ENDPOINT + '/products/' + digital_type + '/stats').text

def get_todays_price():
    return json.loads(requests.get('https://api.coinbase.com/v2/prices/spot?currency=USD').text)

def get_history_stats():
    gran_limit_factor = 3/200
    current_time_ISO = datetime.datetime.now().isoformat() #current time in iso (str)
    start_time_ISO = datetime.datetime.utcfromtimestamp(month_in_sec*month).isoformat() + 'Z'
    end = current_time_ISO
    start = start_time_ISO
    gran = str(int(month_in_sec*gran_limit_factor)-12435)
    history = requests.get(GDAX_ENDPOINT + '/products/'
        + digital_type + '/candles?'
        + 'start=' + start + '&'
        + 'end=' + end + '&'
        +'granularity=' + gran).text
    history_day_close_price = []
    history_day_high_price = []
    history_day_low_price = []
    history_filtered_data = json.loads(history)
    index_close = 4
    index_high = 2
    index_low = 1
    all_history_stats = []
    for entry in history_filtered_data:
        history_day_close_price.append(entry[index_close])
        history_day_high_price.append(entry[index_high])
        history_day_low_price.append(entry[index_low])
    history_day_close_price =  history_day_close_price[::-1]
    history_day_low_price =  history_day_low_price[::-1]
    history_day_high_price =  history_day_high_price[::-1]
    all_history_stats.append(history_day_close_price) #0
    all_history_stats.append(history_day_low_price) #1
    all_history_stats.append(history_day_high_price) #2
    return all_history_stats

@app.route('/dashboard')
@login_required
def dashboard():
    #todays rates
    price = get_todays_price();

    #current stats
    data = get_todays_stats();
    todays_stats = json.loads(data)




    return render_template('dashboard.html',
                            name=current_user.username,
                            bitcoin_val = str(price['data']['amount']),
                            dollar_val = str(round(1/float(price['data']['amount']),accuracy)),
                            timestamp = datetime.datetime.now(),
                            stats_open = str(round(float(todays_stats['open']),2)),
                            stats_high = str(round(float(todays_stats['high']),2)),
                            stats_low = str(round(float(todays_stats['low']),2)),
                            stats_volume = str(round(float(todays_stats['volume']),2)))

@app.route('/analysis')
@login_required
def analysis():
    return render_template('analysis.html', name =current_user.username)
@app.route('/bitgame')
@login_required
def bitgame():
    start_game(datetime.datetime.now())
    player = Gameplayer.query.filter_by(u_id = current_user.id).first()
    if player is None:
        return render_template('bitgame.html', name =current_user.username)
    bit_balance = User.query.filter_by(id = current_user.id).first().game_bit_balance
    print(bit_balance)
    usd_balance = User.query.filter_by(id = current_user.id).first().game_usd_balance
    print(get_leaderboard(1,client))
    return render_template('bitgame.html', bit_bal = bit_balance,
                                        usd_bal = usd_balance,
                                        name = current_user.username)

@app.route('/bitgame/join')
@login_required
def join():
    player = Gameplayer.query.filter_by(u_id = current_user.id).first()
    if not player:
        join_game(current_user.id)
    bit_balance = User.query.filter_by(id = current_user.id).first().game_bit_balance
    usd_balance = User.query.filter_by(id = current_user.id).first().game_usd_balance
    return redirect(url_for('bitgame', bit_bal = bit_balance,
                                        usd_bal = usd_balance,
                                        name = current_user.username))























@app.route('/bitgame/buy', methods=['GET','POST'])
@login_required
def bitgame_buy():
    form = BuySellBitcoin()
    if request.method == 'POST':
        buy_bitcoin(form.amount.data ,client,current_user.id)

        return redirect(url_for('bitgame'))
    return render_template('buy.html', form=form)



@app.route('/bitgame/sell', methods=['GET','POST'])
@login_required
def bitgame_sell():
    form = BuySellBitcoin()

    if request.method == 'POST':
        sell_bitcoin(form.amount.data ,client,current_user.id)

        return redirect(url_for('bitgame'))
    return render_template('sell.html', form=form)
