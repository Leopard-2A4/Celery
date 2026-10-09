"""
В этом файле будут Celery-задачи
"""
"""Celery приложение с Beat для периодических задач"""
from celery import Celery

celery_app = Celery(
    'homework',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['tasks']
)

celery_app.conf.beat_schedule = {
    'send-weekly-newsletter': {
        'task': 'tasks.send_newsletter',
        'schedule': 168 * 60,
    },
}
celery_app.conf.timezone = 'Europe/Moscow'