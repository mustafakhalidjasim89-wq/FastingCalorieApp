import base64
import io
import json
import os
import re
import time
from datetime import datetime, timedelta

from PIL import Image
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Page Configuration & Title
# ---------------------------------------------------------
st.set_page_config(
    page_title="حارس التغذية والصيام المتقطع", page_icon="🔥", layout="centered"
)

st.title("🔥 حارس التغذية والصيام المتقطع")
st.caption("Designed by: Mustafa Khalid Jasim")


# ---------------------------------------------------------
# 2. Helper Functions
# ---------------------------------------------------------
def optimize_image(img, max_size=800):
    """Resize and convert image to strict RGB JPEG."""
    img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img


def encode_image_to_base64(pil_img):
    """Convert a PIL image to a Base64 string for API payloads."""
    buffered = io.BytesIO()
    pil_img.save(buffered, format="JPEG", quality=85)
    img_bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode("utf-8")


# ---------------------------------------------------------
# 3. Session State Initialization
# ---------------------------------------------------------
if "daily_target" not in st.session_state:
    st.session_state.daily_target = 2000

if "meals_history" not in st.session_state:
    st.session_state.meals_history = []

if "fast_start_time" not in st.session_state:
    st.session_state.fast_start_time = None

# ---------------------------------------------------------
# 4. Sidebar Options
# ---------------------------------------------------------
st.sidebar.header("🔑 إعدادات OpenRouter API")

raw_api_key = (
    st.secrets.get("OPENROUTER_API_KEY")
    or os.environ.get("OPENROUTER_API_KEY")
    or ""
)

user_key_input = st.sidebar.text_input(
    "أدخل OpenRouter API Key:",
    value=raw_api_key,
    type="password",
    help="أدخل المفتاح الذي يبدأ بـ sk-or-v1-",
)

api_key = user_key_input.strip() if user_key_input else ""

