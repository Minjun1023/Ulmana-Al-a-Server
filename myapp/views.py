from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from django.db.models.functions import NullIf
from django.db.models import F, FloatField, ExpressionWrapper, Case, Count, Sum, When, IntegerField, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from .models import CustomUser, Question, Genre, QuizResult, QuizSession, QuestionStat
from .serializers import (
    UserSerializer,
    LoginSerializer,
    FindIdSerializer,
    ResetPasswordSerializer,
    QuestionSerializer,
    QuizResultSerializer,
    QuizSessionSerializer,
    QuestionStatSerializer

)

# keep-alive 명시
def index(request):
    response = HttpResponse("Hello from Django!")
    response['Connection'] = 'keep-alive'
    return response

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

# ✅ 로그인 (수정된 LoginView)
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        refresh = RefreshToken.for_user(user)

        interests = []
        if user.interest_1:
            interests.append(user.interest_1)
        if user.interest_2:
            interests.append(user.interest_2)
        if user.interest_3:
            interests.append(user.interest_3)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'email': user.email,
            'username': user.username,
            'interests': interests,
        }, status=status.HTTP_200_OK)


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
# ✅ 닉네임 변경
class UpdateNicknameView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        new_nickname = request.data.get("username")

        if not new_nickname:
            return Response({"error": "닉네임을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.username = new_nickname
        user.save()

        return Response({"message": "닉네임이 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)

# ✅ 관심 분야 변경
class UpdateInterestsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user

        # 요청에서 새로운 관심 분야 받아오기
        interest_1 = request.data.get("interest_1")
        interest_2 = request.data.get("interest_2")
        interest_3 = request.data.get("interest_3")

        # 최소한 하나라도 값이 있어야 변경 가능
        if not any([interest_1, interest_2, interest_3]):
            return Response(
                {"error": "최소 하나 이상의 관심 분야를 선택해야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 저장 (None도 허용됨)
        user.interest_1 = interest_1
        user.interest_2 = interest_2
        user.interest_3 = interest_3
        user.save()

        return Response(
            {"message": "관심 분야가 성공적으로 변경되었습니다."},
            status=status.HTTP_200_OK
        )

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
                score = 4 if is_correct else 0

                if is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1

                # 결과 저장 - 보기 선택한 경우에만 QuestionStat 업데이트
                QuizResult.objects.create(
                    session=quiz_session,
                    question=question,
                    user_answer=user_answer,
                    correct_answer=question.answer,
                    is_correct=is_correct,
                    score=score
                )

                # 오직 보기 선택한 경우만 QuestionStat 반영
                if user_answer and user_answer.strip():
                    question_stat, created = QuestionStat.objects.get_or_create(question=question)
                    question_stat.total_attempts += 1
                    if is_correct:
                        question_stat.correct_attempts += 1
                    question_stat.save()

                total_score += score

            except Question.DoesNotExist:
                continue  # 존재하지 않는 질문은 건너뜀

        # 세션 정보 업데이트
        quiz_session.correct_count = correct_count
        quiz_session.wrong_count = wrong_count
        quiz_session.total_score = total_score
        quiz_session.end_time = timezone.now()  # 퀴즈 종료 시간 설정
        quiz_session.save()

        if user.score is None:
            user.score = 0
        user.score += total_score

        if quiz_type in ['test25', 'test50']:
            user.solve_score = max(user.solve_score or 0, total_score)

        if quiz_type == 'speed':
            selected_time = str(request.data.get('selected_time'))

            if selected_time in ["1min", "1", "60"]:  # 1분 스피드 허용
                user.speed_score_1min = max(user.speed_score_1min or 0, total_score)
            elif selected_time in ["3min", "3", "180"]:  # 3분 스피드 허용
                user.speed_score_3min = max(user.speed_score_3min or 0, total_score)
                
        user.save()

        return Response({
            "message": "퀴즈 결과가 성공적으로 저장되었습니다.",
            "summary": {
                "총 문항 수": len(quiz_results),
                "정답 수": correct_count,
                "오답 수": wrong_count,
                "획득 점수": total_score
            },
        }, status=status.HTTP_201_CREATED)
    
# 프로필 이미지 업로드
class UploadProfileImageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        profile_image = request.FILES.get('profile_image')
        if not profile_image:
            return Response({"error": "이미지 파일이 필요합니다."}, status=400)

        user.profile_image = profile_image
        user.save()

        # 절대 URL로 변환
        absolute_url = request.build_absolute_uri(user.profile_image.url)
        return Response({
            "message": "프로필 이미지가 성공적으로 업로드되었습니다.",
            "profile_image_url": absolute_url
        }, status=200)

# 프로필 이미지 초기화
class ResetProfileImageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.profile_image.delete(save=False)  # 서버에서 실제 파일 삭제
        user.profile_image = None
        user.save()
        return Response({
            "message": "프로필 이미지가 기본 이미지로 초기화되었습니다."
        }, status=200)
    
# 마이페이지 최근 퀴즈 내역
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quiz_results(request):
    user = request.user
    quiz_results = QuizResult.objects.filter(session__user=user).order_by('-submission_time')[:10]

    serializer = QuizResultSerializer(quiz_results, many=True)
    return Response(serializer.data)

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
        origin_session_id = request.data.get("origin_session_id")
        total_questions = request.data.get("total_questions") or len(quiz_results)

        if not quiz_results:
            return Response({"message": "quiz_results가 필요합니다."}, status=400)

        if origin_session_id:
            QuizSession.objects.filter(id=origin_session_id, user=user).delete()
        else:
            # 기존 오답노트 세션 전부 제거 (기존 로직 유지)
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
                score = 1 if is_correct else 0.0

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
            total_questions=total_questions,
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
                sc = 1 if is_correct else 0.0

                QuizResult.objects.create(
                    session=session,
                    question=q,
                    user_answer=ua,
                    correct_answer=q.answer,
                    is_correct=is_correct,
                    score=sc
                )

                question_stat, created = QuestionStat.objects.get_or_create(question=q)
                question_stat.total_attempts += 1
                if is_correct:
                    question_stat.correct_attempts += 1
                question_stat.save()
                
            except Question.DoesNotExist:
                continue

        # 5) 유저 누적 점수 갱신 (0.2점 단위, 반올림 적용)
        if user.score is None:
            user.score = 0.0

        user.score = round(user.score + total_score, 1)  # 🔥 부동소수점 정리
        user.save()

        return Response({
            "message": "오답노트 채점 결과 저장 완료",
            "summary": {
                "정답 수": correct_count,
                "오답 수": wrong_count,
                "총 점수": round(total_score,1)
            }
        }, status=status.HTTP_201_CREATED)
    
# 랭킹
class RankingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mode = request.query_params.get('mode', 'speed_1min')  # 기본값은 1분

        print("💡 현재 mode:", mode)  # 디버깅
        cache_key = f'ranking_{mode}'

        # 캐시 사용 (문제 확인 후 주석 풀기)
        # cached_data = cache.get(cache_key)
        # if cached_data:
        #     return Response(cached_data)

        user = request.user
        ranking_data = {
            'top_rankings': [],
            'my_ranking': {}
        }

        # 점수 필드 매핑
        if mode == 'speed_1min':
            score_field = 'speed_score_1min'
        elif mode == 'speed_3min':
            score_field = 'speed_score_3min'
        elif mode == 'solve':
            score_field = 'solve_score'
        elif mode == 'total':
            score_field = 'score'
        else:
            return Response({'error': '유효하지 않은 mode입니다. (speed_1min, speed_3min, solve, total 중 선택)'}, status=400)

        # 점수 안전 추출 함수
        def get_user_score(u, field):
            return {
                'speed_score_1min': u.speed_score_1min,
                'speed_score_3min': u.speed_score_3min,
                'solve_score': u.solve_score,
                'score': u.score,
            }.get(field, 0)

        users = CustomUser.objects.order_by(F(score_field).desc(nulls_last=True))[:100]

        for rank, user_obj in enumerate(users, start=1):
            score = get_user_score(user_obj, score_field)
            ranking_data['top_rankings'].append({
                'rank': rank,
                'nickname': user_obj.username,
                'profile_image': user_obj.profile_image.url if user_obj.profile_image else None,
                'score': score
            })

            if user_obj.id == user.id:
                ranking_data['my_ranking'] = ranking_data['top_rankings'][-1]

        # 100위 밖 유저
        if not ranking_data['my_ranking']:
            my_score = get_user_score(user, score_field)
            higher_count = CustomUser.objects.only(score_field).filter(
                **{f"{score_field}__gt": my_score}
            ).count()

            ranking_data['my_ranking'] = {
                'rank': higher_count + 1,
                'nickname': user.username,
                'profile_image': user.profile_image.url if user.profile_image else None,
                'score': my_score
            }

        # 캐싱 적용 (필요 시 다시 활성화)
        # cache.set(cache_key, ranking_data, 300)
        return Response(ranking_data)
    
# 정답률에 따른 문제 추천

class DailyRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 관심 장르 추출
        raw_ids = [user.interest_1, user.interest_2, user.interest_3]
        try:
            interest_ids = [int(i) for i in raw_ids if i]
        except ValueError:
            interest_ids = []

        # ✅ 보기 선택된 문제만 필터링
        user_results = QuizResult.objects.filter(
            Q(user_answer__isnull=False) & ~Q(user_answer=""),
            # session__user=user,
            session__genre__genre_id__in=interest_ids
        ).values('question').annotate(
            total=Count('id'),
            correct=Sum(Case(
                When(is_correct=True, then=1),
                default=0,
                output_field=IntegerField()
            )),
            accuracy=ExpressionWrapper(
                F('correct') * 100.0 / F('total'),
                output_field=FloatField()
            )
        ).filter(total__gt=0).order_by('accuracy')[:10]

        question_ids = [r['question'] for r in user_results]
        accuracy_dict = {r['question']: r['accuracy'] for r in user_results}

        questions = []
        for qid in question_ids:
            try:
                q = Question.objects.get(pk=qid)
                q.accuracy_rate = accuracy_dict.get(qid)
                questions.append(q)
            except Question.DoesNotExist:
                continue

        # ✅ 아무 문제도 없으면 빈 리스트 반환
        if not questions:
            return Response([])

        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)
