# app.py - Optimized Version with Real User Wins
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import hashlib
import time
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dating_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static files for 1 year

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    coins = db.Column(db.Integer, default=100)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    agreed_to_terms = db.Column(db.Boolean, default=False)

class BettingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    option = db.Column(db.String(50), nullable=False)
    bet_amount = db.Column(db.Integer, nullable=False)
    opponent = db.Column(db.String(50), nullable=False)
    winner = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    slot_time = db.Column(db.String(50))

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    age = db.Column(db.Integer)
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    interests = db.Column(db.String(200))

# Bot names (fixed as per your request)
BOT_NAMES = ['Ammu', 'Amritha', 'Anjana', 'Shivanisavi']

# Options with minimal data
OPTIONS = {
    'outing': {
        'name': 'Outing with Aswin',
        'time': '7:30 PM - 11:30 PM',
        'image': 'https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=300&h=200&fit=crop&q=80',
        'desc': '✨ Romantic evening stroll',
        'icon': 'fa-walking'
    },
    'dinner': {
        'name': 'Dinner with Aswin',
        'time': '7:00 PM - 10:00 PM',
        'image': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=300&h=200&fit=crop&q=80',
        'desc': '🍷 Candlelight dinner',
        'icon': 'fa-utensils'
    },
    'call': {
        'name': 'Call with Aswin',
        'time': '6:00 PM - 8:00 PM',
        'image': 'https://images.unsplash.com/photo-1544717301-9cdcb1f5940f?w=300&h=200&fit=crop&q=80',
        'desc': '📞 Private phone call',
        'icon': 'fa-phone-alt'
    },
    'video': {
        'name': 'Video Call with Aswin',
        'time': '9:00 PM - 12:00 AM',
        'image': 'https://plus.unsplash.com/premium_photo-1661759476421-af5519793034?w=300&h=200&fit=crop&q=80',
        'desc': '💻 Face-to-face video',
        'icon': 'fa-video'
    }
}

# Betting states
active_bets = {}
BET_DURATION = 60  # seconds

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            if user.agreed_to_terms:
                return redirect(url_for('home'))
            return redirect(url_for('terms_agreement'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = generate_password_hash(request.form['password'])
        email = request.form.get('email', '').strip()

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')

        new_user = User(username=username, password=password, email=email)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        return redirect(url_for('terms_agreement'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username'].strip()
    password = request.form['password']

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        if user.agreed_to_terms:
            return redirect(url_for('home'))
        return redirect(url_for('terms_agreement'))

    return render_template('login.html', error='Invalid credentials')

@app.route('/terms')
def terms_agreement():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])
    if user.agreed_to_terms:
        return redirect(url_for('home'))

    return render_template('terms.html', username=user.username)

@app.route('/agree_terms', methods=['POST'])
def agree_terms():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(session['user_id'])
    user.agreed_to_terms = True
    db.session.commit()

    return jsonify({'success': True})

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])
    if not user.agreed_to_terms:
        return redirect(url_for('terms_agreement'))

    # Fetch data with single queries
    history = BettingHistory.query.filter_by(user_id=user.id).order_by(BettingHistory.timestamp.desc()).limit(10).all()
    leaderboard = User.query.order_by(User.coins.desc()).limit(10).all()

    return render_template('home.html',
                         user=user,
                         options=OPTIONS,
                         history=history,
                         leaderboard=leaderboard)

