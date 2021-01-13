from django.shortcuts import render
from django.views import View


# Create your views here.
class LandingView(View):
    template = "home.html"

    def get(self, request, **kwargs):
        return render(request, self.template, {})

    def dispatch(self, *args, **kwargs):
        return super(LandingView, self).dispatch(*args, **kwargs)
