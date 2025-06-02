import json
from django.core.management.base import BaseCommand
from myapp.models import Question, Genre

class Command(BaseCommand):
    help = 'JSON 파일에서 상식 문제를 가져와 DB에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='JSON 파일 경로')

    def handle(self, *args, **options):
        path = options['json_path']
        inserted_count = 0
        skipped_count = 0

        with open(path, encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            for row in data:
                try:
                    genre = Genre.objects.get(genre_id=row['genre_id'])
                except Genre.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[SKIP] genre_id {row['genre_id']}를 찾을 수 없습니다. 문제: '{row['question_text'][:30]}...'"
                        )
                    )
                    skipped_count += 1
                    continue

                # 새 질문 삽입
                Question.objects.create(
                    genre=genre,
                    question_text=row['question_text'],
                    option1=row['option1'],
                    option2=row['option2'],
                    option3=row['option3'],
                    option4=row['option4'],
                    answer=row['answer'],
                    explanation=row['explanation'],
                )
                inserted_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"{inserted_count}개 문제를 성공적으로 삽입했습니다. (건너뛴 항목: {skipped_count}개)"))