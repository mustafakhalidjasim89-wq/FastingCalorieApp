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

# 2. تهيئة الـ API (قم بإدخال المفتاح في Streamlit Secrets أو حقل إدخال)
st.title("🔥 حارس التغذية والصيام المتقطع")

api_key = st.sidebar.text_input("أدخل Google Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)

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

# التحقق من حالة الصيام الحالية
is_fasting = False
remaining_time = timedelta(0)

if st.session_state.fast_start_time:
    elapsed_time = datetime.now() - st.session_state.fast_start_time
    required_hours = timedelta(hours=fasting_plan)
    
    if elapsed_time < required_hours:
        is_fasting = True
        remaining_time = required_hours - elapsed_time
    else:
        st.sidebar.success("🎉 انتهت فترة الصيام المتقطع! يمكنك تناول الطعام الآن.")

# 4. الشاشة الرئيسية وإجبار المستخدم على الصيام
if is_fasting:
    st.error("🚨 التطبيق مغلق حالياً لأنك في فترة صيام!")
    
    hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    st.metric(label="الوقت المتبقي لفتح نافذة الأكل", value=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    st.info(f"نظامك الحالي: {fasting_plan} ساعة صيام. يرجى الامتناع تماماً عن تناول السعرات.")
    st.image("https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?q=80&w=600", caption="التزم بصيامك لتحقيق هدفك!")

else:
    st.subheader("📸 التقاط/رفع صورة الوجبة لتحليلها")
    uploaded_file = st.file_uploader("التقط صورة للوجبة عبر كاميرا الموبايل:", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='الوجبة المرفوعة', use_container_width=True)
        
        analyze_btn = st.button("تحليل الوجبة والسعرات 🔍")

        if analyze_btn:
            if not api_key:
                st.error("يرجى إدخال API Key في القائمة الجانبية أولاً!")
            else:
                with st.spinner("جاري تحليل الوجبة وتقييم مخاطرها..."):
                    try:
                        model = genai.GenerativeModel('gemini-3.6-flash')
                        
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
