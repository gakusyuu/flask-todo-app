from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# データベースの初期化（テーブル作成）
# v2 追加点 期限と優先度を追加
def init_db():
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT,
            priority TEXT DEFAULT '中',
            is_done INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# アプリ起動時にDBを作成
init_db()

# 一覧表示（READ）
# v2変更点 期限が近い順、かつ優先度順にソート
@app.route('/')
def index():
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    # v2 due_dateがからのものは後ろに、あるものは日付順に取得
    c.execute('''
        SELECT id, title, due_date, priority, is_done FROM tasks
        ORDER BY CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END, due_date ASC
    ''')
    tasks = c.fetchall()
    conn.close()
    return render_template('index.html', tasks=tasks)

# タスク追加（CREATE）
# v2変更点 期限日・優先度を受け取る
@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title')
    due_date = request.form.get('due_date')
    priority = request.form.get('priority')

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
