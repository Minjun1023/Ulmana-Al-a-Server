from django.urls import path
from myapp import views
from myapp.views import get_random_explanations
from myapp.views import get_daily_facts
from myapp.views import Genre25QuestionView
from myapp.views import Genre50QuestionView
from myapp.views import SpeedQuizView
from myapp.views import QuizSubmitView

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('find-id/', views.FindIdView.as_view(), name='findid'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='resetpassword'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('api/questions/random_explanations/', get_random_explanations),
    path('daily-facts/', views.get_daily_facts),
    path('questions/genre/25/', Genre25QuestionView.as_view(), name='genre_25_questions'), 
    path('questions/genre/50/', Genre50QuestionView.as_view(), name='genre_50_questions'), 
    path('questions/speed/', SpeedQuizView.as_view(), name='speed_quiz'),
    path('quiz/submit/', QuizSubmitView.as_view(), name='quiz_submit'),  
]