@app.route('/start_bet', methods=['POST'])
def start_bet():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    option = data.get('option')
    bet_amount = int(data.get('bet_amount', 10))

    user = User.query.get(session['user_id'])

    if user.coins < bet_amount:
        return jsonify({'error': 'Insufficient coins'}), 400

    # Use all 4 bots (Ammu, Amritha, Anjana, Shivanisavi)
    selected_bots = BOT_NAMES.copy()

    bet_id = hashlib.md5(f"{user.id}_{option}_{time.time()}".encode()).hexdigest()[:16]

    # Create bot bets with fixed amounts as shown in your example
    bot_bets = {
        'Ammu': 58,
        'Amritha': 35,
        'Anjana': 37,
        'Shivanisavi': 57
    }

    active_bets[bet_id] = {
        'user_id': user.id,
        'username': user.username,
        'option': option,
        'bet_amount': bet_amount,
        'bots': selected_bots,
        'bot_bets': bot_bets,
        'user_bet': bet_amount,
        'end_time': time.time() + BET_DURATION,
        'is_active': True,
        'winner': None
    }

    return jsonify({
        'success': True,
        'bet_id': bet_id,
        'bots': selected_bots,
        'bot_bets': bot_bets,
        'user_bet': bet_amount,
        'duration': BET_DURATION
    })

@app.route('/get_bet_status/<bet_id>')
def get_bet_status(bet_id):
    bet = active_bets.get(bet_id)
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404

    current_time = time.time()

    if current_time >= bet['end_time'] and bet['is_active']:
        bet['is_active'] = False

        # Find winner - real user can win if their bid is highest
        all_bets = {bet['username']: bet['user_bet']}
        all_bets.update(bet['bot_bets'])
        winner = max(all_bets, key=all_bets.get)
        bet['winner'] = winner

        # If real user wins, give them coins
        if winner == bet['username']:
            user = User.query.get(bet['user_id'])
            # User gets double their bet amount as reward
            user.coins += bet['bet_amount'] * 2
            db.session.commit()

        # Save history
        history = BettingHistory(
            user_id=bet['user_id'],
            option=bet['option'],
            bet_amount=bet['bet_amount'],
            opponent=', '.join(bet['bots']),
            winner=winner,
            slot_time=OPTIONS[bet['option']]['time']
        )
        db.session.add(history)
        db.session.commit()

    time_left = max(0, bet['end_time'] - current_time)

    return jsonify({
        'bet_id': bet_id,
        'user_bet': bet['user_bet'],
        'bot_bets': bet['bot_bets'],
        'bots': bet['bots'],
        'is_active': bet['is_active'],
        'time_left': time_left,
        'winner': bet.get('winner'),
        'username': bet['username']
    })

@app.route('/increase_bet', methods=['POST'])
def increase_bet():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    bet_id = data.get('bet_id')
    increment = int(data.get('increment', 10))

    bet = active_bets.get(bet_id)
    if not bet:
        return jsonify({'error': 'Bet not found'}), 404

    if not bet['is_active']:
        return jsonify({'error': 'Betting time is over'}), 400

    user = User.query.get(session['user_id'])

    if user.coins < increment:
        return jsonify({'error': 'Insufficient coins'}), 400

    # Increase user's bet
    bet['user_bet'] += increment
    user.coins -= increment

    # Bots react randomly - they can increase their bets too
    for bot in bet['bots']:
        if random.random() < 0.4:  # 40% chance each bot increases
            bot_increment = random.randint(1, 15)
            bet['bot_bets'][bot] += bot_increment

    db.session.commit()

    return jsonify({
        'success': True,
        'user_bet': bet['user_bet'],
        'bot_bets': bet['bot_bets'],
        'user_coins': user.coins
    })

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])
    profile = UserProfile.query.filter_by(user_id=user.id).first()

    return render_template('profile.html', user=user, profile=profile)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(session['user_id'])
    profile = UserProfile.query.filter_by(user_id=user.id).first()

    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)

    profile.age = request.form.get('age')
    profile.location = request.form.get('location')
    profile.bio = request.form.get('bio')
    profile.interests = request.form.get('interests')
    db.session.commit()

    return redirect(url_for('profile'))

@app.route('/add_coins', methods=['POST'])
def add_coins():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    amount = int(data.get('amount', 10))

    user = User.query.get(session['user_id'])
    user.coins += amount
    db.session.commit()

    return jsonify({'success': True, 'new_balance': user.coins})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/get_aswin_number')
def get_aswin_number():
    return jsonify({'number': '+917012453261'})

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=6000, threaded=True)
