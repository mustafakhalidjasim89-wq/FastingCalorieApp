import streamlit as st
import os
from google import genai
from google.genai import types
from PIL import Image
from datetime import datetime, timedelta
import re

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="حارس التغذية والصيام المتقطع",
    page_icon="🔥",
    layout="centered"
)

# 2. العنوان والتوقيع الرئيسي
st.title("🔥 حارس التغذية والصيام المتقطع")
st.caption("Designed by: Mustafa Khalid Jasim")

# 3. إدارة وإدخال API Key بأمان
st.sidebar.header("🔑 إعدادات المفتاح (AQ.Ab8RN6JizY-2-MXKBwDXrauL8UoqT_HBOQlcdqVBJOELyvTjFw)")

# محاولة جلب المفتاح من Secrets أولاً أو من المتغيرات البيئية
api_key = st.secrets.get("AQ.Ab8RN6JizY-2-MXKBwDXrauL8UoqT_HBOQlcdqVBJOELyvTjFw") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    user_key_input = st.sidebar.text_input(
        "AQ.Ab8RN6JizY-2-MXKBwDXrauL8UoqT_HBOQlcdqVBJOELyvTjFw:", 
        type="password",
        help="احصل على مفتاح مجاني من https://aistudio.google.com/"
    )
    if user_key_input:
        api_key = user_key_input.strip()

# دالة لتصغير حجم الصورة لسرعة معالجة استثنائية
def optimize_image(img, max_size=800):
    img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img

# 4. إدارة الجلسة للسعرات والسجل اليومي
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2000

if 'meals_history' not in st.session_state:
    st.session_state.meals_history = []

if 'fast_start_time' not in st.session_state:
    st.session_state.fast_start_time = None

# 5. القائمة الجانبية: إعدادات الهدف اليومي والصيام المتقطع
st.sidebar.header("🎯 الهدف اليومي للسعرات")
st.session_state.daily_target = st.sidebar.number_input(
    "حدد حد السعرات اليومي (Kcal):", 
    min_value=1000, 
    max_value=5000, 
    value=st.session_state.daily_target, 
    step=100
)

st.sidebar.markdown("---")
st.sidebar.header("⏱️ نظام الصيام المتقطع")
fasting_plan = st.sidebar.selectbox("اختر خطة الصيام (ساعة):", [12, 14, 16, 20])

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("بدء الصيام الآن"):
        st.session_state.fast_start_time = datetime.now()
        st.success("تم بدء الصيام!")

with col2:
    if st.button("إنهاء الصيام"):
        st.session_state.fast_start_time = None
        st.warning("تم إنهاء الصيام.")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ إعادة ضبط سجل اليوم"):
    st.session_state.meals_history = []
    st.sidebar.success("تم مسح سجل الوجبات اليومي!")

st.sidebar.markdown("---")
st.sidebar.markdown("**Designed by:**\nMustafa Khalid Jasim")

# 6. عرض لوحة متابعة السعرات والصيام
consumed_calories = sum(meal['calories'] for meal in st.session_state.meals_history)
remaining_calories = st.session_state.daily_target - consumed_calories

st.subheader("📊 الميزانية اليومية للسعرات")
metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("الهدف اليومي", f"{st.session_state.daily_target} سعرة")
metric_col2.metric("المستهلك حتى الآن", f"{consumed_calories} سعرة")

if remaining_calories >= 0:
    metric_col3.metric("المتبقي لك اليوم", f"{remaining_calories} سعرة", delta=f"{remaining_calories} Kcal")
else:
    metric_col3.metric("تجاوزت الحد بـ", f"{abs(remaining_calories)} سعرة", delta=f"-{abs(remaining_calories)} Kcal", delta_color="inverse")

# شريط حالة الصيام المتقطع
if st.session_state.fast_start_time:
    elapsed_time = datetime.now() - st.session_state.fast_start_time
    required_hours = timedelta(hours=fasting_plan)
    
    if elapsed_time < required_hours:
        remaining_time = required_hours - elapsed_time
        hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.info(f"⏳ أنت الآن في فترة صيام ({fasting_plan} ساعة). الوقت المتبقي: {hours:02d}:{minutes:02d}:{seconds:02d}")
    else:
        st.success("🎉 انتهت فترة الصيام المتقطع!")

