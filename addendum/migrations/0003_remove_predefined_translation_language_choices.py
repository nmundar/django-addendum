# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('addendum', '0002_auto_translations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='snippettranslation',
            name='language',
            field=models.CharField(max_length=5),
        ),
    ]