# Tested OpenRouter Vision Models
selected_model = st.sidebar.selectbox(
    "اختر نموذج الذكاء الاصطناعي:",
    [
        "google/gemini-2.0-flash-001",
        "google/gemini-flash-1.5",
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-sonnet",
    ],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.header("🎯 الهدف اليومي للسعرات")
st.session_state.daily_target = st.sidebar.number_input(
    "حدد حد السعرات اليومي (Kcal):",
    min_value=1000,
    max_value=5000,
    value=st.session_state.daily_target,
    step=100,
)

st.sidebar.markdown("---")
st.sidebar.header("⏱️ نظام الصيام المتقطع")
fasting_plan = st.sidebar.selectbox(
    "اختر خطة الصيام (ساعة):", [12, 14, 16, 20]
)

col_fast_start, col_fast_end = st.sidebar.columns(2)
with col_fast_start:
    if st.button("بدء الصيام الآن"):
        st.session_state.fast_start_time = datetime.now()
        st.success("تم بدء الصيام!")

with col_fast_end:
    if st.button("إنهاء الصيام"):
        st.session_state.fast_start_time = None
        st.warning("تم إنهاء الصيام.")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ إعادة ضبط سجل اليوم"):
    st.session_state.meals_history = []
    st.sidebar.success("تم مسح سجل الوجبات اليومي!")

st.sidebar.markdown("---")
st.sidebar.markdown("**Designed by:**\nMustafa Khalid Jasim")

# ---------------------------------------------------------
# 5. Dashboard Metrics
# ---------------------------------------------------------
consumed_calories = sum(
    meal["calories"] for meal in st.session_state.meals_history
)
remaining_calories = st.session_state.daily_target - consumed_calories

st.subheader("📊 الميزانية اليومية للسعرات")
metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("الهدف اليومي", f"{st.session_state.daily_target} سعرة")
metric_col2.metric("المستهلك حتى الآن", f"{consumed_calories} سعرة")

if remaining_calories >= 0:
    metric_col3.metric(
        "المتبقي لك اليوم",
        f"{remaining_calories} سعرة",
        delta=f"{remaining_calories} Kcal",
    )
else:
    metric_col3.metric(
        "تجاوزت الحد بـ",
        f"{abs(remaining_calories)} سعرة",
        delta=f"-{abs(remaining_calories)} Kcal",
        delta_color="inverse",
    )

if st.session_state.fast_start_time:
    elapsed_time = datetime.now() - st.session_state.fast_start_time
    required_hours = timedelta(hours=fasting_plan)

    if elapsed_time < required_hours:
        remaining_time = required_hours - elapsed_time
        hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.info(
            f"⏳ أنت الآن في فترة صيام ({fasting_plan} ساعة). الوقت المتبقي:"
            f" {hours:02d}:{minutes:02d}:{seconds:02d}"
        )
    else:
        st.success("🎉 انتهت فترة الصيام المتقطع!")

st.markdown("---")

# ---------------------------------------------------------
# 6. Image Input
# ---------------------------------------------------------
st.subheader("📸 فحص وتسجيل وجبة جديدة")

input_method = st.radio(
    "اختر مصدر الصورة:",
    ["📷 الكاميرا المباشرة", "🖼️ اختيار من المعرض / الاستوديو"],
    horizontal=True,
)

uploaded_image = None

if input_method == "📷 الكاميرا المباشرة":
    uploaded_image = st.camera_input("التقط صورة للوجبة مباشرة:")
else:
    uploaded_image = st.file_uploader(
        "اختر صورة الوجبة من الاستوديو:", type=["jpg", "jpeg", "png"]
    )

# ---------------------------------------------------------
# 7. AI Analysis Engine
# ---------------------------------------------------------
if uploaded_image is not None:
    raw_image = Image.open(uploaded_image)
    optimized_img = optimize_image(raw_image)

    if input_method == "🖼️ اختيار من المعرض / الاستوديو":
        st.image(
            optimized_img, caption="الوجبة المختارة", use_container_width=True
        )

    meal_name = st.text_input(
        "اسم الوجبة (اختياري للتسجيل):", value="وجبة مسجلة"
    )
    analyze_btn = st.button("تحليل الوجبة وإضافتها للسجل 🔍", type="primary")

    if analyze_btn:
        if not api_key:
            st.error("⚠️ يرجى إدخال OpenRouter API Key في القائمة الجانبية!")
        else:
            with st.spinner("جاري فحص الصورة وتحليلها بدقة... ⚡"):
                try:
                    base64_str = encode_image_to_base64(optimized_img)
                    data_url = f"data:image/jpeg;base64,{base64_str}"

                    # Unique prompt with timestamp to force fresh inference
                    prompt = f"""
                    [Timestamp: {time.time()}]
                    انظر إلى هذه الصورة بدقة عالية واشرح ما تراه فقط.
                    إذا كانت الصورة تحتوي على ماء أو كوب ماء فارغ/مليء، السعرات تكون 0 سعرة.
                    أنت خبير تغذية صارم جداً. قم بتحليل العنصر في الصورة بدقة واكتب التقرير كالتالي:

                    الإجمالي التقديري للسعرات: [اكتب الرقم فقط ثم كلمة سعرة، مثال: 0 سعرة]

                    1. **المكونات والسعرات:** (تحديد العنصر المباشر في الصورة بدقة)
                    2. **القيم الغذائية:** (البروتين/الكربوهيدرات/الدهون)
                    3. **النقد الصارم والحكم النهائي:** (نصيحة في 3 أسطر).
                    """

                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://streamlit.io",
                        "X-Title": "Fasting Guard Vision",
                        "Content-Type": "application/json",
                    }

                    payload = {
                        "model": selected_model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url},
                                },
                            ],
                        }],
                    }

                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=40,
                    )

                    if response.status_code == 200:
                        res_json = response.json()
                        analysis_text = res_json["choices"][0]["message"][
                            "content"
                        ]

                        cal_match = re.search(
                            r"الإجمالي التقديري للسعرات:\s*(\d+)", analysis_text
                        )
                        if not cal_match:
                            cal_match = re.search(
                                r"(\d+)\s*سعرة", analysis_text
                            )

                        extracted_calories = (
                            int(cal_match.group(1)) if cal_match else 0
                        )

                        st.session_state.meals_history.append({
                            "time": datetime.now().strftime("%I:%M %p"),
                            "name": meal_name,
                            "calories": extracted_calories,
                            "details": analysis_text,
                        })

                        st.rerun()
                    else:
                        st.error(
                            f"فشل الاتصال بـ OpenRouter ({response.status_code}): {response.text}"
                        )

                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")

# ---------------------------------------------------------
# 8. Daily Meals Log
# ---------------------------------------------------------
if st.session_state.meals_history:
    st.markdown("---")
    st.subheader("📋 سجل الوجبات اليومية")
    for idx, meal in enumerate(reversed(st.session_state.meals_history), 1):
        with st.expander(
            f"🍽️ {meal['name']} - {meal['calories']} سعرة ({meal['time']})"
        ):
            st.markdown(meal["details"])

# ---------------------------------------------------------
# 9. Footer
# ---------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Designed by: Mustafa Khalid Jasim</div>",
    unsafe_allow_html=True,
)
