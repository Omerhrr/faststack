"""FastStack Class-based Views"""

from faststack.faststack.views.base import View, TemplateView, RedirectView
from faststack.faststack.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from faststack.faststack.views.mixins import *

__all__ = [
    "View", "TemplateView", "RedirectView",
    "ListView", "DetailView", "CreateView", "UpdateView", "DeleteView",
]
