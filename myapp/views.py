from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import CustomUser
from .serializers import UserSerializer
from .serializers import LoginSerializer
from .serializers import FindIdSerializer
from .serializers import ResetPasswordSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from .models import Question  # ← 문제 모델도 import 필요
import random

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'message': 'Registration successful',
            'data': response.data
        })

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

class FindIdView(generics.GenericAPIView):
    serializer_class = FindIdSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        return Response({
            'message': f'당신의 이메일은 {user.email}'
        })


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)  # User는 get_user_model()을 통해 CustomUser 모델로 가져옵니다.
        except User.DoesNotExist:
            return Response({"error": "등록되지 않은 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({"message": "비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_random_explanations(request):
    user = request.user

    # 유저 관심 장르 ID 가져오기
    interests = [user.interest1, user.interest2, user.interest3]
    interests = [i for i in interests if i is not None]

    # 해당 장르 문제 중 랜덤하게 3개 선택
    questions = Question.objects.filter(genre_id__in=interests)
    explanations = [q.explanation for q in random.sample(list(questions), min(3, len(questions)))]

    return Response({"explanations": explanations})


@csrf_exempt
def get_daily_facts(request):
    email = request.GET.get('email')  # 안드로이드에서 보낼 예정

    try:
        user = CustomUser.objects.get(email=email)
        genre_ids = []

        for interest in [user.interest1, user.interest2, user.interest3]:
            if interest:
                genre_ids.append(int(interest))

        questions = Question.objects.filter(genre_id__in=genre_ids)
        explanations = list(questions.values_list('explanation', flat=True))
        random.shuffle(explanations)

        return JsonResponse({'daily_facts': explanations[:3]}, status=200)

    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
