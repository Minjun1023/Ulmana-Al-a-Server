from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.db import models
from django.utils import timezone
from datetime import timedelta

# 사용자 관리자
class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, interest_1=None, interest_2=None, interest_3=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            interest_1=interest_1,
            interest_2=interest_2,
            interest_3=interest_3,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)

# 사용자 모델
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=20, unique=True)
    score = models.FloatField(default=0.0) 
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    speed_score_1min = models.IntegerField(default=0)
    speed_score_3min = models.IntegerField(default=0)
    solve_score = models.IntegerField(default=0)

    interest_1 = models.CharField(max_length=100, blank=True, null=True)
    interest_2 = models.CharField(max_length=100, blank=True, null=True)
    interest_3 = models.CharField(max_length=100, blank=True, null=True)

    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    # 점수 업데이트 메서드
    def update_speed_score(self, correct_answers, time_limit):
        if time_limit == "1min":
            self.speed_score_1min = max(self.speed_score_1min, correct_answers)
        elif time_limit == "3min":
            self.speed_score_3min = max(self.speed_score_3min, correct_answers)
        self.save()
    

# 장르 모델
class Genre(models.Model):
    genre_id = models.AutoField(primary_key=True)
    genre_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.genre_name
    
# 문제/상식 모델
class Question(models.Model):
    question_id = models.AutoField(primary_key=True)
    genre = models.ForeignKey(Genre,to_field='genre_id',on_delete=models.CASCADE,related_name="questions",null=True,)  # 또는 default=1 등으로 설정
    question_text = models.TextField()
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)
    explanation = models.TextField()

    def __str__(self):
        return f"[{self.genre.genre_name}] {self.question_text[:30]}..."

# 퀴즈 세션 모델
class QuizSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='quiz_sessions')
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True)
    quiz_type = models.CharField(max_length=20)  # "25문제", "50문제", "스피드퀴즈" 등 퀴즈 유형 추가
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    total_questions = models.IntegerField()
    correct_count = models.IntegerField()
    wrong_count = models.IntegerField()
    total_score = models.IntegerField()
    start_time = models.DateTimeField(auto_now_add=True)  # auto_now_add로 자동 설정됨
    end_time = models.DateTimeField(null=True, blank=True)  # end_time 필드 추가

    def __str__(self):
        return f"{self.user.username} - {self.genre.genre_name} - {self.quiz_type} - {self.created_at.date()}"
# 퀴즈 결과 모델
class QuizResult(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, null=True)
    question = models.ForeignKey('myapp.Question', on_delete=models.CASCADE)
    user_answer = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(db_index=True)
    score = models.IntegerField()
    submission_time = models.DateTimeField(auto_now_add=True)  # 답안 제출 시간

    def __str__(self):
        return f"{self.session.user.username} - Q{self.question.question_id} - {'O' if self.is_correct else 'X'}"

# 정답률에 따른 문제 추천 모델
class QuestionStat(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='stats')
    total_attempts = models.PositiveIntegerField(default=0)
    correct_attempts = models.PositiveIntegerField(default=0)

    @property
    def accuracy_rate(self):
        if self.total_attempts == 0:
            return 0.0
        return round((self.correct_attempts / self.total_attempts) * 100, 1)