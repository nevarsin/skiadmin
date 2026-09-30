from dataclasses import dataclass

from django.db import models
from django.db.models import OuterRef, Sum, Subquery
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.transactions.models import TransactionLine

SKIPASS_CATEGORY = "skipass"


class SkipassUsage(models.Model):
    date = models.DateField(_("Ski day"))
    associate = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="skipass_usages")
    article = models.ForeignKey(
        Article,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skipass_usages",
    )
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "associate"],
                name="unique_skipass_usage_per_day",
            ),
        ]

    def __str__(self):
        return f"{self.associate} - {self.date.strftime('%d/%m/%Y')}"


def skipass_article_map():
    """
    Maps associate_id -> skipass article_id for every associate that bought a skipass.
    Quantities are always summed per associate, so this is only used to group and label
    rows; an associate holding more than one skipass article just gets one of them.
    """
    return {
        associate_id: article_id
        for associate_id, article_id in TransactionLine.objects.filter(
            article__category=SKIPASS_CATEGORY, article__isnull=False
        ).values_list("associate_id", "article_id").distinct()
    }


@dataclass
class SkipassStockRow:
    associate: Associate
    article: Article | None
    purchased: int
    consumed: int
    remaining: int


def skipass_stock():
    """
    Returns a list of SkipassStockRow for every associate holding at least one skipass.
    """
    purchased_sq = (
        TransactionLine.objects
        .filter(associate=OuterRef("pk"), article__category=SKIPASS_CATEGORY, article__isnull=False)
        .values("associate_id")
        .annotate(total=Sum("quantity"))
        .values("total")
    )
    consumed_sq = (
        SkipassUsage.objects
        .filter(associate=OuterRef("pk"))
        .values("associate_id")
        .annotate(total=Sum("quantity"))
        .values("total")
    )

    article_map = skipass_article_map()
    articles = Article.objects.in_bulk(article_map.values())
    stock = []
    qs = (
        Associate.objects
        .annotate(
            skipass_purchased=Coalesce(Subquery(purchased_sq), 0),
            skipass_consumed=Coalesce(Subquery(consumed_sq), 0),
        )
        .filter(skipass_purchased__gt=0)
        .order_by("last_name", "first_name")
    )
    for associate in qs:
        article_id = article_map.get(associate.pk)
        stock.append(SkipassStockRow(
            associate=associate,
            article=articles.get(article_id),
            purchased=associate.skipass_purchased,
            consumed=associate.skipass_consumed,
            remaining=associate.skipass_purchased - associate.skipass_consumed,
        ))
    return stock
