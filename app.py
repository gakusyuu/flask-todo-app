from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash,check_password_hash
import sqlite3

app = Flask(__name__)
# セッション暗号化用の秘密鍵
app.secret_key = 'your_secret_key_here'

# データベースの初期化（テーブル作成）
# v2 追加点 期限と優先度を追加
def init_db():
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()

    # v6 ユーザーテーブルの作成
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # v6 user_idを追加
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            due_date TEXT,
            priority TEXT DEFAULT '中',
            is_done INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# アプリ起動時にDBを作成
init_db()

# 一覧表示（READ）
# v2変更点 期限が近い順、かつ優先度順にソート
# v5 検索・フィルター機能追加
# v6 ログインユーザー限定に変更
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    # URLから検索条件を取得
    status_filter = request.args.get('status', 'all')
    keyword = request.args.get('keyword', '').strip()

    conn = sqlite3.connect('todo.db')
    c = conn.cursor()

    # ベースとなるSQLクエリ
    # v6 ユーザー自身のタスクのみ取得するように変更
    query = 'SELECT id, title, due_date, priority, is_done FROM tasks WHERE user_id = ?'
    params = [user_id]

    # ステータスでの絞り込み
    if status_filter == 'active':
        query += ' AND is_done = 0'
    elif status_filter == 'completed':
        query += ' AND is_done = 1'
    # キーワードでの曖昧検索（LIKE）
    if keyword:
        query += ' AND title LIKE ?'
        params.append(f'%{keyword}%')
    # 並び替え（期限が近い順）
    query += ' ORDER BY CASE WHEN due_date IS NULL OR due_date = "" THEN 1 ELSE 0 END, due_date ASC'

    # v2 due_dateがからのものは後ろに、あるものは日付順に取得
    # v5 
    c.execute(query, params)
    tasks = c.fetchall()
    conn.close()
    return render_template(
        'index.html', 
        tasks=tasks,
        status_filter=status_filter,
        keyword=keyword
        )

# ユーザー登録（Sign Up）
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # パスワードのハッシュ化（セキュリティ保護）
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('todo.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('そのユーザー名はすでに使われています')
            return redirect(url_for('register'))
    return render_template('register.html')

# v6 ログイン（Login）
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('todo.db')
        c = conn.cursor()
        c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        # ユーザーが存在しパスワードが一致するか確認
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('ユーザーまたはパスワードが正しくありません')
            return redirect(url_for('login'))
    return render_template('login.html')

# v6 ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# タスク追加（CREATE）
# v2変更点 期限日・優先度を受け取る
@app.route('/add', methods=['POST'])
def add():
    # V6 ログイン状態でのみ追加できるように変更
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    due_date = request.form.get('due_date')
    priority = request.form.get('priority')
    user_id = session['user_id']

    if title:
        conn = sqlite3.connect('todo.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO tasks (title, due_date, priority)
            VALUES (?, ?, ?)
        ''', (title, due_date, priority))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

# v4 変更点 タスク編集　＆　更新処理
@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit(task_id):
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()

    if request.method == 'POST':
        # フォームから入力された値を取得
        title = request.form.get('title')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority')

        # データベースを更新
        c.execute('''
            UPDATE tasks
            SET title = ?, due_date = ?, priority = ?
            WHERE id = ?
        ''', (title, due_date, priority, task_id))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        # 編集対象のタスク情報を取得して編集画面へ渡す
        c.execute('SELECT id, title, due_date, priority FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()
        conn.close()
        return render_template('edit.html', task=task)
 
# v3 追加点 完了/未完了の切り替え
@app.route('/toggle/<int:task_id>')
def toggle(task_id):
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    # 現在の is_done の値(０か１か)を反転させる
    c.execute('UPDATE tasks SET is_done = NOT is_done WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# タスク削除（DELETE）
@app.route('/delete/<int:task_id>')
def delete(task_id):
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
