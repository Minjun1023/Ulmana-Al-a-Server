from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from myapp import views
from myapp.views import (
    RegisterView, LoginView, FindIdView, ResetPasswordView, UserProfileView, UploadProfileImageView, UpdateNicknameView, UpdateInterestsView, get_quiz_results,
    get_random_explanations, get_daily_facts, Genre25QuestionView, Genre50QuestionView,
    SpeedQuizView, QuizSubmitView, get_quiz_sessions, QuestionDetailView, WrongNoteSubmitView, RankingView
)

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'), # 회원가입
    path('login/', views.LoginView.as_view(), name='login'), # 로그인
    path('find-id/', views.FindIdView.as_view(), name='findid'), # 아이디 찾기
    path('reset-password/', views.ResetPasswordView.as_view(), name='resetpassword'), # 비밀번호 찾기
    path('profile/', views.UserProfileView.as_view(), name='user-profile'), # 유저 프로필
    path('user/upload-profile-image/', UploadProfileImageView.as_view(), name='upload-profile-image'), # 이미지 파일 업로드 API
    path('profile/update-nickname/', UpdateNicknameView.as_view(), name='update-nickname'),# ✅ 닉네임 변경 URL 추가
    path("profile/update-interests/", UpdateInterestsView.as_view(), name="update-interests"), # ✅ 관심 분야 변경 URL 추가
    path('quiz-results/', get_quiz_results, name='quiz_result'), # 마이페이지 최근 퀴즈 내역
    path('questions/random_explanations/', get_random_explanations, name='random_explanations'), # 랜덤 뽑기
    path('daily-facts/', views.get_daily_facts, name='daily-facts'), # 데일리 상식
    path('questions/genre/25/', Genre25QuestionView.as_view(), name='genre_25_questions'), # 25문제
    path('questions/genre/50/', Genre50QuestionView.as_view(), name='genre_50_questions'), # 50문제
    path('questions/speed/', SpeedQuizView.as_view(), name='speed_quiz'), # 스피드 퀴즈
    path('quiz/submit/', QuizSubmitView.as_view(), name='quiz_submit'), # 퀴즈 제출(퀴즈 결과)
    path('quiz/sessions/', get_quiz_sessions, name='quiz_session'), # 최근 퀴즈 결과
    path('questions/<int:question_id>/details/', QuestionDetailView.as_view(), name='question-detail'), # 문제 및 해설
    path("wrong-note-submit/", WrongNoteSubmitView.as_view(), name="wrong-note-submit"), # 오답노트 퀴즈 제출
    path('quiz/ranking/', RankingView.as_view(), name='ranking'), # 랭킹    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
