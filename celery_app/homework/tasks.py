"""Celery задачи"""
"""Celery задачи с реальной отправкой писем"""
import os
import sqlite3
import zipfile
import smtplib
from PIL import Image, ImageFilter
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from celery_app import celery_app
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD


def blur_image(src, dst):
    """Применяет размытие к изображению"""
    try:
        with Image.open(src) as img:
            blurred = img.filter(ImageFilter.GaussianBlur(5))
            blurred.save(dst)
        return True
    except Exception as e:
        print(f"Error blurring image {src}: {e}")
        return False


def send_email(receiver, subject, body, attachments=None):
    """РЕАЛЬНО отправляет письмо на почту через SMTP"""
    print(f"Attempting to send email to: {receiver}")
    print(f"Using SMTP: {SMTP_HOST}:{SMTP_PORT}, User: {SMTP_USER}")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)

            email = MIMEMultipart()
            email['Subject'] = subject
            email['From'] = SMTP_USER
            email['To'] = receiver

            email.attach(MIMEText(body, 'plain'))

            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())

                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{os.path.basename(filepath)}"'
                        )
                        email.attach(part)

            server.send_message(email)
            print(f"✓ Email sent successfully to {receiver}")
            return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ SMTP Authentication Error! Check your SMTP_USER and SMTP_PASSWORD in config.py")
        print(f"  Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error sending email to {receiver}: {e}")
        return False


@celery_app.task(bind=True)
def process_images_task(self, task_id, email, image_paths):
    """Обработка изображений с размытием и отправка на почту"""
    total = len(image_paths)
    processed = 0
    processed_files = []

    for i, path in enumerate(image_paths):
        if not os.path.exists(path):
            continue

        dst = f'processed/blur_{os.path.basename(path)}'
        os.makedirs('processed', exist_ok=True)

        if blur_image(path, dst):
            processed += 1
            processed_files.append(dst)

        conn = sqlite3.connect('service.db')
        conn.execute('UPDATE tasks SET processed = ?, status = ? WHERE id = ?',
                     (processed, 'processing', task_id))
        conn.commit()
        conn.close()

        self.update_state(state='PROGRESS', meta={'processed': processed, 'total': total})

    if processed > 0 and email:
        if processed == 1:
            send_email(
                email,
                'Ваше изображение обработано',
                f'''Здравствуйте!

Ваше изображение было обработано эффектом размытия.
Заказ №{task_id}

Изображение прикреплено к этому письму.

С уважением,
Сервис обработки изображений''',
                processed_files
            )
        else:
            zip_path = f'processed/{task_id}.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for img_path in processed_files:
                    zipf.write(img_path, os.path.basename(img_path))

            send_email(
                email,
                'Ваши изображения обработаны',
                f'''Здравствуйте!

Ваши {processed} изображения были обработаны эффектом размытия.
Заказ №{task_id}

Изображения прикреплены к этому письму в виде архива.

С уважением,
Сервис обработки изображений''',
                [zip_path]
            )

    conn = sqlite3.connect('service.db')
    conn.execute('UPDATE tasks SET status = ? WHERE id = ?', ('completed', task_id))
    conn.commit()
    conn.close()

    return {'processed': processed, 'total': total, 'status': 'completed'}


@celery_app.task
def send_newsletter():
    """Еженедельная рассылка для подписчиков"""
    conn = sqlite3.connect('service.db')
    subscribers = conn.execute('SELECT email FROM subscribers').fetchall()
    conn.close()

    sent = 0
    newsletter_body = """
Здравствуйте!

Это ваше еженедельное обновление от Image Blur Service.

Наш сервис позволяет:
- Загружать несколько изображений сразу
- Применять эффект размытия ко всем изображениям
- Получать обработанные изображения на почту

API endpoints:
- POST /blur - Загрузить изображения
- GET /status/<id> - Проверить статус
- POST /subscribe - Подписаться на newsletter
- POST /unsubscribe - Отписаться

Спасибо, что используете наш сервис!

С уважением,
Команда Image Blur Service
"""

    for row in subscribers:
        if send_email(row[0], 'Еженедельное обновление: Image Blur Service', newsletter_body):
            sent += 1

    return {'sent': sent, 'total_subscribers': len(subscribers)}