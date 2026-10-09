# 🩺 혈당 가이드 (HealthCare Management System)

음식 사진을 찍거나 업로드하면 AI(Google Gemini)가 영양소(칼로리, 당류, 탄수화물)를 분석하고 맞춤형 식단 조언을 제공하며, Supabase(PostgreSQL) 데이터베이스와 연동하여 캘린더 및 대시보드로 관리할 수 있는 Streamlit 기반 헬스케어 웹 애플리케이션입니다.

---

## 🚀 빠른 시작 가이드

### 1. 필수 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 2. 시크릿(Secret) 설정
본 프로젝트는 보안을 위해 API 키 및 데이터베이스 정보를 `st.secrets`를 통해 관리합니다.  
`.streamlit/secrets.toml.example` 파일을 복사하여 `.streamlit/secrets.toml` 파일을 생성한 후 실제 키 값을 입력해 주세요.

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

#### `.streamlit/secrets.toml` 설정 예시:
```toml
# Google Gemini API 설정 (선택 사항: https://aistudio.google.com/)
GOOGLE_API_KEY = "AIzaSy..."

# Supabase 접속 정보 (https://supabase.com/)
[supabase]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

### 3. 애플리케이션 실행
```bash
streamlit run main.py
```

---

## 📌 주요 기능
1. **사용자 맞춤형 프로필**: 이름, 나이, 성별, 일일 목표 당 섭취량(g) 설정
2. **AI 음식 영양 분석**:
   - 카메라 즉석 촬영 (`st.camera_input`) 또는 갤러리 업로드 (`st.file_uploader`)
   - Gemini 2.5 Flash를 통한 추정 당류, 탄수화물, 칼로리 분석 및 임상 조언 제공
3. **Supabase 연동 및 영속화**: 분석 결과 원클릭 Supabase(`diet_records` 테이블) 저장
4. **건강 리포트 대시보드**: 최근 7일 식단 기록, 누적 칼로리/탄수화물/당류 수치 및 가로 막대 차트
5. **캘린더 관리**: 날짜별 식단 달력 시각화 및 클릭 시 상세 분석 리포트 확인
