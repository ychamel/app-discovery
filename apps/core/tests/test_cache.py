"""Cache backend selection (platform-staging T-08, DESIGN §4.5).

REDIS_URL set ⇒ the shared RedisCache (limiter correct across gunicorn workers);
unset ⇒ a per-process LocMemCache so local dev / tests are unchanged.
"""

from django.test import SimpleTestCase

from config.settings import _cache_settings


class CacheSelectionTests(SimpleTestCase):
    def test_locmem_when_redis_url_unset(self):
        caches = _cache_settings(None)
        self.assertEqual(
            caches["default"]["BACKEND"],
            "django.core.cache.backends.locmem.LocMemCache",
        )

    def test_locmem_when_redis_url_blank(self):
        caches = _cache_settings("")
        self.assertEqual(
            caches["default"]["BACKEND"],
            "django.core.cache.backends.locmem.LocMemCache",
        )

    def test_rediscache_when_redis_url_set(self):
        caches = _cache_settings("redis://cache:6379/0")
        self.assertEqual(
            caches["default"]["BACKEND"],
            "django.core.cache.backends.redis.RedisCache",
        )
        self.assertEqual(caches["default"]["LOCATION"], "redis://cache:6379/0")
