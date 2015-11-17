from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings


get_cache_prefix = lambda: 'snippet:'
if hasattr(settings, 'ADDENDUM_CACHE_PREFIX'):
    get_cache_prefix = settings.ADDENDUM_CACHE_PREFIX


class CachedManager(models.Manager):

    def get_from_cache(self, key):
        """
        Fetches the snippet from cache.

        Returns a `Snippet` object or `None`.

        This method addes every queried key to the cache to ensure that misses
        doesn't continue to generate database lookups. Since `None` is the
        default return value for a cache miss, the method uses -1 as the miss
        value. If this is returned we know that the value should not be present
        in the database, either.
        """
        cache_key = '{0}:{1}'.format(get_cache_prefix(), key)
        snippet = cache.get(cache_key)

        if snippet == -1:
            return None

        if snippet is None:
            try:
                snippet = Snippet.objects.get(key=key)
            except Snippet.DoesNotExist:
                cache.set(cache_key, -1)
            else:
                cache.set(cache_key, snippet)

        return snippet


class Snippet(models.Model):
    """
    Model for storing snippets of text for replacement in templates.
    """
    key = models.CharField(max_length=250, primary_key=True)
    text = models.TextField()
    objects = CachedManager()

    class Meta:
        ordering = ('key',)

    def __unicode__(self):
        return self.key


@receiver(post_save, sender=Snippet)
def set_cached_business(sender, **kwargs):
    """Update the cached copy of the snippet on creation or change"""
    instance = kwargs.pop('instance')
    cache_key = '{0}:{1}'.format(get_cache_prefix(), instance.key)
    cache.set(cache_key, instance)


@receiver(post_delete, sender=Snippet)
def clear_cached_business(sender, **kwargs):
    """Remove the cached copy of the snippet after deletion"""
    instance = kwargs.pop('instance')
    cache_key = '{0}:{1}'.format(get_cache_prefix(), instance.key)
    cache.delete(cache_key)
