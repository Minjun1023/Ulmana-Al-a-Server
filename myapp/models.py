from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)

# 유저 모델
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # 이메일 필드 (기본키 역할)
    username = models.CharField(max_length=20, unique=True)  # 닉네임 (중복 방지)
    score = models.IntegerField(default=0)  # 점수 (기본값 0)
    
    interest_1 = models.CharField(max_length=100, blank=True, null=True)
    interest_2 = models.CharField(max_length=100, blank=True, null=True)
    interest_3 = models.CharField(max_length=100, blank=True, null=True)

    # 그룹 및 권한 설정 (Django 기본 User와 충돌 방지)
    groups = models.ManyToManyField(
        Group,
        related_name="customuser_groups",
        blank=True,
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_permissions",
        blank=True,
    )

    objects = CustomUserManager()

    # 로그인 시 email을 사용하도록 설정
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
# 퀴즈 장르 모델
class Genre(models.Model):
    genre_id = models.AutoField(primary_key=True)
    genre_name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.genre_name

# 문제 모델
class Question(models.Model):
    question_id = models.AutoField(primary_key=True)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)
    explanation = models.TextField()

    def __str__(self):
        return f"[{self.genre.genre_name}] {self.question_text[:30]}..."

# 퀴즈 결과 모델
class QuizResult(models.Model):
    answer_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="quiz_results")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="quiz_results")
    user_answer = models.TextField()
    correct_answer = models.TextField()
    is_correct = models.BooleanField()
    submission_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question.question_text[:20]}"

# 사용자 선호 장르 모델
class UserPreference(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="preferences")
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name="user_preferences")

    class Meta:
        unique_together = ("user", "genre")

    def __str__(self):
        return f"{self.user.username} - {self.genre.genre_name}"