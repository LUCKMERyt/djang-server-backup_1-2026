from django.contrib import admin
from django.urls import path
from hello import views
from hello import telegram_control
from django.conf import settings
from django.conf.urls.static import static


from django.urls import re_path
from django.views.static import serve




urlpatterns = [
    # NOTE: Именованные маршруты используются в шаблонах через тег url.
    path('', views.index, name='index'),
    path('reg/', views.reg, name='reg'),
    path('admin/', admin.site.urls),
    path('index/', views.index, name='index'),
    path('weo/', views.weo, name='weo'),
    path('blog/', views.blog, name='blog'),
    path('products/', views.products, name='products'),
    # NOTE: str вместо slug: встроенный slug-конвертер Django принимает только ASCII.
    path('products/<str:slug>/', views.product_detail, name='product_detail'),
    path('products/<str:slug>/inquiry/', views.product_inquiry_form, name='product_inquiry_form'),
    path('news/', views.news, name='news'),
    path('vhod/', views.vhod, name='vhod'),
    path('account/', views.account, name='account'),
    path('vyhod/', views.vyhod, name='vyhod'),
    path('reviews/', views.reviews_page, name='reviews'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
    path('telegram-control/', telegram_control.mini_app_page, name='telegram_control'),
    path('telegram-control/api/status/', telegram_control.mini_app_status, name='telegram_control_status'),
    path('telegram-control/api/logs/', telegram_control.mini_app_logs, name='telegram_control_logs'),
    path('telegram-control/api/action/', telegram_control.mini_app_action, name='telegram_control_action'),

]


urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
if settings.DEBUG:
    # ! В production media должен обслуживать Nginx, CDN или object storage.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