st.markdown("---")

# 7. التقاط أو اختيار صورة الوجبة
st.subheader("📸 فحص وتسجيل وجبة جديدة")

input_method = st.radio(
    "اختر مصدر الصورة:",
    ["📷 الكاميرا المباشرة", "🖼️ اختيار من المعرض / الاستوديو"],
    horizontal=True
)

uploaded_image = None

if input_method == "📷 الكاميرا المباشرة":
    uploaded_image = st.camera_input("التقط صورة للوجبة مباشرة:")
else:
    uploaded_image = st.file_uploader("اختر صورة الوجبة من الاستوديو:", type=["jpg", "jpeg", "png"])

# 8. معالجة وتحليل الوجبة وإضافتها للسجل
if uploaded_image is not None:
    raw_image = Image.open(uploaded_image)
    optimized_img = optimize_image(raw_image)

    if input_method == "🖼️ اختيار من المعرض / الاستوديو":
        st.image(optimized_img, caption='الوجبة المختارة', use_container_width=True)
    
    meal_name = st.text_input("اسم الوجبة (اختياري للتسجيل):", value="وجبة مسجلة")
    analyze_btn = st.button("تحليل الوجبة وإضافتها للسجل 🔍", type="primary")

    if analyze_btn:
        if not api_key:
            st.error("⚠️ يرجى إدخال Gemini API Key في القائمة الجانبية أو ضبطه في Secrets للبدء!")
        else:
            with st.spinner("جاري التحليل السريع للوجبة... ⚡"):
                try:
                    # إعداد الـ Client باستخدام المكتبة الجديدة الحديثة
                    client = genai.Client(api_key=api_key)
                    
                    prompt = """
                    أنت خبير تغذية صارم جداً ولا تجامل (Brutally Honest). 
                    قم بتحليل صورة الوجبة المرفقة واكتب التقرير بشكل اختصار ومباشر دون إطالة وفق التالي:

                    الإجمالي التقديري للسعرات: [اكتب الرقم فقط ثم كلمة سعرة، مثال: 650 سعرة]

                    1. **المكونات والسعرات:** (تقدير سريع بدقة)
                    2. **الماكروز:** (بروتين/كارب/دهون)
                    3. **النقد الصارم والحكم النهائي:** (مخاطر الوجبة ونصيحة حازمة بدون مجاملة في 3 أسطر فقط).
                    """

                    # الاستدعاء الصحيح وفق google-genai
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=[optimized_img, prompt]
                    )
                    
                    analysis_text = response.text

                    # استخراج عدد السعرات تلقائياً
                    cal_match = re.search(r'الإجمالي التقديري للسعرات:\s*(\d+)', analysis_text)
                    extracted_calories = int(cal_match.group(1)) if cal_match else 0

                    # حفظ الوجبة في السجل اليومي
                    st.session_state.meals_history.append({
                        "time": datetime.now().strftime("%I:%M %p"),
                        "name": meal_name,
                        "calories": extracted_calories,
                        "details": analysis_text
                    })

                    st.markdown("---")
                    st.markdown("### 📊 التقرير والتحليل الغذائي:")
                    st.markdown(analysis_text)
                    st.success(f"✅ تم التسجيل ورصد {extracted_calories} سعرة حرارية!")

                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")

# 9. عرض سجل الوجبات اليومية
if st.session_state.meals_history:
    st.markdown("---")
    st.subheader("📋 سجل الوجبات اليومية")
    for idx, meal in enumerate(reversed(st.session_state.meals_history), 1):
        with st.expander(f"🍽️ {meal['name']} - {meal['calories']} سعرة ({meal['time']})"):
            st.markdown(meal['details'])

# تذييل الصفحة السفلية
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Designed by: Mustafa Khalid Jasim</div>", unsafe_allow_html=True)
