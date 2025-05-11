from django.urls import path
from myapp import views
from myapp.views import (
    RegisterView, LoginView, FindIdView, ResetPasswordView, UserProfileView,
    get_random_explanations, get_daily_facts, Genre25QuestionView, Genre50QuestionView,
    SpeedQuizView, QuizSubmitView, get_quiz_results, get_wrong_answers, genre_score_summary, RankingView,
    UpdateNicknameView,  # ✅ 닉네임 변경 뷰 import 추가
)

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('find-id/', views.FindIdView.as_view(), name='findid'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='resetpassword'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('profile/update-nickname/', UpdateNicknameView.as_view(), name='update-nickname'),  # ✅ 닉네임 변경 URL 추가
    path("profile/update-interests/", UpdateInterestsView.as_view(), name="update-interests"), # ✅ 관심 분야 변경 URL 추가
    path('questions/random_explanations/', get_random_explanations, name='random_explanations'),
    path('daily-facts/', views.get_daily_facts, name='daily-facts'),
    path('questions/genre/25/', Genre25QuestionView.as_view(), name='genre_25_questions'), 
    path('questions/genre/50/', Genre50QuestionView.as_view(), name='genre_50_questions'), 
    path('questions/speed/', SpeedQuizView.as_view(), name='speed_quiz'),
    path('quiz/submit/', QuizSubmitView.as_view(), name='quiz_submit'),  
    path('quiz/result/', get_quiz_results, name='quiz-results'),
    path('quiz/wrong-answers/', get_wrong_answers, name='wrong-answer'),
    path('quiz/score-summary/', genre_score_summary, name='score-summary'),
    path('quiz/ranking/', RankingView.as_view(), name='ranking'),
]
