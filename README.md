<div align="center">

# Async FastAPI Shop Engine

Асинхронный backend интернет-магазина с полноценной event-driven инфраструктурой. Проект портфолийный, демонстрирует работу с production-стеком на реальных паттернах.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy_2.0-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-Event_Driven-231F20?style=for-the-badge&logo=apachekafka&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Task_Queue-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?style=for-the-badge&logo=nginx&logoColor=white)

</div>

---

## Технологический стек

| Слой | Технологии |
|------|-----------|
| Framework | FastAPI (Full Async) |
| Database | PostgreSQL + SQLAlchemy 2.0 Async |
| Cache | Redis |
| Message Broker | Apache Kafka + aiokafka |
| Task Queue | Celery (два воркера: io / cpu) |
| Monitoring | Flower (Celery dashboard) |
| Migrations | Alembic |
| Auth | JWT + Passlib (Bcrypt) |
| Proxy | Nginx (reverse proxy + load balancing) |
| DevOps | Docker + Docker Compose |

---

## Архитектура

Layered Architecture с явным разделением ответственности:

```
Routers → Services → Repositories → Models
```

- **Routers** — HTTP слой, валидация входных данных через Pydantic v2
- **Services** — бизнес-логика, оркестрация зависимостей
- **Repositories** — изолированный CRUD через SQLAlchemy async
- **Kafka** — асинхронная доставка событий между сервисами

---

## Ролевая модель (RBAC)

| Роль | Возможности |
|------|------------|
| `user` | Просмотр каталога, создание заказов |
| `seller` | Управление своим магазином и товарами |
| `admin` | Управление пользователями, заявками, модерация магазинов |
| `creator` | Все права admin + управление ролями пользователей |
| `banned` | Доступ заблокирован независимо от токена |

Переход `user → seller` через заявку, рассматриваемую администратором.

---

## Event-Driven обработка

```
POST /orders
    └── Kafka producer → топик order_created
            └── order_consumer
                    ├── process_order.delay()        # обработка по этапам
                    └── send_order_confirmation.delay()  # email пользователю

PATCH /admin/seller-applications/{id}/review
    └── Kafka producer → топик seller.notification
            └── notify_consumer → send_application_result.delay()

PATCH /admin/moderation/{id}/review
    └── Kafka producer → топик seller.notification
            └── notify_consumer → send_moderation_result.delay()
```

---

## Celery воркеры

| Воркер | Pool | Очередь | Задачи |
|--------|------|---------|--------|
| `shop_worker_io` | eventlet | `io_tasks` | Email уведомления |
| `shop_worker_cpu` | prefork | `cpu_tasks` | Обработка заказов по этапам (pending → processing → shipping → delivered) |

Мониторинг воркеров — Flower, доступен по адресу `/flower/` (закрыт basic auth через Nginx).

---

## Безопасность

- **JWT Blacklist** — при логауте JTI токена заносится в Redis с TTL равным оставшемуся времени жизни
- **Rate Limiting** — Sliding Window через Redis Sorted Set, ключ по `user_id` (fallback на IP для неавторизованных)
- **Бан-система** — статус бана кешируется в Redis, проверяется на каждый запрос
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`
- **server_tokens off** — версия Nginx скрыта из заголовков

---

## Redis кэширование

- Категории — Set с TTL
- Продукты магазина — JSON string через `setex`
- Статистика уникальных активных пользователей за сутки (доступна администратору)

---

## Тестирование

Проект покрыт автоматизированными тестами на pytest + pytest-asyncio.
Тесты роутеров реализованы через моки сервисов (`AsyncMock`) без поднятия реальной БД.

```bash
pytest tests --cov=routers --cov=services -s
```

---

## Быстрый запуск

1. Клонируй репозиторий:
```bash
git clone https://github.com/Alex21D31/alex_async_fastapi_21d31.git
```

2. Создай `.env` файл по примеру `.env.example`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/shop
SECRET_KEY=your-secret-key
ALGORITHM=HS256
LIVE_TIME=30
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_NAME=your-db-name
REDIS_HOST=redis
REDIS_PORT=6379
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

3. Запусти:
```bash
docker compose up --build
```

- Swagger UI: `http://localhost/docs`
- Flower: `http://localhost/flower/`

---

## Структура проекта

```
SHOP_PROJECT/
├── alembic/                    # Миграции БД
├── celery_utils/
│   ├── celery_app.py           # Конфигурация + роутинг очередей
│   ├── email_tasks.py          # Email задачи
│   └── order_tasks.py          # process_order по этапам
├── kafka_utils/
│   ├── producer.py             # Отправка событий
│   ├── consumer.py             # order_created консьюмер
│   └── notify_consumer.py      # seller.notification консьюмер
├── repositories/               # CRUD слой (SQLAlchemy)
├── routers/                    # API эндпоинты
├── services/                   # Бизнес-логика
├── tests/                      # Тесты
├── auth.py                     # JWT аутентификация
├── config.py                   # Настройки (.env)
├── database.py                 # Async engine + session
├── decorators.py               # RBAC декораторы
├── dependencies.py             # DI зависимости
├── docker-compose.yaml         # Полная инфраструктура
├── main.py                     # Точка входа + lifespan
├── middleware.py               # Logging + Rate Limiting
├── models.py                   # SQLAlchemy модели
├── nginx.conf                  # Reverse proxy + security
├── schemas.py                  # Pydantic схемы
└── requirements.txt
```