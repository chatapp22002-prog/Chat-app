import os
import random
import string
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_chat_key_2026'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Flask-Mail Configuration (Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'chatapp22002@gmail.com'
app.config['MAIL_PASSWORD'] = 'kxng asmi dxtf qhow'

mail = Mail(app)
socketio = SocketIO(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            unique_code TEXT UNIQUE NOT NULL,
            profile_pic TEXT,
            age INTEGER,
            gender TEXT,
            about TEXT,
            latitude REAL,
            longitude REAL,
            is_verified INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('terms.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'POST':
        email = request.form.get('email')
        otp = ''.join(random.choices(string.digits, k=6))
        session['temp_email'] = email
        session['otp'] = otp
        
        try:
            msg = Message('Chat App Email Verification OTP',
                          sender='chatapp22002@gmail.com',
                          recipients=[email])
            msg.body = f'Your verification OTP code is: {otp}'
            mail.send(msg)
            return redirect(url_for('enter_otp'))
        except Exception as e:
            flash('Failed to send email. Please check your settings.')
    return render_template('verify_email.html')

@app.route('/enter-otp', methods=['GET', 'POST'])
def enter_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        if user_otp == session.get('otp'):
            session['email_verified'] = True
            return redirect(url_for('register_profile'))
        else:
            flash('Invalid OTP code. Please try again.')
    return render_template('enter_otp.html')

@app.route('/register-profile', methods=['GET', 'POST'])
def register_profile():
    if not session.get('email_verified'):
        return redirect(url_for('verify_email'))
        
    if request.method == 'POST':
        # මිතුරන්ට පමණක් දෙන රහස් කෝඩ් එක පරීක්ෂා කිරීම
        invite_code = request.form.get('invite_code')
        if invite_code != 'rakitha190508':  # ඔබට අවශ්‍ය පරිදි මෙම කෝඩ් එක වෙනස් කරගත හැක
            flash('Invalid Invite Code! This app is only for friends.')
            return redirect(url_for('register_profile'))
            
        username = request.form.get('username').strip()
        password = request.form.get('password')
        age = request.form.get('age')
        gender = request.form.get('gender')
        about = request.form.get('about')
        
        if not (any(c.isupper() for c in password) and 
                any(c.islower() for c in password) and 
                any(c.isdigit() for c in password) and 
                any(not c.isalnum() for c in password)):
            flash('Password must include uppercase letters, lowercase letters, numbers, and symbols (e.g., @, #).')
            return redirect(url_for('register_profile'))
            
        file = request.files.get('profile_pic')
        pic_filename = 'default.png'
        if file and file.filename != '':
            pic_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_filename))
            
        password_hash = generate_password_hash(password)
        unique_code = generate_unique_code()
        email = session.get('temp_email')
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, unique_code, profile_pic, age, gender, about, is_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (username, email, password_hash, unique_code, pic_filename, age, gender, about))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('This username or email is already in use.')
            conn.close()
            return redirect(url_for('register_profile'))
        conn.close()
        
        session.clear()
        return redirect(url_for('login'))
        
    return render_template('register_profile.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT username, unique_code, profile_pic FROM users WHERE id = ?', (user_id,))
    user_row = cursor.fetchone()
    
    if user_row:
        username = user_row[0]
        unique_code = user_row[1]
        profile_pic = user_row[2] if user_row[2] else 'default.png'
    else:
        conn.close()
        session.clear()
        return redirect(url_for('login'))
    
    cursor.execute('''
        SELECT fr.id, u.id, u.username, u.profile_pic, u.unique_code 
        FROM friend_requests fr
        JOIN users u ON fr.sender_id = u.id
        WHERE fr.receiver_id = ? AND fr.status = 'pending'
    ''', (user_id,))
    pending_requests = cursor.fetchall()
    
    cursor.execute('''
        SELECT u.id, u.username, u.profile_pic, u.unique_code 
        FROM friend_requests fr
        JOIN users u ON (fr.sender_id = u.id OR fr.receiver_id = u.id)
        WHERE (fr.sender_id = ? OR fr.receiver_id = ?) AND fr.status = 'accepted' AND u.id != ?
    ''', (user_id, user_id, user_id))
    friends = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                           username=username, 
                           unique_code=unique_code, 
                           profile_pic=profile_pic, 
                           requests=pending_requests, 
                           friends=friends)

@app.route('/search', methods=['POST'])
def search_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    code = request.form.get('unique_code')
    current_user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, unique_code, profile_pic, age, gender, about 
        FROM users WHERE unique_code = ? AND id != ?
    ''', (code, current_user_id))
    target_user = cursor.fetchone()
    conn.close()
    
    if not target_user:
        flash('No user found matching this unique code.')
        return redirect(url_for('dashboard'))
        
    return render_template('profile_view.html', user=target_user)

@app.route('/send-request/<int:receiver_id>', methods=['POST'])
def send_request(receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    sender_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM friend_requests 
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
    ''', (sender_id, receiver_id, receiver_id, sender_id))
    existing = cursor.fetchone()
    
    if not existing:
        cursor.execute('''
            INSERT INTO friend_requests (sender_id, receiver_id, status)
            VALUES (?, ?, 'pending')
        ''', (sender_id, receiver_id))
        conn.commit()
        flash('Friend request sent successfully!')
    else:
        flash('A request or connection with this user already exists.')
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/handle-request/<int:req_id>/<action>', methods=['POST'])
def handle_request(req_id, action):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if action == 'accept':
        cursor.execute("UPDATE friend_requests SET status = 'accepted' WHERE id = ?", (req_id,))
        conn.commit()
        flash('Friend request accepted! You can now chat.')
    elif action == 'delete':
        cursor.execute("DELETE FROM friend_requests WHERE id = ?", (req_id,))
        conn.commit()
        flash('Friend request removed.')
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/chat/<int:friend_id>')
def chat_room(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM friend_requests 
        WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        AND status = 'accepted'
    ''', (user_id, friend_id, friend_id, user_id))
    relation = cursor.fetchone()
    
    if not relation:
        conn.close()
        flash('You must accept a friend request with this user before chatting.')
        return redirect(url_for('dashboard'))
        
    cursor.execute('SELECT id, username, profile_pic FROM users WHERE id = ?', (friend_id,))
    friend = cursor.fetchone()
    
    cursor.execute('''
        SELECT sender_id, receiver_id, message, timestamp FROM messages
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        ORDER BY timestamp ASC
    ''', (user_id, friend_id, friend_id, user_id))
    messages = cursor.fetchall()
    
    conn.close()
    return render_template('chat.html', friend=friend, messages=messages, current_user_id=user_id)

@socketio.on('send_private_message')
def handle_private_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    message = data['message']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (sender_id, receiver_id, message))
    conn.commit()
    conn.close()
    
    emit('receive_private_message', {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'message': message
    }, broadcast=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/nearby-users')
def nearby_users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    current_user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, unique_code, profile_pic, age, gender, about 
        FROM users WHERE id != ?
    ''', (current_user_id,))
    users = cursor.fetchall()
    conn.close()
    
    return render_template('nearby_users.html', users=users)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)