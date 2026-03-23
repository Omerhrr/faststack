"""FastStack Class-based Views"""

from faststack.views.base import View, TemplateView, RedirectView
from faststack.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from faststack.views.mixins import *

__all__ = [
    "View", "TemplateView", "RedirectView",
    "ListView", "DetailView", "CreateView", "UpdateView", "DeleteView",
]
