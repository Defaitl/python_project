from schemas import CreateOrder, OutOrder, UpdateOrder, OutOrderWithWarnings
from fastapi import APIRouter, Depends
from dependencies import get_order_service
from services.order_service import OrderService
from auth import verify_token
from decorators import require_role
from models import Status
from aiokafka import AIOKafkaProducer
from kafka_utils.producer import get_producer
router = APIRouter(prefix='/orders', tags=['orders'])

@router.post('', response_model=OutOrderWithWarnings)
async def create_order(new_order : CreateOrder, token_data : dict = Depends(verify_token), service : OrderService = Depends(get_order_service),producer: AIOKafkaProducer = Depends(get_producer)):
    """
    Создание заказа.
    """
    return await service.create_order(token_data, new_order, producer)
@router.get('', response_model=list[OutOrder])
async def get_my_orders(token_data : dict = Depends(verify_token), service : OrderService = Depends(get_order_service)):
    """
    Просмотр всех заказов пользователя.
    """
    return await service.get_all_orders(token_data)
@router.get('/task_status/{id}')
async def get_task_status(id : int, token_data : dict = Depends(verify_token), service : OrderService = Depends(get_order_service)):
    return await service.get_task_status(id, token_data)
@router.get('/{id}', response_model=OutOrder)
async def get_one_order(id : int, token_data : dict = Depends(verify_token), service : OrderService = Depends(get_order_service)):
    """
    Просмотр заказа пользователя по ID.
    """
    return await service.get_one_order(id, token_data)
@router.patch('/status/{id}',response_model=OutOrder)
@require_role('admin', 'creator')
async def update_status(id : int, new_status : Status,token_data : dict = Depends(verify_token), service : OrderService = Depends(get_order_service)):
    """
    Изменение статуса заказа.
    """
    return await service.update_status(id, new_status)
@router.patch('/{id}',response_model=OutOrder)
async def update_order(id : int, new_data : UpdateOrder, token_data : dict = Depends(verify_token), service : OrderService = Depends(get_order_service)):
    """
    Изменение данных заказа.
    """
    return await service.update_order(id, new_data)
@router.delete('/{id}')
@require_role('admin', 'creator')
async def delete_order(id : int,  token_data : dict = Depends(verify_token), service : OrderService = Depends(get_order_service)):
    """
    Удаление заказа.
    """
    return await service.delete_order(id)