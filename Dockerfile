# Python 기반 이미지 선택
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Flask 애플리케이션 파일 복사
COPY . .

# Flask 실행 포트 설정 (Fly.io에서는 기본 포트 8080 사용)
ENV PORT 8080
EXPOSE 8080

# Flask 실행
CMD ["python", "app.py"]
3
