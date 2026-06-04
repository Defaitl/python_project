from celery import Celery
from config import settings

REDIS_URL = f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0'

celery_instance = Celery(
    'shop_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['celery_utils.email_tasks', 'celery_utils.order_tasks']
)

celery_instance.conf.update(
    task_track_started=True,
    task_routes={
        'send_welcome_email': {'queue': 'io_tasks'},
        'change_password_email': {'queue': 'io_tasks'},
        'send_order_confirmation': {'queue': 'io_tasks'},
        'send_application_result': {'queue': 'io_tasks'},
        'send_moderation_result': {'queue': 'io_tasks'},
        'process_order': {'queue': 'cpu_tasks'},
    }
)