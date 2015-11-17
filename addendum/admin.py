from django.contrib import admin

from .models import Snippet


class SnippetAdmin(admin.ModelAdmin):
    list_display = ('key', 'text')
    search_fields = ['key', 'text']


admin.site.register(Snippet, SnippetAdmin)
