from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import sqlite3
import os
import chromedriver_autoinstaller
from wordcloud import WordCloud
from konlpy.tag import Okt
from sklearn.feature_extraction.text import TfidfVectorizer
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# OpenAI API 설정
GOOGLE_API_KEY = 'AIzaSyBlEWYCjt1LSc_r1sykPJS8-7rGrEcyLRc'  # 실제 키로 교체하세요
genai.configure(api_key=GOOGLE_API_KEY)
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}
model = genai.GenerativeModel('gemini-pro', generation_config=generation_config)

# 앱 디렉토리 경로
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY,
            stance TEXT,
            paper TEXT,
            title TEXT,
            time TEXT,
            content TEXT,
            link TEXT,
            summary TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(data):
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    for article in data:
        c.execute('''
            INSERT INTO articles (stance, paper, title, time, content, link, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', 
        (article['stance'], article['paper'], article['title'], article['time'], 
         article['content'], article['link'], article.get('summary', '')))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    keyword = request.form['keyword']

    # Chromedriver 자동 설치 및 설정
    chromedriver_autoinstaller.install()
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service()

    driver = webdriver.Chrome(service=service, options=options)

    # 신문사와 성향 설정
    papers = {
        "진보": [("한겨레", "028"), ("경향신문", "032")],
        "중도": [("서울신문", "081"), ("한국일보", "469")],
        "보수": [("조선일보", "023")]
    }

    end_date = datetime.today()
    start_date = end_date - timedelta(days=14)
    all_articles = []
    stance_articles = {"진보": "", "중도": "", "보수": ""}

    # 날짜별 기사 수집
    for single_date in (start_date + timedelta(n) for n in range(14)):
        formatted_date = single_date.strftime("%Y%m%d")

        for stance, paper_list in papers.items():
            for paper_name, oid in paper_list:
                url = f"https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid={oid}&listType=title&date={formatted_date}"
                driver.get(url)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                articles = soup.find_all('a', class_='nclicks(cnt_flashart)')

                for article in articles:
                    title = article.text.strip()
                    link = article['href']

                    if keyword in title:
                        driver.get(link)
                        # 불필요한 대기 시간을 줄이기 위해 명시적 대기 대신 암묵적 대기 사용
                        driver.implicitly_wait(3)
                        try:
                            temp_article = driver.find_element(By.CSS_SELECTOR, '#newsct_article').text
                        except:
                            try:
                                temp_article = driver.find_element(By.CSS_SELECTOR, '._article_content').text
                            except:
                                continue

                        if temp_article.count(keyword) >= 2:
                            try:
                                time_e = driver.find_element(By.CSS_SELECTOR, '.media_end_head_info_datestamp_time').text
                            except:
                                try:
                                    time_e = driver.find_element(By.CSS_SELECTOR, '.NewsEndMain_date__xjtsQ').text
                                except:
                                    time_e = "시간 정보 없음"

                            all_articles.append({
                                'stance': stance,
                                'paper': paper_name,
                                'title': title,
                                'time': time_e,
                                'content': temp_article,
                                'link': link,
                                'summary': '',  # 초기값 설정
                            })
                            stance_articles[stance] += temp_article

    driver.quit()

    if not all_articles:
        return "최근 14일 기준으로 해당 키워드가 포함된 기사가 없습니다."

    # 요약을 병렬로 처리
    def summarize_article(article):
        temp_article = article['content']
        prompt = f"다음 기사를 세 줄로 요약해줘:\n{temp_article}"
        try:
            response = model.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            else:
                return "요약 실패: 응답이 없습니다."
        except Exception as e:
            return f"요약 실패: {str(e)}"

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_article = {executor.submit(summarize_article, article): article for article in all_articles}
        for future in as_completed(future_to_article):
            article = future_to_article[future]
            try:
                summary = future.result()
            except Exception as exc:
                summary = f"요약 실패: {str(exc)}"
            article['summary'] = summary

    save_to_db(all_articles)

    # 워드 클라우드 생성
    okt = Okt()
    font_path = 'NanumGothic.ttf'  # 자신의 시스템에 맞는 경로로 설정
    wordclouds = {}
    for stance, text in stance_articles.items():
        if text:
            nouns = okt.nouns(text)
            nouns_text = " ".join(nouns)

            vectorizer = TfidfVectorizer()
            X = vectorizer.fit_transform([nouns_text])
            tfidf_dict = dict(zip(vectorizer.get_feature_names_out(), X.toarray()[0]))

            wordcloud = WordCloud(width=800, height=400, background_color='white', font_path=font_path).generate_from_frequencies(tfidf_dict)
            wordclouds[stance] = wordcloud
            wordcloud.to_file(os.path.join(APP_ROOT, f"static/wordcloud_{stance}.png"))

    return render_template('results.html', keyword=keyword, articles=all_articles)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
