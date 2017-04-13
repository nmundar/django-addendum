#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import warnings

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


def get_cache_prefix():
    return 'snippet:'


if hasattr(settings, 'ADDENDUM_CACHE_PREFIX'):
    get_cache_prefix = settings.ADDENDUM_CACHE_PREFIX


def get_cache_key(key):
    return '{0}:{1}'.format(get_cache_prefix(), key)


def set_cached_snippet(key, data):
    """
    Adds a dictionary of snippet text and translations to the cache.
    """
    cache.set(get_cache_key(key), data)


def get_cached_snippet(key, language=''):
    """
    Fetches the snippet from cache.

    Returns the text value (string) of a Snippet or None.

    This method addes every queried key to the cache to ensure that misses
    doesn't continue to generate database lookups. Since `None` is the
    default return value for a cache miss, the method uses -1 as the miss
    value. If this is returned we know that the value should not be present
    in the database, either.

    :param key: the snippet key (string)
    :param language: optional language code (string)
    :returns: text of snippet (string) or None
    """
    # TODO on fallback try looking for parent language string, e.g. if 'es-ar'
    # is missing then try looking for 'es'.

    snippet = cache.get(get_cache_key(key))

    # Previous cache miss and DB miss
    if snippet == -1:
        return None

    # First cache miss
    if snippet is None:
        try:
            snippet = Snippet.objects.get(key=key)
        except Snippet.DoesNotExist:
            cache.set(get_cache_key(key), -1)
            snippet = {'': None}
        else:
            set_cached_snippet(snippet.key, snippet.to_dict())
            snippet = snippet.to_dict()

    return snippet.get(language, snippet.get(''))


class CachedManager(models.Manager):

    def get_from_cache(self, key):
        """
        DEPRECATED.

        Use get_cached_snippet instead.
        """
        warnings.warn("The CachedManager is now deprecated, use get_cached_text instead",
                DeprecationWarning)
        snippet = cache.get(get_cache_key(key))

        if snippet == -1:
            return None

        if snippet is None:
            try:
                snippet = Snippet.objects.get(key=key)
            except Snippet.DoesNotExist:
                cache.set(get_cache_key(key), -1)
            else:
                cache.set(get_cache_key(key), snippet)

        return snippet


class Snippet(models.Model):
    """
    Model for storing snippets of text for replacement in templates.

    This should be used for the default language in the case of a multilingual
    app.
    """
    key = models.CharField(max_length=250, primary_key=True)
    text = models.TextField()
    objects = CachedManager()

    class Meta:
        ordering = ('key',)

    def __str__(self):
        return self.key

    def to_dict(self):
        """
        Builds a dictionary of snippet text and translations to the cache.

        The default text has the key of an empty string.

            {
                "": "Hello, humans",
                "es": "Hola, humanos",
                "en-au": "G'day, humans",
            }

        """
        data = {
            trans.language: trans.text for trans in
            SnippetTranslation.objects.filter(snippet_id=self.key)
        }
        data.update({'': self.text})
        return data

    def save(self, *args, **kwargs):
        super(Snippet, self).save(*args, **kwargs)
        set_cached_snippet(self.key, self.to_dict())
        return self


@receiver(post_delete, sender=Snippet)
def delete_snippet(instance, **kwargs):
    cache.delete(get_cache_key(instance.key))


class SnippetTranslation(models.Model):
    """
    Additional text copies of the original snippet for use with the specified
    language.
    """
    snippet = models.ForeignKey(Snippet, related_name="translations")
    language = models.CharField(max_length=5)
    text = models.TextField()

    class Meta:
        unique_together = ('snippet', 'language')

    def __str__(self):
        return "{0} ({1})".format(self.snippet, self.language)

    def save(self, *args, **kwargs):
        super(SnippetTranslation, self).save(*args, **kwargs)
        set_cached_snippet(self.snippet_id, self.snippet.to_dict())
        return self


@receiver(post_delete, sender=SnippetTranslation)
def delete_snippet_translation(instance, **kwargs):
    """
    After removing from the database update the snippet cache values.
    """
    set_cached_snippet(instance.snippet_id, instance.snippet.to_dict())
