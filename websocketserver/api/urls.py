from django.urls import path
from . import views

urlpatterns = [
    path('', views.ApiBaseView.as_view()),
    path('version',views.ApiVersionView().as_view()),
    path('character', views.CharacterEditorView.as_view()),
    path('game/login', views.GameLoginView.as_view()),
    path('game/assets', views.GameAssetsView.as_view()),
    path('user/inventory', views.InventoryView.as_view()),
    path('user/nft', views.NftView.as_view()),
    path('user/parcels', views.ParcelsView.as_view()),
]
