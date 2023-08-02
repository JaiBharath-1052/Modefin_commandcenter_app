import os
import asyncio
import aioredis
# import uvloop
import socket
import uuid
import contextvars


REDIS_HOST = 'localhost'
REDIS_PORT = 6379
XREAD_TIMEOUT = 0
XREAD_COUNT = 100
NUM_PREVIOUS = 30
STREAM_MAX_LEN = 1000
ALLOWED_ROOMS = ['chat:1', 'chat:2', 'chat:3']
PORT = 9080
HOST = "0.0.0.0"

cvar_client_addr = contextvars.ContextVar('client_addr', default=None)
cvar_chat_info = contextvars.ContextVar('chat_info', default=None)
cvar_tenant = contextvars.ContextVar('tenant', default=None)
cvar_redis = contextvars.ContextVar('redis', default=None)


# pool = await aioredis.create_redis_pool((REDIS_HOST, REDIS_PORT), encoding='utf-8')
