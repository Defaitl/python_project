from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from fastapi import Depends
from services.user_service import UserService
from repositories.user_repo import UserRepository
from services.product_service import ProductService
from repositories.product_repo import ProductRepository
from services.order_service import OrderService
from repositories.order_repo import OrderRepository
from services.admin_service import AdminService
from repositories.shop_prod_repo import ShopProductRepository
from services.shop_prod_service import ShopProductService
from repositories.seller_applic_repo import SellerApplicationRepository
from services.seller_application_service import SellerApplicationService
from repositories.shop_repo import ShopRepository
from services.shop_service import ShopService
from repositories.category_repo import CategoryRepository
from services.category_service import CategoryService
from repositories.moderation_repo import ModerationRepository
from services.moderation_service import ModerationService
from services.redis_service import RedisService

def get_user_service(db : AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))
def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(ProductRepository(db), UserRepository(db), OrderRepository(db), ShopProductRepository(db), ShopRepository(db), db)
def get_product_service(db : AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))
def get_admin_service(db : AsyncSession = Depends(get_db)) -> AdminService:
    return AdminService(UserRepository(db), OrderRepository(db))
def get_seller_application_serivce(db : AsyncSession = Depends(get_db)) -> SellerApplicationService:
    return SellerApplicationService(SellerApplicationRepository(db), UserRepository(db))
def get_shop_service(db : AsyncSession = Depends(get_db)) -> ShopService:
    return ShopService(ShopRepository(db), UserRepository(db))
def get_category_service(db : AsyncSession = Depends(get_db)) -> CategoryService:
    return CategoryService(CategoryRepository(db), RedisService())
def get_moderation_service(db : AsyncSession = Depends(get_db)) -> ModerationService:
    return ModerationService(ModerationRepository(db), ShopRepository(db))
def get_shop_prod_service(db : AsyncSession = Depends(get_db)) -> ShopProductService:
    return ShopProductService(CategoryRepository(db), ShopProductRepository(db), ShopRepository(db), ProductRepository(db), RedisService())