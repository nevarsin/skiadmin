from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext as _
from .models import Article
from .forms import ArticleForm

def list_articles(request):
    articles = Article.objects.all()
    return render(request, "articles/list.html", {"articles": articles})

def add_article(request):
    if request.method == "POST":
        form = ArticleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Article created successfully."))
            return redirect("list_articles")
    else:
        form = ArticleForm()
    template_data = {}
    template_data["header"] = _("New Article")
    return render(request, "articles/manage.html", {"form": form,'template_data': template_data})

def delete_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.method == "POST":
        article.delete()
        messages.success(request, _("Article deleted successfully."))
        return redirect("list_articles")  # Replace with your associates listing view name
    return render(request, "articles/confirm_delete.html", {"object": article, "type": "Article"})

def edit_article(request, pk):
    article = get_object_or_404(Article, pk=pk)

    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, _("Article")+" "+article.name+" "+_("edited successfully."))
            return redirect('list_articles')  # Redirect to the list view after saving
    else:
        form = ArticleForm(instance=article)
    template_data = {}
    template_data["header"] = _("Edit Article")
    return render(request, 'articles/manage.html', {'form': form, 'article': article, 'template_data': template_data})

def get_article_price(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return JsonResponse({"price": article.price})