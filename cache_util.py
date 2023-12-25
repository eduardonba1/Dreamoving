import os
from pickle import dumps, loads

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PASS = os.getenv('REDIS_PASS')

from redis import StrictRedis

redis = StrictRedis(host=REDIS_HOST, port=int(os.getenv("REDIS_PORT", "6379")),
                    max_connections=256, password=REDIS_PASS)


class PythonNativeRedisClient(object):
    """A simple redis client for storing and retrieving native python datatypes."""

    def __init__(self, redis_host=redis):
        """Initialize client."""
        self.client = redis_host

    def set(self, key, value, **kwargs):
        """Store a value in Redis."""
        return self.client.set(key, dumps(value), **kwargs)

    def get(self, key, default=None):
        """Retrieve a value from Redis."""
        val = self.client.get(key)
        if val:
            return loads(val)
        return default

    def expire(self, key, expire_secs):
        self.client.expire(key, expire_secs)

    def ttl(self, key):
        self.client.ttl(key)

    def delete(self, key):
        redis.delete(key)

redis_client = PythonNativeRedisClient(redis)


# Reids 缓存，结果保存到 redis 中, 根据函数的第一个参数缓存结果, 可以指定缓存有效期
class RedisCache:
    def __init__(self, expire=60, cache_prefix="redis_cache_"):
        self.expire = expire
        self.cache_prefix = cache_prefix

    def format_key(self, input_key):
        return self.cache_prefix + "_" + input_key

    def get(self, input_key):
        return redis_client.get(self.format_key(input_key))

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # 使用函数的第一个参数作为 limit_key
            key = args[1]
            if key:
                try:
                    cached_value = self.get(key)
                    if cached_value:
                        print("Cached value from redis for method:%s with param:%s" % (func.__name__, str(key)) )
                        return cached_value
                except Exception as ex:
                    print("Error get data from cache, key:%s error message:%s" % (key, repr(ex)))

            result = func(*args, **kwargs)

            try:
                redis_key = self.format_key(key)
                redis_client.set(redis_key, result)
                redis_client.expire(redis_key, self.expire)
            except Exception as ex:
                print("Error put data to cache, key:%s error message:%s" % (key, repr(ex)) )

            return result
        return wrapper # to be used in method within a class