import streamlit as st
import google.generativeai as genai
from PIL import Image
from datetime import datetime, timedelta

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="حاسبة السعرات وحارس الصيام",
    page_icon="🔥",
    layout="centered"
)

st.title("🔥 حارس التغذية والصيام المتقطع")

# 2. المفتاح المثبت تلقائياً
API_KEY = "AQ.Ab8RN6LtXyeBL-q6uovDkpn1XCccKKhjrDniJxefItYhM56yFg"

if API_KEY and API_KEY != "ضع_مفتاح_GEMINI_الخاص_بك_هنا":
    genai.configure(api_key=API_KEY)
else:
    # خيار بديل في حال أردت إدخاله من القائمة الجانبية
    api_key_input = st.sidebar.text_input("أدخل Google Gemini API Key:", type="password")
    if api_key_input:
        genai.configure(api_key=api_key_input)
        API_KEY = api_key_input

# 3. إدارة نظام الصيام المتقطع
st.sidebar.header("⏱️ نظام الصيام المتقطع")
fasting_plan = st.sidebar.selectbox("اختر خطة الصيام (ساعة):", [12, 14, 16, 20])

if 'fast_start_time' not in st.session_state:
    st.session_state.fast_start_time = None

col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("بدء الصيام الآن"):
        st.session_state.fast_start_time = datetime.now()
        st.success("تم بدء الصيام!")

with col2:
    if st.button("إنهاء الصيام"):
        st.session_state.fast_start_time = None
        st.warning("تم إنهاء الصيام.")

# عرض حالة الصيام بدون غلق البرنامج
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

# 4. تحليل الوجبة (مفتوح دائماً)
st.subheader("📸 التقاط/رفع صورة الوجبة لتحليلها")
uploaded_file = st.file_uploader("التقط صورة للوجبة عبر كاميرا الموبايل:", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='الوجبة المرفوعة', use_container_width=True)
    
    analyze_btn = st.button("تحليل الوجبة والسعرات 🔍")

    if analyze_btn:
        if not API_KEY or API_KEY == "ضع_مفتاح_GEMINI_الخاص_بك_هنا":
            st.error("يرجى وضع المفتاح الخاص بك في الكود أو إدخاله من القائمة الجانبية!")
        else:
            with st.spinner("جاري تحليل الوجبة وتقييم مخاطرها..."):
                try:
                    # تم التحديث لاستخدام اسم الموديل المعتمد لإنهاء خطأ 404
                    model = genai.GenerativeModel('models/gemini-1.5-flash')
                    
                    prompt = """
                    أنت خبير تغذية صارم جداً ولا تجامل على الإطلاق (Brutally Honest). 
                    قم بتحليل الصورة التالية للوجبة وتقديم التقرير باللغة العربية بالصيغة التالية:

                    1. **مكونات الوجبة:** (تحديد كل مكون بدقة)
                    2. **السعرات الحرارية التقديرية:** (تقدير دقيق لكل مكون والإجمالي)
                    3. **الماكروز (تخميني):** (البروتين، الكارب، الدهون)
                    4. **المخاطر الصحية والتقييم الصارم:** (انتقد الوجبة بدون أي مجاملة، وضح التأثير على الوزن، نسبة السكر، والدهون، وهل تصلح للدايت أم لا).
                    5. **الحكم النهائي:** (ضع نصيحة صارمة ومباشرة للمستخدم).
                    """

                    response = model.generate_content([prompt, image])
                    st.markdown("---")
                    st.markdown(response.text)

                except Exception as e:
                    st.error(f"حدث خطأ أثناء التحليل: {e}")
