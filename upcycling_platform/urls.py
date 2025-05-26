# upcycling_platform/urls.py
from django.contrib import admin
from django.urls import path, include # Make sure 'include' is here!
# --- NEW IMPORTS FOR MEDIA FILES ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')), # For Django's built-in login/logout
    path('requests/', include('requests.urls')), # <--- THIS LINE IS CRUCIAL
    path('', include('requests.urls')), # Assuming your home page is in requests.urls
]

# --- NEW: Serve media files only in development mode ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)