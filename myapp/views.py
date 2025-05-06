from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken


from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from .models import CustomUser, Question, Genre, QuizResult, QuizSession
from .serializers import (
    UserSerializer,
    LoginSerializer,
    FindIdSerializer,
    ResetPasswordSerializer,
    QuestionSerializer,
    QuizResultSerializer,
    QuizSessionSerializer

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


# 25문제
class Genre25QuestionView(APIView):
    def get(self, request):
        genre_id = request.query_params.get('genre_id')
        if not genre_id:
            return Response({"error": "genre_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        questions = Question.objects.filter(genre__genre_id=genre_id).order_by('?')[:25]
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


# 50문제
class Genre50QuestionView(APIView):
    def get(self, request):
        genre_id = request.query_params.get('genre_id')
        if not genre_id:
            return Response({"error": "genre_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        questions = Question.objects.filter(genre__genre_id=genre_id).order_by('?')[:50]
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


# 스피드퀴즈
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
    
# 퀴즈 제출(퀴즈 결과까지 보여줌)
class QuizSubmitView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        quiz_results = request.data.get('quiz_results')
        genre_id = request.data.get('genre_id')
        quiz_type = request.data.get('quiz_type')
        

        if not all([quiz_results, genre_id, quiz_type]):
            return Response({
                "message": "필수 정보가 누락되었습니다. (quiz_results, genre_id, quiz_type)"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            genre = Genre.objects.get(pk=genre_id)
        except Genre.DoesNotExist:
            return Response({
                "message": f"장르 ID {genre_id}에 해당하는 장르가 존재하지 않습니다."
            }, status=status.HTTP_404_NOT_FOUND)

        total_score = 0
        correct_count = 0
        wrong_count = 0

        # QuizSession 객체 생성 (start_time은 자동 설정됨)
        quiz_session = QuizSession.objects.create(
            user=user,
            genre=genre,
            quiz_type=quiz_type,
            total_questions=len(quiz_results),
            correct_count=0,
            wrong_count=0,
            total_score=0
        )

        # 퀴즈 결과 처리
        for result in quiz_results:
            question_id = result.get('question_id')
            user_answer_raw = result.get('user_answer')

            if user_answer_raw is None:
                return Response({
                    "message": f"문제 ID {question_id}의 사용자 답안이 없습니다."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                question = Question.objects.get(question_id=question_id)

                # 숫자형 인덱스를 보기 텍스트로 변환
                options = {
                    '1': question.option1,
                    '2': question.option2,
                    '3': question.option3,
                    '4': question.option4,
                }
                user_answer = options.get(str(user_answer_raw), "").strip().lower()
                correct_answer = str(question.answer).strip().lower()

                is_correct = user_answer == correct_answer
                score = 1 if is_correct else 0

                if is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1

                # 결과 저장
                QuizResult.objects.create(
                    session=quiz_session,
                    question=question,
                    user_answer=user_answer,
                    correct_answer=question.answer,
                    is_correct=is_correct,
                    score=score
                )

                total_score += score

            except Question.DoesNotExist:
                continue  # 존재하지 않는 질문은 건너뜀

        # 세션 정보 업데이트
        quiz_session.correct_count = correct_count
        quiz_session.wrong_count = wrong_count
        quiz_session.total_score = total_score
        quiz_session.end_time = timezone.now()  # 퀴즈 종료 시간 설정
        quiz_session.save()

        # 사용자 누적 점수 업데이트
        if user.score is None:
            user.score = 0
        user.score += total_score
        user.save()

        return Response({
            "message": "퀴즈 결과가 성공적으로 저장되었습니다.",
            "summary": {
                "총 문항 수": len(quiz_results),
                "정답 수": correct_count,
                "오답 수": wrong_count,
                "획득 점수": total_score,
                "누적 점수": user.score,
            },
        }, status=status.HTTP_201_CREATED)


# 최근 퀴즈 결과
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quiz_sessions(request):
    user = request.user

    quiz_sessions = (
        QuizSession.objects
        .filter(
            user=user,
            genre__isnull=False,
            quiz_type__isnull=False
        )
        # ── 오답노트에서 wrong_count=0인 세션만 제거
        .exclude(quiz_type='wrong_note', wrong_count=0)
        .prefetch_related(
            'quizresult_set__question',
            'quizresult_set__question__genre'
        )
        .select_related('genre')
        .order_by('-created_at')[:20]
    )

    serializer = QuizSessionSerializer(quiz_sessions, many=True)
    return Response(serializer.data)

# 문제 및 해설 상세 조회 뷰
class QuestionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, question_id):
        try:
            # 문제 정보 조회
            question = Question.objects.get(question_id=question_id)

            # 현재 사용자에 대한 QuizResult 조회 (session을 통해 user 연결)
            quiz_result = QuizResult.objects.filter(
                question=question,
                session__user=request.user  # session 테이블을 통해 user 필터링
            ).first()

            # user_answer가 존재할 경우 가져오고, 없으면 None
            user_answer = quiz_result.user_answer if quiz_result else None

            # 해당 퀴즈 결과의 세션 정보(quiz_type 포함) 조회
            quiz_session = quiz_result.session if quiz_result else None
            quiz_type = quiz_session.quiz_type if quiz_session else None

            # 응답 데이터 구성
            response_data = {
                "question_id": question.question_id,
                "question_text": question.question_text,
                "option1": question.option1,
                "option2": question.option2,
                "option3": question.option3,
                "option4": question.option4,
                "user_answer": user_answer,  # 사용자 선택 답
                "answer": question.answer,  # 정답
                "explanation": question.explanation,  # 해설
                "quiz_type": quiz_type,  # 퀴즈 유형
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Question.DoesNotExist:
            return Response({"error": "문제를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

# 오답노트 제출
class WrongNoteSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        quiz_results = request.data.get("quiz_results")
        quiz_type = request.data.get("quiz_type", "wrong_note")

        if not quiz_results:
            return Response({"message": "quiz_results가 필요합니다."}, status=400)

        # 1) 이전 오답노트 세션 모두 삭제 (기타/NULL로 남아 있는 예전 기록 제거)
        QuizSession.objects.filter(user=user, quiz_type=quiz_type).delete()

        total_score = 0.0
        correct_count = 0
        wrong_count = 0
        first_genre = None

        # 2) 채점만 먼저 돌려서 통계 집계 & 첫 문제의 장르 저장
        for item in quiz_results:
            qid = item.get("question_id")
            idx = item.get("user_answer")
            try:
                q = Question.objects.get(question_id=qid)
                if first_genre is None:
                    first_genre = q.genre
                # 보기 텍스트 매핑
                opts = {"1": q.option1, "2": q.option2, "3": q.option3, "4": q.option4}
                ua = opts.get(str(idx), "").strip().lower()
                ca = str(q.answer).strip().lower()
                is_correct = (ua == ca)
                score = 0.5 if is_correct else 0.0

                total_score += score
                correct_count += int(is_correct)
                wrong_count += int(not is_correct)
            except Question.DoesNotExist:
                continue

        # 3) 새 세션 생성 (장르와 quiz_type 모두 채워짐)
        session = QuizSession.objects.create(
            user=user,
            genre=first_genre,
            quiz_type=quiz_type,
            total_questions=len(quiz_results),
            correct_count=correct_count,
            wrong_count=wrong_count,
            total_score=total_score,
            end_time=timezone.now()
        )

        # 4) 개별 문제 기록 저장
        for item in quiz_results:
            qid = item.get("question_id")
            idx = item.get("user_answer")
            try:
                q = Question.objects.get(question_id=qid)
                opts = {"1": q.option1, "2": q.option2, "3": q.option3, "4": q.option4}
                ua = opts.get(str(idx), "").strip().lower()
                ca = str(q.answer)
                is_correct = (ua == ca.strip().lower())
                sc = 0.5 if is_correct else 0.0

                QuizResult.objects.create(
                    session=session,
                    question=q,
                    user_answer=ua,
                    correct_answer=q.answer,
                    is_correct=is_correct,
                    score=sc
                )
            except Question.DoesNotExist:
                continue

        # 5) 유저 누적 점수 갱신 (0.5점 단위)
        if user.score is None:
            user.score = 0.0
        user.score += total_score
        user.save()

        return Response({
            "message": "오답노트 채점 결과 저장 완료",
            "summary": {
                "정답 수": correct_count,
                "오답 수": wrong_count,
                "총 점수": total_score,
                "누적 점수": user.score
            }
        }, status=status.HTTP_201_CREATED)
    
# 랭킹
class RankingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mode = request.query_params.get('mode', 'speed')
        user = request.user

        if mode == 'solve':
            users = CustomUser.objects.order_by('-solve_score')[:100]
            score_field = 'solve_score'
        elif mode == 'total':
            users = CustomUser.objects.order_by('-total_score')[:100]
            score_field = 'total_score'
        else:  # default: speed
            users = CustomUser.objects.order_by('-speed_score')[:100]
            score_field = 'speed_score'

        ranking_list = []
        my_rank = None

        for idx, u in enumerate(users, start=1):
            if u.id == user.id:
                my_rank = idx

            ranking_list.append({
                'rank': idx,
                'nickname': u.username,
                'profile_image': u.profileImage.url if u.profileImage else None,
                'score': getattr(u, score_field),
            })

        if my_rank is None:
            my_rank = CustomUser.objects.filter(**{
                f"{score_field}__gt": getattr(user, score_field)
            }).count() + 1

        my_info = {
            'rank': my_rank,
            'nickname': user.username,
            'profile_image': user.profileImage.url if user.profileImage else None,
            'score': getattr(user, score_field),
        }

        return Response({
            'ranking': ranking_list,
            'my_info': my_info
        })