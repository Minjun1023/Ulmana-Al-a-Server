from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from .models import CustomUser, Question, Genre, QuizResult
from .serializers import (
    UserSerializer,
    LoginSerializer,
    FindIdSerializer,
    ResetPasswordSerializer,
    QuestionSerializer,
    QuizResultSerializer
)

import random

User = get_user_model()

# ✅ 회원가입
class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'message': 'Registration successful',
            'data': response.data
        })


# ✅ 로그인 (JWT 발급)
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


# ✅ 아이디(이메일) 찾기
class FindIdView(generics.GenericAPIView):
    serializer_class = FindIdSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        return Response({
            'message': f'당신의 이메일은 {user.email}'
        })


# ✅ 비밀번호 재설정
class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "등록되지 않은 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"message": "비밀번호가 성공적으로 변경되었습니다."}, status=200)


# ✅ 사용자 프로필
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


# ✅ JWT 기반 해설 제공
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_random_explanations(request):
    user = request.user
    interests = [user.interest_1, user.interest_2, user.interest_3]
    interests = [i for i in interests if i and i.isdigit()]
    genre_ids = list(map(int, interests))

    questions = Question.objects.filter(genre_id__in=genre_ids)
    explanations = [q.explanation for q in random.sample(list(questions), min(3, len(questions)))]
    return Response({"explanations": explanations})


@csrf_exempt
@require_GET
def get_daily_facts(request):
    email = request.GET.get('email')

    try:
        user = CustomUser.objects.get(email=email)

        interests = [user.interest_1, user.interest_2, user.interest_3]
        valid_genres = [int(i) for i in interests if i and i.isdigit()]

        if not valid_genres:
            return JsonResponse({'daily_facts': []}, status=200)

        selected_genres = random.sample(valid_genres, min(3, len(valid_genres)))

        daily_facts = []
        for genre_id in selected_genres:
            try:
                genre = Genre.objects.get(genre_id=genre_id)
                questions = Question.objects.filter(genre=genre)
                if questions.exists():
                    question = random.choice(questions)
                    daily_facts.append({
                        'genre_name': genre.genre_name,
                        'explanation': question.explanation
                    })
            except Genre.DoesNotExist:
                continue

        # ✅ 매 요청마다 새로운 상식 제공
        return JsonResponse({'daily_facts': daily_facts}, safe=False, status=200)

    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

        
class Genre25QuestionView(APIView):
    def get(self, request):
        genre_id = request.query_params.get('genre_id')
        if not genre_id:
            return Response({"error": "genre_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        questions = Question.objects.filter(genre__genre_id=genre_id).order_by('?')[:25]
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


class Genre50QuestionView(APIView):
    def get(self, request):
        genre_id = request.query_params.get('genre_id')
        if not genre_id:
            return Response({"error": "genre_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        questions = Question.objects.filter(genre__genre_id=genre_id).order_by('?')[:50]
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


class SpeedQuizView(APIView):
    def get(self, request):
        genre_id = request.query_params.get('genre_id')
        if not genre_id:
            return Response({"error": "genre_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        questions = Question.objects.filter(genre__genre_id=genre_id).order_by('?')[:100]
        serializer = QuestionSerializer(questions, many=True)

        return Response({
            "time_options": [60, 180],  # 1분, 3분
            "questions": serializer.data
        })
class QuizSubmitView(generics.GenericAPIView):
    serializer_class = QuizResultSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        quiz_results = request.data.get('quiz_results', [])

        results = []
        total_score = 0

        for result in quiz_results:
            try:
                question_id = result.get('question_id')
                user_answer = result.get('user_answer')

                question = Question.objects.get(question_id=question_id)
                correct_answer = question.answer
                is_correct = user_answer == correct_answer
                score = 1 if is_correct else 0
                total_score += score

                quiz_result = QuizResult.objects.create(
                    user=user,
                    question=question,
                    user_answer=user_answer,
                    correct_answer=correct_answer,
                    is_correct=is_correct,
                    score=score
                )

                results.append({
                    "question_id": question_id,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "score": score
                })

            except Question.DoesNotExist:
                continue

        # 전체 점수 누적
        user.score += total_score
        user.save()

        return Response({
            "message": "퀴즈 결과가 성공적으로 저장되었습니다.",
            "total_score": total_score,
            "results": results
        }, status=status.HTTP_201_CREATED)
