# Python 3.9 Slim 이미지를 기반으로 빌드
FROM python:3.9-slim

# 작업 디렉토리를 설정
WORKDIR /app

# Python 의존성 파일 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Flask 애플리케이션 파일 복사
COPY . .

# Fly.io 기본 실행 포트 설정
ENV PORT=8080
EXPOSE 8080

# Flask 애플리케이션 실행
CMD ["python", "app.py"]
