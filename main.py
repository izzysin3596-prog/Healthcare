import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
from PIL import Image
from datetime import datetime, timedelta
from streamlit_calendar import calendar
from supabase import create_client, Client

# Streamlit 페이지 기본 설정
st.set_page_config(page_title="혈당 가이드", page_icon="🩺", layout="wide")

# Supabase 클라이언트 초기화 (@st.cache_resource)
@st.cache_resource
def init_supabase() -> Client:
    try:
        supabase_url = st.secrets["supabase"]["SUPABASE_URL"]
        supabase_key = st.secrets["supabase"]["SUPABASE_PUBLISHABLE_KEY"]
        return create_client(supabase_url, supabase_key)
    except KeyError as e:
        st.error(f"Supabase 설정 누락: .streamlit/secrets.toml 파일의 [supabase] 섹션을 확인해주세요. ({e})")
        st.stop()
    except Exception as e:
        st.error(f"Supabase 클라이언트 초기화 실패: {e}")
        st.stop()

supabase = init_supabase()

# Supabase 데이터베이스 연동 함수
def save_diet_record(meal_name: str, calories: float, carbs: float, sugar: float, ai_feedback: str):
    """Supabase diet_records 테이블에 식단 기록을 저장합니다."""
    data = {
        "meal_name": meal_name,
        "calories": calories,
        "carbs": carbs,
        "sugar": sugar,
        "ai_feedback": ai_feedback
    }
    return supabase.table("diet_records").insert(data).execute()

def fetch_diet_records():
    """Supabase diet_records 테이블에서 데이터를 created_at 기준 내림차순으로 조회합니다."""
    try:
        response = supabase.table("diet_records").select("*").order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        st.error(f"식단 기록 조회 실패: {e}")
        return []

# Google Gemini API 설정
if "GOOGLE_API_KEY" in st.secrets and st.secrets["GOOGLE_API_KEY"]:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

st.title("🩺 혈당 가이드")
st.markdown("음식 사진을 찍거나 올려주세요. AI가 영양소를 분석해드립니다.")

# 사이드 바 : 사용자 프로필 작성
with st.sidebar:
    st.header("사용자 프로필")
    st.write("개인 정보를 입력하면 맞춤형 분석을 제공합니다.")

    # 정보 입력
    user_name = st.text_input("이름", value="홍길동")
    user_age = st.number_input("나이", min_value=1, max_value=120, value=20)
    user_gender = st.selectbox("성별", ["남성", "여성"])

    st.header("목표 설정")
    daily_goal = st.number_input("하루 목표 당 섭취량(g)", min_value=0, value=25)

# 탭 메뉴 만들기
tab1, tab2, tab3, tab4 = st.tabs(["대시보드", "혈당 관리", "카메라로 촬영", "갤러리에서 업로드"])

# [탭 1] 대시보드 (나의 건강 리포트)
with tab1:
    st.subheader("📊 나의 주간 건강 리포트")

    try:
        records = fetch_diet_records()

        if records:
            today = datetime.now()
            week_ago = today - timedelta(days=7)

            weekly_data = []
            for item in records:
                created_at_raw = item.get("created_at")
                if created_at_raw:
                    try:
                        record_dt = pd.to_datetime(created_at_raw).to_pydatetime()
                        if record_dt.tzinfo is not None:
                            record_dt = record_dt.replace(tzinfo=None)
                    except Exception:
                        record_dt = today
                else:
                    record_dt = today

                if record_dt >= week_ago:
                    weekly_data.append({
                        "식단명": item.get("meal_name", "미상"),
                        "칼로리(kcal)": float(item.get("calories") or 0),
                        "탄수화물(g)": float(item.get("carbs") or 0),
                        "당류(g)": float(item.get("sugar") or 0),
                        "기록일시": record_dt.strftime("%Y-%m-%d %H:%M")
                    })

            if weekly_data:
                df = pd.DataFrame(weekly_data)
                st.write(f"최근 7일간 총 **{len(weekly_data)}개**의 식단 기록이 있습니다.")

                # 통계 지표 카드
                col1, col2, col3 = st.columns(3)
                total_cal = df["칼로리(kcal)"].sum()
                total_carbs = df["탄수화물(g)"].sum()
                total_sugar = df["당류(g)"].sum()

                col1.metric("누적 칼로리", f"{total_cal:,.1f} kcal")
                col2.metric("누적 탄수화물", f"{total_carbs:,.1f} g")
                col3.metric("누적 당류", f"{total_sugar:,.1f} g", delta=f"목표 대비 {total_sugar - float(daily_goal):+.1f}g" if daily_goal else None)

                st.markdown("---")
                st.write("#### 🥗 식단별 칼로리 현황")
                st.bar_chart(df.set_index("식단명")["칼로리(kcal)"], horizontal=True)

                st.write("#### 📈 식단별 탄수화물 & 당류 섭취 현황")
                st.bar_chart(df.set_index("식단명")[["탄수화물(g)", "당류(g)"]])

                with st.expander("최근 7일 상세 기록 목록 보기"):
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("최근 7일간 기록된 식단이 없습니다.")
                if records:
                    with st.expander("전체 식단 기록 보기"):
                        all_df = pd.DataFrame([{
                            "식단명": r.get("meal_name", "미상"),
                            "칼로리(kcal)": float(r.get("calories") or 0),
                            "탄수화물(g)": float(r.get("carbs") or 0),
                            "당류(g)": float(r.get("sugar") or 0),
                            "기록일시": str(r.get("created_at", ""))[:19]
                        } for r in records])
                        st.dataframe(all_df, use_container_width=True)
        else:
            st.info("아직 기록된 식단이 없어요. 식단 기록을 시작해보세요.")
    except Exception as e:
        st.error(f"데이터를 불러오지 못했습니다: {e}")

