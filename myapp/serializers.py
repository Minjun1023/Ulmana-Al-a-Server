from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import CustomUser, Genre, Question, QuizResult, QuizSession, QuestionStat
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'interest_1', 'interest_2', 'interest_3']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # genre_name → genre_id(str) 변환 함수
        def get_genre_id_by_name(name):
            try:
                genre = Genre.objects.get(genre_name=name)
                return str(genre.genre_id)  # DB에는 문자열로 저장됨
            except Genre.DoesNotExist:
                return None

        # 변환 적용
        interest_1 = get_genre_id_by_name(validated_data.get('interest_1'))
        interest_2 = get_genre_id_by_name(validated_data.get('interest_2'))
        interest_3 = get_genre_id_by_name(validated_data.get('interest_3'))

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            interest_1=interest_1,
            interest_2=interest_2,
            interest_3=interest_3,
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()  

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if user is None:
            raise serializers.ValidationError('Invalid credentials')
        return user

class FindIdSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate(self, data):
        try:
            user = CustomUser.objects.get(username=data['username'])
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError('User not found')
        return user

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        email = data.get("email")
        new_password = data.get("new_password")

        try:
            user = User.objects.get(email=email)  # 이메일로 유저 찾기
        except User.DoesNotExist:
            raise serializers.ValidationError("이메일을 확인해주세요.")

        # 새로운 비밀번호가 기존 비밀번호와 동일한지 확인
        if check_password(new_password, user.password):
            raise serializers.ValidationError({"new_password": "새로운 비밀번호는 기존 비밀번호와 다르게 설정해야 합니다."})

        return data

    def save(self):
        email = self.validated_data.get("email")
        new_password = self.validated_data.get("new_password")

        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
class QuestionSerializer(serializers.ModelSerializer):
    genre_name = serializers.CharField(source='genre.genre_name', read_only=True)
    accuracy = serializers.SerializerMethodField()
    correct_answer = serializers.CharField(source='answer', read_only=True)

    class Meta:
        model = Question
        fields = [
            'question_id', 'question_text', 'option1', 'option2', 'option3', 'option4',
            'answer', 'genre_name', 'accuracy', 'correct_answer', 'explanation'
        ]

    def get_accuracy(self, obj):
        return getattr(obj, 'accuracy_rate', None)

class QuizResultSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    explanation = serializers.CharField(source='question.explanation', read_only=True)
    genre_name = serializers.CharField(source='question.genre.genre_name', read_only=True)
    user_answer = serializers.CharField(read_only=True)
    class Meta:
        model = QuizResult
        fields = [
            'question', 'question_text', 'user_answer', 'correct_answer',
            'is_correct', 'score', 'submission_time', 'explanation', 'genre_name', 
        ]

    def get_correct_count(self, obj):
        # 해당 퀴즈 세션에서 맞춘 문제 수를 반환
        correct_answers = QuizResult.objects.filter(session=obj.session, is_correct=True).count()
        return correct_answers
    
    def create(self, validated_data):
        user = validated_data['user']
        question = validated_data['question']
        user_answer = validated_data['user_answer']
        correct_answer = question.answer
        is_correct = user_answer == correct_answer
        score = 4 if is_correct else 0

        # 퀴즈 결과 생성
        quiz_result = QuizResult.objects.create(
            user=user,
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            score=score
        )

        # 누적 점수 반영
        if user.score is None:
            user.score = 0
        user.score += score
        user.save()

        return quiz_result


class QuizSummarySerializer(serializers.Serializer):
    score = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    wrong_count = serializers.IntegerField()

class QuizSessionSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(
        source='created_at',
        format='%Y-%m-%d %H:%M',
        read_only=True
    )
    genre = serializers.CharField(
        source='genre.genre_name',
        read_only=True
    )
    quiz_type = serializers.CharField(read_only=True)
    totalQuestions = serializers.IntegerField(
        source='total_questions',
        read_only=True
    )
    correctAnswers = serializers.IntegerField(
        source='correct_count',
        read_only=True
    )
    wrongAnswers = serializers.IntegerField(
        source='wrong_count',
        read_only=True
    )
    totalScore = serializers.FloatField(
        source='total_score',
        read_only=True
    )
    quizResults = QuizResultSerializer(
        many=True,
        source='quizresult_set'
    )

    class Meta:
        model = QuizSession
        fields = [
            'id',
            'date',
            'genre',
            'quiz_type',
            'totalQuestions',
            'correctAnswers',
            'wrongAnswers',
            'totalScore',
            'quizResults',
        ]
class QuestionStatSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    option1 = serializers.CharField(source='question.option1', read_only=True)
    option2 = serializers.CharField(source='question.option2', read_only=True)
    option3 = serializers.CharField(source='question.option3', read_only=True)
    option4 = serializers.CharField(source='question.option4', read_only=True)
    explanation = serializers.CharField(source='question.explanation', read_only=True)
    genre_name = serializers.CharField(source='question.genre.genre_name', read_only=True)
    correct_answer = serializers.CharField(source='question.answer', read_only=True)
    accuracy = serializers.SerializerMethodField()

    class Meta:
        model = QuestionStat
        fields = [
            'question_text', 'option1', 'option2', 'option3', 'option4',
            'correct_answer', 'explanation', 'genre_name', 'accuracy'
        ]

    def get_accuracy(self, obj):
        if obj.total_attempts == 0:
            return None
        return round((obj.correct_attempts / obj.total_attempts) * 100, 1)