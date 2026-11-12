from django.urls import path
from .views import Subscribe, SubscriptionAction, Unsubscribe

urlpatterns = [path('subscribe/', Subscribe.as_view()), path('confirm/', SubscriptionAction.as_view()), path('unsubscribe/', Unsubscribe.as_view())]
