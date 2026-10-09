"""
В этом файле будет ваше Flask-приложение
"""
"""Flask приложение для сервиса обработки изображений"""
from flask import Flask, request, jsonify
import os
import uuid
import sqlite3
from tasks import process_images_task

app = Flask(__name__)


os.makedirs('uploads', exist_ok=True)
os.makedirs('processed', exist_ok=True)


def init_db():
    conn = sqlite3.connect('service.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, email TEXT, total INTEGER, processed INTEGER DEFAULT 0, status TEXT DEFAULT 'pending')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS subscribers (email TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

@app.route('/blur', methods=['POST'])
def blur():
    """Загрузка изображений на обработку"""
    if 'images' not in request.files:
        return jsonify({'error': 'No images'}), 400

    files = request.files.getlist('images')
    email = request.form.get('email', '')

    task_id = str(uuid.uuid4())
    image_paths = []

    for file in files:
        if file and file.filename:
            path = f'uploads/{task_id}_{file.filename}'
            file.save(path)
            image_paths.append(path)

    conn = sqlite3.connect('service.db')
    conn.execute('INSERT INTO tasks VALUES (?, ?, ?, 0, ?)',
                 (task_id, email, len(image_paths), 'pending'))
    conn.commit()
    conn.close()

    process_images_task.delay(task_id, email, image_paths)

    return jsonify({'task_id': task_id, 'total': len(image_paths), 'status': 'queued'}), 202


@app.route('/status/<task_id>')
def status(task_id):
    """Статус задачи"""
    conn = sqlite3.connect('service.db')
    conn.row_factory = sqlite3.Row
    task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    conn.close()

    if not task:
        return jsonify({'error': 'Not found'}), 404

    return jsonify({
        'task_id': task_id,
        'progress': task['processed'],
        'total': task['total'],
        'status': task['status']
    })


@app.route('/subscribe', methods=['POST'])
def subscribe():
    """Подписка на рассылку"""
    email = request.json.get('email') if request.json else request.form.get('email')
    if not email:
        return jsonify({'error': 'Email required'}), 400

    conn = sqlite3.connect('service.db')
    conn.execute('INSERT OR IGNORE INTO subscribers VALUES (?)', (email,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Subscribed', 'email': email}), 201


@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Отписка от рассылки"""
    email = request.json.get('email') if request.json else request.form.get('email')
    if not email:
        return jsonify({'error': 'Email required'}), 400

    conn = sqlite3.connect('service.db')
    conn.execute('DELETE FROM subscribers WHERE email = ?', (email,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Unsubscribed', 'email': email})


if __name__ == '__main__':
    init_db()
    app.run(port=5000, debug=True)