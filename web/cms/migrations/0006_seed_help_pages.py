from django.db import migrations


def seed_help_pages(apps, schema_editor):
    """
    No-op data migration.

    The previous implementation attempted to use Wagtail tree methods on
    historical migration models and could crash deployment startup.
    Help pages can be created safely from Wagtail admin afterwards.
    """
    return


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0005_alter_sections_with_product_blocks"),
    ]

    operations = [
        migrations.RunPython(seed_help_pages, migrations.RunPython.noop),
    ]

