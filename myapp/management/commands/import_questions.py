import csv
from django.core.management.base import BaseCommand
from myapp.models import Question

class Command(BaseCommand):
    help = 'CSV 파일에서 상식 문제를 가져와 DB에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='CSV 파일 경로')

    def handle(self, *args, **options):
        path = options['csv_path']
        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                Question.objects.create(
                    genre_id=row['genre_id'],
                    question=row['question'],
                    option1=row['option1'],
                    option2=row['option2'],
                    option3=row['option3'],
                    option4=row['option4'],
                    answer=row['answer'],
                    explanation=row['explanation'],
                )
        self.stdout.write(self.style.SUCCESS(f"{path}에서 문제 데이터를 성공적으로 삽입했습니다."))