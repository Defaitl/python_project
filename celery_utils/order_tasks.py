from .celery_app import celery_instance
from database import session
from models import Order, TaskStage
from sqlalchemy import select
import logging
import time
import asyncio

logger = logging.getLogger(__name__)

async def _update_task_stage(order_id: int, stage: str):
    async with session() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order:
            order.task_stage = stage
            await db.commit()
@celery_instance.task(name='process_order', bind=True)
def process_order(self, order_id: int):
    """
    Обработка заказа по этапам.
    Обновляет task_stage в БД на каждом шаге.
    """
    stages = [
        (TaskStage.processing, 'Заказ принят в обработку', 7),
        (TaskStage.shipping, 'Заказ передан в доставку', 10),
        (TaskStage.delivered, 'Заказ доставлен', 5),
    ]
    try:
        for stage, message, delay in stages:
            logger.info(f'Заказ #{order_id}: {message}')
            asyncio.run(_update_task_stage(order_id, stage))
            time.sleep(delay)
    except Exception as exc:
        logger.error(f'Ошибка обработки заказа #{order_id}: {exc}')
        raise self.retry(exc=exc, countdown=10, max_retries=3)

    return {'order_id': order_id, 'status': 'delivered'}