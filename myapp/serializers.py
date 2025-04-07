from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import CustomUser
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
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            interest_1=validated_data.get('interest_1'),
            interest_2=validated_data.get('interest_2'),
            interest_3=validated_data.get('interest_3'),
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