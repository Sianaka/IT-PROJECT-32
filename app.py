from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import sqlite3
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')

app.secret_key = '9472transmitancja67'
DB_NAME = 'database.db'

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# --- Data Base ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Tabela treningów 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                age INTEGER,
                level TEXT,
                plan_json TEXT,
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        # Tabela użytkowników
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        
        # Tabela postów
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # Tabela komentarzy
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # Tabela reakcji
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reaction_type TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                UNIQUE(post_id, user_id) 
            )
        """)

        conn.commit()

# --- ROUTING ---

@app.route('/')
def main():
    user = session.get('user')
    return render_template('main.html', user=user)

@app.route('/wywiad')
def survey():
    user = session.get('user')
    return render_template('survey.html', user=user)

@app.route('/plan')
def results():
    if 'user' not in session:
        flash('You need to be logged in to see your plan!', 'info')
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    user = session.get('user')

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workouts WHERE user_id = ? ORDER BY id DESC", (user_id,))
        plans = cursor.fetchall()

        formatted_plans = []
        for p in plans:
            plan_dict = dict(p)
            plan_dict['plan_data'] = json.loads(p['plan_json'])
            formatted_plans.append(plan_dict)

    return render_template('results.html', user=user, plans=formatted_plans)

# --- FORUM ROUTING ---

@app.route('/forum')
def forum():
    user = session.get('user')
    user_id = session.get('user_id')

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, u.username 
            FROM posts p 
            JOIN users u ON p.user_id = u.id 
            ORDER BY p.id DESC
        """)
        posts_rows = cursor.fetchall()
        
        posts_data = []
        for post in posts_rows:
            post_dict = dict(post)
            
            cursor.execute("""
                SELECT c.*, u.username 
                FROM comments c 
                JOIN users u ON c.user_id = u.id 
                WHERE c.post_id = ? 
                ORDER BY c.id ASC
            """, (post['id'],))
            post_dict['comments'] = [dict(c) for c in cursor.fetchall()]

            cursor.execute("SELECT reaction_type, COUNT(*) as count FROM reactions WHERE post_id = ? GROUP BY reaction_type", (post['id'],))
            reactions_count = {row['reaction_type']: row['count'] for row in cursor.fetchall()}
            post_dict['reactions'] = reactions_count

            post_dict['user_reaction'] = None
            if user_id:
                cursor.execute("SELECT reaction_type FROM reactions WHERE post_id = ? AND user_id = ?", (post['id'], user_id))
                my_react = cursor.fetchone()
                if my_react:
                    post_dict['user_reaction'] = my_react['reaction_type']

            posts_data.append(post_dict)

    return render_template('forum.html', user=user, posts=posts_data)

# --- login and register ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password or not confirm_password:
            flash('Fill in all fields!', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))

        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                if cursor.fetchone():
                    flash('This username is already taken!', 'error')
                    return redirect(url_for('register'))

                hashed_password = generate_password_hash(password)
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
                
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('login'))

        except Exception as e:
            flash(f'Data base error: {e}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username') 
        password = request.form.get('password')

        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                session['user'] = user['username']
                session['user_id'] = user['id']
                flash('Logged in succesfuly!', 'success')
                return redirect(url_for('main'))
            else:
                flash('Invalid username or password.', 'error')
                
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    flash('Logged out', 'info')
    return redirect(url_for('main'))

# ----- Plan -----

@app.route('/save_plan', methods=['POST'])
def save_plan():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.get_json()
    
    name = data.get('name')
    age = data.get('age')
    level = data.get('level')
    plan = data.get('plan')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workouts (user_id, name, age, level, plan_json, created_at) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], name, age, level, json.dumps(plan), get_current_time()))
        conn.commit()
        
    return jsonify({"status": "success", "message": "Plan saved successfully!"})

@app.route('/delete_plan/<int:plan_id>', methods=['POST'])
def delete_plan(plan_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workouts WHERE id = ? AND user_id = ?", (plan_id, session['user_id']))
        conn.commit()
    
    return jsonify({"status": "success"})

# ----- Forum -----

@app.route('/add_post', methods=['POST'])
def add_post():
    if 'user_id' not in session:
        flash('Please login to post.', 'error')
        return redirect(url_for('login'))

    content = request.form.get('content')
    if content:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO posts (user_id, content, created_at) VALUES (?, ?, ?)", 
                           (session['user_id'], content, get_current_time()))
            conn.commit()
    
    return redirect(url_for('forum'))

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        flash('Please login to comment.', 'error')
        return redirect(url_for('login'))

    content = request.form.get('content')
    if content:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)", 
                           (post_id, session['user_id'], content, get_current_time()))
            conn.commit()
            
    return redirect(url_for('forum')) 

@app.route('/react/<int:post_id>/<reaction_type>')
def react(post_id, reaction_type):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Login required"}), 401

    allowed_reactions = ['like', 'heart', 'muscle', 'fire']
    if reaction_type not in allowed_reactions:
        return jsonify({"status": "error", "message": "Invalid reaction type"}), 400

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT reaction_type FROM reactions WHERE post_id = ? AND user_id = ?", (post_id, session['user_id']))
        existing = cursor.fetchone()

        if existing:
            if existing[0] == reaction_type:
                cursor.execute("DELETE FROM reactions WHERE post_id = ? AND user_id = ?", (post_id, session['user_id']))
                current_active = None
            else:
                cursor.execute("UPDATE reactions SET reaction_type = ? WHERE post_id = ? AND user_id = ?", (reaction_type, post_id, session['user_id']))
                current_active = reaction_type
        else:
            cursor.execute("INSERT INTO reactions (post_id, user_id, reaction_type) VALUES (?, ?, ?)", (post_id, session['user_id'], reaction_type))
            current_active = reaction_type
        
        conn.commit()

        counts = {}
        for r_type in allowed_reactions:
            cursor.execute("SELECT COUNT(*) FROM reactions WHERE post_id = ? AND reaction_type = ?", (post_id, r_type))
            counts[r_type] = cursor.fetchone()[0]

    return jsonify({
        "status": "success", 
        "counts": counts, 
        "current_active": current_active, 
        "post_id": post_id
    })

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        flash('Login required.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
  
        cursor.execute("SELECT id FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id))
        post = cursor.fetchone()
        
        if post:

            cursor.execute("DELETE FROM reactions WHERE post_id = ?", (post_id,))
            
            cursor.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
            
            cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            
            conn.commit()
            flash('Post deleted successfully.', 'success')
        else:
            flash('You cannot delete this post.', 'error')

    return redirect(url_for('forum'))

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        flash('Login required.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM comments WHERE id = ? AND user_id = ?", (comment_id, user_id))
        comment = cursor.fetchone()
        
        if comment:
            cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
            conn.commit()
            flash('Comment deleted.', 'success')
        else:
            flash('You cannot delete this comment.', 'error')

    return redirect(url_for('forum'))

if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        init_db()
    init_db() 
    
    app.run(debug=True)