# [탭 2] 혈당 관리 (캘린더 뷰)
with tab2:
    st.subheader("📅 식단 및 혈당 관리 캘린더")

    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek",
        },
        "initialView": "dayGridMonth",
        "aspectRatio": 1.5,
        "height": "auto",
        "dayMaxEvents": True,
    }

    events = []
    raw_data = fetch_diet_records()

    for item in raw_data:
        try:
            meal_name = item.get("meal_name", "식단")
            cal = item.get("calories", 0)
            carbs = item.get("carbs", 0)
            sugar = item.get("sugar", 0)
            analysis_content = item.get("ai_feedback", "")
            start_date_raw = item.get("created_at")

            if start_date_raw:
                start_date = str(start_date_raw)[:10]
                events.append({
                    "title": f"{meal_name} ({cal}kcal)",
                    "start": start_date,
                    "end": start_date,
                    "extendedProps": {
                        "meal_name": meal_name,
                        "calories": cal,
                        "carbs": carbs,
                        "sugar": sugar,
                        "content": analysis_content
                    }
                })
        except Exception:
            continue

    state = calendar(events=events, options=calendar_options)

    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = False

    if state.get("eventClick"):
        clicked_event = state["eventClick"]["event"]
        st.session_state.show_detail = True
        st.session_state.current_event = clicked_event.get("extendedProps", {})
        st.session_state.current_title = clicked_event.get("title", "")

    if st.session_state.show_detail and "current_event" in st.session_state:
        current = st.session_state.current_event
        st.divider()
        st.write(f"### 📋 상세 분석 리포트: {current.get('meal_name', st.session_state.get('current_title', ''))}")

        m1, m2, m3 = st.columns(3)
        m1.metric("칼로리", f"{current.get('calories', 0)} kcal")
        m2.metric("탄수화물", f"{current.get('carbs', 0)} g")
        m3.metric("당류", f"{current.get('sugar', 0)} g")

        st.markdown("#### 🤖 AI 맞춤 조언")
        st.info(current.get("content", "분석 내용이 없습니다."))

# [탭 3] 카메라 촬영 기능 & [탭 4] 갤러리 업로드 기능
img_file = None

with tab3:
    camera_img = st.camera_input("음식을 촬영해주세요")
    if camera_img:
        img_file = camera_img

with tab4:
    upload_img = st.file_uploader("이미지 파일을 업로드 하세요.", type=['png', 'jpg', 'jpeg'])
    if upload_img:
        img_file = upload_img

