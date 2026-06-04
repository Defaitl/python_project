from repositories.order_repo import OrderRepository
from repositories.shop_prod_repo import ShopProductRepository
from repositories.user_repo import UserRepository
from repositories.product_repo import ProductRepository
from repositories.shop_repo import ShopRepository
from schemas import CreateOrder, UpdateOrder
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import Order, OrderItem, Status
from kafka_utils.producer import send_order_event
from sqlalchemy.orm import selectinload
from celery.result import AsyncResult
from sqlalchemy import select
from aiokafka import AIOKafkaProducer
import logging
logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, product_repo: ProductRepository, user_repo: UserRepository, order_repo: OrderRepository, shop_product_repo: ShopProductRepository, shop_repo: ShopRepository, db: AsyncSession):
        self.order_repo = order_repo
        self.shop_product_repo = shop_product_repo
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.shop_repo = shop_repo
        self.db = db
    async def _get_order_or_404(self, order_id: int) -> Order:
        """
        Вспомогательная функция для получения заказа по айди.
        Используется в основных функциях.
        """
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail='Заказ не найден')
        return order
    async def create_order(self, user_data: dict, data: CreateOrder, producer: AIOKafkaProducer) -> dict:
        """
        Создание заказа и списание товаров со склада.

        Процесс:
        1. Ищем магазин по shop_name
        2. Создается объект заказа
        3. Проверяется наличие каждого товара в базе и его количество на складе.
        4. Уменьшается количество товара
        5. Создаются записи OrderItem.
        6. Данные отправляются в Kafka для уведомлений.

        Args:
            user_data : данные пользователя из токена.
            data : Обьект CreateOrder, содержащий в себе список продуктов, отобранных пользователем.
            producer: взаимодействие с Kafka

        Returns:
            Созданный заказ + warnings

        Raises:
            HTTPException: 404, магазин не найден
            HTTPException: 400, ни один товар не прошёл проверку
        """
        try:
            shop = await self.shop_repo.get_by_shop_name(data.shop_name)
            if not shop:
                raise HTTPException(404, f'Магазин {data.shop_name} не найден')

            user = await self.user_repo.get_by_id(int(user_data['sub']))
            order = Order(owner_name=user.username, info=data.info, shop_id=shop.id)
            self.db.add(order)
            await self.db.flush()

            kafka_items = []
            warnings = []

            for item in data.items:
                product_in_shop = await self.shop_product_repo.get_one_product_for_seller_by_name(item.product_name, shop.id)
                if not product_in_shop:
                    warnings.append(f'Товар "{item.product_name}" не найден в магазине {data.shop_name}')
                    continue
                if product_in_shop.quantity < item.quantity:
                    warnings.append(f'Недостаточно товара "{item.product_name}" на складе')
                    continue
                product_in_shop.quantity -= item.quantity
                kafka_items.append({
                    'product_id': product_in_shop.id,
                    'name': item.product_name,
                    'quantity': item.quantity
                })
                order_item = OrderItem(
                    order_id=order.id,
                    product_name=item.product_name,
                    shop_product_id=product_in_shop.id,
                    quantity=item.quantity
                )
                self.db.add(order_item)

            if not kafka_items:
                raise HTTPException(400, 'Ни один товар не прошёл проверку')

            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        query = (
            select(Order)
            .where(Order.id == order.id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product)
            )
        )
        result = await self.db.execute(query)
        order = result.scalar_one()

        try:
            await send_order_event(
                order_id=order.id,
                user_id=user_data['sub'],
                items=kafka_items,
                producer=producer
            )
        except Exception as e:
            logger.error(f'Kafka недоступна, событие для заказа {order.id} потеряно. {e}')

        return {'order': order, 'warnings': warnings}
    async def get_all_orders(self, data : dict) -> list[Order]:
        """
        Получение  информации обо всех заказов пользователя.
        В качестве параметра ID для поиска используется айди пользователя из его Access токена.
        """
        user = await self.user_repo.get_by_id(int(data['sub']))
        return await self.order_repo.get_all_orders_by_user(user.username)
    async def get_one_order(self, order_id : int, data : dict) -> Order:
        """
        Получение  информации об 1 заказе пользователя.

        Args:
            order_id: Айди заказа
            data: Информация о пользователе из Access токена.
        
        Returns:
            Информация о заказе
        
        Raises:
            HTTPException: 404, заказ не найден.
        """ 
        user = await self.user_repo.get_by_id(int(data['sub']))
        result = await self.order_repo.get_by_id_for_user(order_id, user.username)
        if not result:
            raise HTTPException(404, 'Заказ не найден')
        return result
    async def update_order(self, order_id : int, patch_order : UpdateOrder) -> Order:
        """
        Обновление информации о заказе.

        Args:
            order_id: Айди заказа.
            patch_order: Обновляемая информация.

        Returns:
            Обновленный заказ.
        
        Raises:
            HTTPException: 404, заказ не найден. (через _get_order_or_404).
        """
        order = await self._get_order_or_404(order_id)
        return await self.order_repo.update(order, patch_order.model_dump(exclude_none=True)) 
    async def delete_order(self, order_id):
        """
        Удаление заказа

        Args:
            order_id: Айди заказа

        Returns:
            Информация о удалении.
        
        Raises:
            HTTPException: 404, заказ не найден. (через _get_order_or_404).
        """
        order = await self._get_order_or_404(order_id)
        await self.order_repo.delete(order)
        return f'Заказ под номером {order_id} успешно удален.'
    async def update_status(self, order_id : int, new_status : Status):
        """
        Обновление статуса заказа.
        Функция доступна только для ролей Admin и выше.

        Raises:
            HTTPException: 404, заказ не найден. (через _get_order_or_404).
        """
        order = await self._get_order_or_404(order_id)
        return await self.order_repo.update(order, {'status' : new_status})
    async def get_task_status(self, task_id : int, token_data : dict):
        user = await self.user_repo.get_by_id(int(token_data['sub']))
        order = await self.order_repo.get_by_id_for_user(task_id, user.username)
        if not order:
            raise HTTPException(status_code=404, detail='Заказ не найден')
        result = AsyncResult(order.task_id) if order.task_id else None
        return {
            'task_stage': order.task_stage,
            'celery_status': result.status if result else None
        }
