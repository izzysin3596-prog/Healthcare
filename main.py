import streamlit as st
import base64

st.title("당뇨 케어 푸드 스캐너")

img_file = st.camera_input("음식을 촬영해주세요")

if img_file is not None:
    bytes_data = img_file.getvalue()
    base64_image = base64.b64encode(bytes_data).decode('utf-8')

    st.success("이미지 변환 성공")

    st.write("변환된 데이터 앞 100자 : ")
    st.code(base64_image[:100])