def extract_and_parse_json(text: str) -> dict:
    """정규식을 활용하여 AI 응답에서 JSON 데이터를 안전하게 추출 및 파싱합니다."""
    # 1. ```json ... ``` 마크다운 블록 추출 시도
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        json_str = code_block.group(1)
    else:
        # 2. 첫 번째 '{'부터 마지막 '}'까지 추출 시도
        bracket_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if bracket_match:
            json_str = bracket_match.group(1)
        else:
            raise ValueError("응답에서 JSON 데이터 블록을 찾을 수 없습니다.")

    parsed = json.loads(json_str)

    # 필드명 및 자료형 정규화
    def parse_number(val, default=0.0):
        if val is None:
            return default
        if isinstance(val, (int, float)):
            return float(val)
        num_match = re.search(r"[-+]?\d*\.?\d+", str(val))
        return float(num_match.group(0)) if num_match else default

    meal_name = parsed.get("meal_name") or parsed.get("식단명") or "분석된 식단"
    calories = parse_number(parsed.get("calories") if parsed.get("calories") is not None else parsed.get("칼로리"))
    carbs = parse_number(parsed.get("carbs") if parsed.get("carbs") is not None else parsed.get("탄수화물"))
    sugar = parse_number(parsed.get("sugar") if parsed.get("sugar") is not None else parsed.get("당류"))
    ai_feedback = parsed.get("ai_feedback") or parsed.get("분석내용") or text

    return {
        "meal_name": str(meal_name),
        "calories": calories,
        "carbs": carbs,
        "sugar": sugar,
        "ai_feedback": str(ai_feedback)
    }

# 이미지 처리 및 AI 분석
if img_file is not None:
    image = Image.open(img_file)
    st.image(image, caption="선택된 음식 이미지", use_container_width=True)

    prompt = f"""
    너는 {user_name}님의 전담 임상 영양사야.
    사용자의 정보는 다음과 같아:
    - 이름: {user_name}
    - 나이: {user_age}
    - 성별: {user_gender}
    - 오늘 목표 당 섭취량: {daily_goal}g
        
    분석을 수행한 뒤, 사용자가 읽기 좋은 결과와 데이터베이스 기록용 JSON 결과를 함께 제공해줘.
    
    1. [인사 및 요약]: {user_name}님, 보여주신 음식의 정보를 알려드릴게요.
    2. [영양소 정보]: 추정 당류 함량 (g), 추정 탄수화물 함량 (g), 칼로리(kcal)
    3. [개인 맞춤 분석]: 이 음식이 사용자의 목표치({daily_goal}g)에서 몇 %나 차지하는지 계산해줘.
       (예: 이 쿠키 한 개는 {user_name}님의 하루 목표 섭취량의 60%에 달합니다!)
    4. [영양사의 조언]: 사용자의 나이와 목표를 고려해서 혈당을 덜 올리는 섭취 꿀팁을 알려줘.

    [분석 리포트] : 위 1~4번 형식으로 사용자에게 보여줄 친절한 메시지를 작성해줘.
    [JSON 데이터] : 아래 JSON 형식으로만 데이터를 작성해줘. 단위(g, kcal 등) 없이 순수 숫자만 기재해줘.
    ```json
    {{
        "meal_name": "음식 이름",
        "calories": 0,
        "carbs": 0,
        "sugar": 0,
        "ai_feedback": "분석 리포트 전체 내용"
    }}
    ```
    """

    if st.button("영양소 분석하기"):
        if "GOOGLE_API_KEY" not in st.secrets or not st.secrets["GOOGLE_API_KEY"]:
            st.error("Google Gemini API 키가 설정되지 않았습니다. .streamlit/secrets.toml을 확인해주세요.")
        else:
            with st.spinner("AI 영양사가 분석 중입니다..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content([prompt, image])
                    st.session_state.ai_result = response.text
                    st.success("분석 완료!")
                except Exception as e:
                    st.error(f"AI 분석 중 오류가 발생했습니다: {e}")

    # 분석 결과 출력 및 Supabase 저장
    if 'ai_result' in st.session_state:
        result_text = st.session_state.ai_result

        st.write("### AI 분석 결과")
        st.write(result_text)

        if st.button("Supabase에 저장하기"):
            try:
                parsed_data = extract_and_parse_json(result_text)
                save_diet_record(
                    meal_name=parsed_data["meal_name"],
                    calories=parsed_data["calories"],
                    carbs=parsed_data["carbs"],
                    sugar=parsed_data["sugar"],
                    ai_feedback=parsed_data["ai_feedback"]
                )
                st.success(f"'{parsed_data['meal_name']}' 식단이 Supabase에 성공적으로 저장되었습니다!")
                st.balloons()
            except Exception as e:
                st.error(f"데이터 형식이 올바르지 않거나 저장에 실패했습니다: {e}")
