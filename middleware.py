import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from services.redis_service import redis_service
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from jose import jwt
from config import settings

logger = logging.getLogger(__name__)

EXCLUDED_PATHS = ['/products', '/openapi.json', '/docs', '/redoc']

LIMIT = 5
WINDOW = 30

class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request : Request, call_next):
        """
        Логирование входящих запросов и ответов.
        """
        logger.info(f'-> {request.method} {request.url}')
        response = await call_next(request)
        if response.status_code >= 400:
            logger.error(f'<- {response.status_code} {request.method} {request.url}')
        else:
            logger.info(f'<- {response.status_code} {request.method} {request.url}')
        return response
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Ограничение частоты запросов по user_id (если авторизован) или по IP.
        """
        if any(request.url.path.startswith(path) for path in EXCLUDED_PATHS):
            return await call_next(request)

        key_id = request.client.host  # fallback на IP
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split(' ')[1]
                data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                key_id = f"user:{data.get('sub')}"
            except Exception:
                pass  # токен невалидный — используем IP

        key = f'rate_limit:{key_id}'
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - WINDOW
        member = str(uuid.uuid4())
        try:
            await redis_service.redis_client.zremrangebyscore(key, 0, window_start)
            await redis_service.redis_client.zadd(key, {member: now})
            result = await redis_service.redis_client.zcard(key)
            if result > LIMIT:
                return JSONResponse(status_code=429, content={'detail': 'Слишком много запросов. Подождите 30 секунд.'})
        except Exception as e:
            logger.error(f'Ошибка Redis в rate limiter: {e}')
        return await call_next(request)
            