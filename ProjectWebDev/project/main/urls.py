from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name="home"),
    path('login/', views.login_page, name="login"),
    path('logout/', views.logout_page, name="logout"),
    path('dashboard/', views.dashboard_page, name="dashboard"),
    path('products/', views.products_page, name="products"),
    path('products/manage', views.manage_product_page, name="manageproduct"),
    path('reports/', views.reports_page, name="reports"),
    path('accounts/', views.accounts_page, name="accounts"),
    path('accounts/manage', views.manage_user_page, name="manageuser"),
]