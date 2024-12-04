# Python 3.9 Slim 이미지를 기반으로 빌드
FROM python:3.9-slim

# Chrome과 필요한 패키지를 설치하기 위한 추가 도구 설치
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    xvfb \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libappindicator3-1 \
    fonts-liberation \
    libasound2 \
    libgbm-dev \
    libgtk-3-0 \
    && apt-get clean

# Chrome 브라우저 설치
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y /tmp/chrome.deb && \
    rm /tmp/chrome.deb

# 작업 디렉토리를 설정
WORKDIR /app

# Python 의존성 파일 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Flask 애플리케이션 파일 복사
COPY . .

# DigitalOcean 기본 실행 포트 설정
ENV PORT 8080
EXPOSE 8080

# WSGI 서버 Gunicorn 설치 및 실행
RUN pip install gunicorn

# Flask 애플리케이션 실행 (gunicorn 사용)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
