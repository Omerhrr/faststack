"""Generic Views"""
from faststack.faststack.views.base import View, TemplateView, RedirectView


class ListView(View):
    """Display a list of objects."""
    
    model = None
    template_name = None
    context_object_name = None
    paginate_by = None
    
    async def get(self, request, **kwargs):
        from sqlmodel import Session
        session = Session()
        objects = session.exec(self.get_queryset()).all()
        context = {self.get_context_object_name(): objects}
        return self.render(context)
    
    def get_queryset(self):
        from sqlmodel import select
        return select(self.model)
    
    def get_context_object_name(self):
        if self.context_object_name:
            return self.context_object_name
        return f"{self.model.__name__.lower()}_list"


class DetailView(View):
    """Display a single object."""
    
    model = None
    template_name = None
    context_object_name = "object"
    pk_url_kwarg = "pk"
    
    async def get(self, request, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        from sqlmodel import Session, select
        session = Session()
        obj = session.exec(select(self.model).where(self.model.id == pk)).first()
        if obj is None:
            from starlette.exceptions import HTTPException
            raise HTTPException(404)
        return self.render({self.context_object_name: obj})


class CreateView(View):
    """Create a new object."""
    
    model = None
    form_class = None
    template_name = None
    success_url = None
    
    async def get(self, request, **kwargs):
        form = self.get_form()
        return self.render({"form": form})
    
    async def post(self, request, **kwargs):
        form_data = await request.form()
        form = self.get_form(data=dict(form_data))
        if form.is_valid():
            return self.form_valid(form)
        return self.render({"form": form})
    
    def get_form(self, data=None):
        return self.form_class(data=data)
    
    def form_valid(self, form):
        from sqlmodel import Session
        session = Session()
        obj = self.model(**form.cleaned_data)
        session.add(obj)
        session.commit()
        return self.redirect(self.success_url)


class UpdateView(View):
    """Update an existing object."""
    
    model = None
    form_class = None
    template_name = None
    success_url = None
    pk_url_kwarg = "pk"
    
    async def get(self, request, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        from sqlmodel import Session, select
        session = Session()
        obj = session.exec(select(self.model).where(self.model.id == pk)).first()
        if obj is None:
            from starlette.exceptions import HTTPException
            raise HTTPException(404)
        form = self.get_form(instance=obj)
        return self.render({"form": form, "object": obj})
    
    async def post(self, request, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        from sqlmodel import Session, select
        session = Session()
        obj = session.exec(select(self.model).where(self.model.id == pk)).first()
        form_data = await request.form()
        form = self.get_form(data=dict(form_data), instance=obj)
        if form.is_valid():
            return self.form_valid(form, obj, session)
        return self.render({"form": form, "object": obj})
    
    def get_form(self, data=None, instance=None):
        return self.form_class(data=data)
    
    def form_valid(self, form, obj, session):
        for k, v in form.cleaned_data.items():
            setattr(obj, k, v)
        session.add(obj)
        session.commit()
        return self.redirect(self.success_url)


class DeleteView(View):
    """Delete an object."""
    
    model = None
    template_name = None
    success_url = None
    pk_url_kwarg = "pk"
    
    async def get(self, request, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        from sqlmodel import Session, select
        session = Session()
        obj = session.exec(select(self.model).where(self.model.id == pk)).first()
        if obj is None:
            from starlette.exceptions import HTTPException
            raise HTTPException(404)
        return self.render({"object": obj})
    
    async def post(self, request, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        from sqlmodel import Session, select
        session = Session()
        obj = session.exec(select(self.model).where(self.model.id == pk)).first()
        if obj:
            session.delete(obj)
            session.commit()
        return self.redirect(self.success_url)
