from flask import Flask, render_template, request, redirect
import sqlite3
import random
from flask_mail import Mail, Message

otp_storage = {}  # temporarily holds OTPs
app = Flask(__name__)

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''          # your Gmail
app.config['MAIL_PASSWORD'] = ''             # app password
mail = Mail(app)

# Database Initialization
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            voted INTEGER DEFAULT 0
        )
    ''')

    # Candidates table
    c.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            votes INTEGER DEFAULT 0
        )
    ''')

    # Insert candidates if not present
    c.execute("SELECT COUNT(*) FROM candidates")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO candidates (name) VALUES ('Alice')")
        c.execute("INSERT INTO candidates (name) VALUES ('Bob')")
        c.execute("INSERT INTO candidates (name) VALUES ('Charlie')")

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return redirect('/register')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", 
                      (name, email, password))
            conn.commit()

            # Generate and Send OTP
            otp = str(random.randint(100000, 999999))
            otp_storage[email] = otp

            msg = Message('Your OTP for Voting System',
                          sender='YOUR_EMAIL@gmail.com',
                          recipients=[email])
            msg.body = f'Your OTP is: {otp}'
            mail.send(msg)

            return render_template('otp_verify.html', email=email)

        except sqlite3.IntegrityError:
            return "⚠️ Email already registered!"
        finally:
            conn.close()

    return render_template('register.html')
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = request.form['email']
    entered_otp = request.form['otp']

    if otp_storage.get(email) == entered_otp:
        del otp_storage[email]
        return redirect(f'/vote?email={email}')  # redirect to voting page
    else:
        return "❌ Invalid OTP. Please try again."
@app.route('/vote')
def vote():
    email = request.args.get('email')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check if user already voted
    c.execute("SELECT voted FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    if result and result[0] == 1:
        return "⚠️ You have already voted."

    # Show candidates
    c.execute("SELECT * FROM candidates")
    candidates = c.fetchall()
    conn.close()

    return render_template('vote.html', candidates=candidates, email=email)
@app.route('/submit_vote', methods=['POST'])
def submit_vote():
    email = request.form['email']
    candidate_id = request.form['candidate_id']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check if user already voted
    c.execute("SELECT voted FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    if result and result[0] == 1:
        return "⚠️ You have already voted."

    # Update candidate vote count
    c.execute("UPDATE candidates SET votes = votes + 1 WHERE id = ?", (candidate_id,))

    # Mark user as voted
    c.execute("UPDATE users SET voted = 1 WHERE email = ?", (email,))

    conn.commit()
    conn.close()

    return "✅ Your vote has been recorded successfully!"
@app.route('/admin')
def admin():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name, votes FROM candidates")
    results = c.fetchall()
    conn.close()
    return render_template('result.html', results=results)

if __name__ == '__main__':
    init_db()  # Create DB tables when app starts
    app.run(debug=True)
