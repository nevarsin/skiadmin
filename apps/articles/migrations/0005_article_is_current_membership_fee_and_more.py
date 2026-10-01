from django.db import migrations, models


def flag_current_membership_articles(apps, schema_editor):
    """Hand the two flags to the season's existing membership fee articles.

    A no-op on any database that does not have them (e.g. a fresh test run),
    since ``update()`` on an empty queryset touches nothing.
    """
    Article = apps.get_model("articles", "Article")
    Article.objects.filter(name="Tessera 2025/2026").update(is_current_membership_fee=True)
    Article.objects.filter(name="Tessera ragazzi 2025/2026").update(
        is_current_minor_membership_fee=True
    )


def unflag_current_membership_articles(apps, schema_editor):
    """Reverse: drop the flags, leaving the articles themselves alone."""
    Article = apps.get_model("articles", "Article")
    Article.objects.update(
        is_current_membership_fee=False, is_current_minor_membership_fee=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0004_alter_article_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="is_current_membership_fee",
            field=models.BooleanField(
                default=False,
                help_text="Auto-added to a transaction when an inactive associate buys something. Only one article may carry this flag.",
                verbose_name="Current membership fee",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="is_current_minor_membership_fee",
            field=models.BooleanField(
                default=False,
                help_text="Auto-added instead of the one above for members aged 14 or under. Only one article may carry this flag.",
                verbose_name="Current membership fee (kids)",
            ),
        ),
        migrations.RunPython(
            flag_current_membership_articles, unflag_current_membership_articles
        ),
    ]
