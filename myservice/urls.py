from django.urls import path
from myapp import views
from .views import get_random_explanations

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('find-id/', views.FindIdView.as_view(), name='findid'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='resetpassword')
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('api/questions/random_explanations/', get_random_explanations),
]
