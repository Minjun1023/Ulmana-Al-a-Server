#!/usr/bin/env bash

# Django 마이그레이션과 정적 파일 수집 (Render에서 자동 실행)
python manage.py migrate
python manage.py collectstatic --noinput