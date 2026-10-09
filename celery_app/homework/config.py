"""
В этом файле будут секретные данные

Для создания почтового сервиса воспользуйтесь следующими инструкциями

- Yandex: https://yandex.ru/support/mail/mail-clients/others.html
- Google: https://support.google.com/mail/answer/7126229?visit_id=638290915972666565-928115075
"""

# https://yandex.ru/support/mail/mail-clients/others.html

import os

SMTP_USER = "artemrusikhan@gmail.com"
SMTP_PASSWORD = "mxvw cwol xhst adzl"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

CELERY_BROKER = os.environ.get('CELERY_BROKER', 'redis://localhost:6379/0')

SECRET_KEY = 'simple-secret-key'
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
PROCESSED_FOLDER = os.path.join(os.path.dirname(__file__), 'processed')