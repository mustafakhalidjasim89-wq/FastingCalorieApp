import base64
from datetime import datetime, timedelta
import io
import json
import os
import re
import time

from PIL import Image
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Page Configuration & Custom CSS Styling (واجهة حديثة)
# ---------------------------------------------------------
st.set_page_config(
    page_title="حارس التغذية والصحة الذكي",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# تطبيق تنسيق بصري احترافي بألوان متناسقة (Emerald & Teal Theme)
st.markdown(
    """
<style>
    /* Gradient Background & Fonts */
    .main {
        background-color: #f8fafc;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Header Styling */
    .main-title {
        background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.3rem;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        text-align: center;
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Card Container Style */
    .css-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
    }
    
    /* Metric Card Customization */
    [data-testid="stMetricValue"] {
        font-weight: 700;
        color: #0f172a;
    }
    
    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #f1f5f9;
        border-left: 1px solid #e2e8f0;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-title">🥗 حارس التغذية والصحة الذكي</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-title">نظام المتابعة التغذوية والتحليل الطبي الشامل |'
    " Designed by: Mustafa Khalid Jasim</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 2. Helper Functions
# ---------------------------------------------------------
def optimize_image(img, max_size=900):
    """Resize and compress image for fast AI processing."""
    img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img


def encode_image_to_base64(pil_img):
    """Convert PIL Image to Base64 string."""
    buffered = io.BytesIO()
    pil_img.save(buffered, format="JPEG", quality=85)
    img_bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode("utf-8")


def calculate_bmr(weight, height, age, gender):
    """حساب السعرات الحرارية الأساسية (Mifflin-St Jeor Equation)."""
    if gender == "ذكر":
        return int(10 * weight + 6.25 * height - 5 * age + 5)
    else:
        return int(10 * weight + 6.25 * height - 5 * age - 161)


# ---------------------------------------------------------
# 3. Session State Initialization
# ---------------------------------------------------------
if "meals_history" not in st.session_state:
    st.session_state.meals_history = []

if "fast_start_time" not in st.session_state:
    st.session_state.fast_start_time = None

if "latest_analysis" not in st.session_state:
    st.session_state.latest_analysis = None

if "medical_report_analysis" not in st.session_state:
    st.session_state.medical_report_analysis = None

# ---------------------------------------------------------
# 4. Sidebar: API Key & Models
# ---------------------------------------------------------
with st.sidebar:
    st.header("🔑 إعدادات النظام والنموذج")

    raw_api_key = (
        st.secrets.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or ""
    )

    user_key_input = st.text_input(
        "أدخل OpenRouter API Key:",
        value=raw_api_key,
        type="password",
        help="أدخل المفتاح الخاص بك ابتداءً بـ sk-or-v1-",
    )
    api_key = user_key_input.strip() if user_key_input else ""

    selected_model = st.selectbox(
        "اختر نموذج الذكاء الاصطناعي:",
        [
            "google/gemini-2.0-flash-001",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
        ],
        index=0,
    )

    st.markdown("---")
    st.header("⏱️ نظام الصيام المتقطع")
    fasting_plan = st.selectbox("خطة الصيام (ساعة):", [12, 14, 16, 18, 20])

    col_fast_s, col_fast_e = st.columns(2)
    with col_fast_s:
        if st.button("بدء الصيام 🚀", use_container_width=True):
            st.session_state.fast_start_time = datetime.now()
            st.success("تم بدء الصيام!")

    with col_fast_e:
        if st.button("إنهاء الصيام 🛑", use_container_width=True):
            st.session_state.fast_start_time = None
            st.warning("تم إنهاء الصيام.")

    st.markdown("---")
    if st.button("🗑️ إعادة ضبط بيانات اليوم", use_container_width=True):
        st.session_state.meals_history = []
        st.session_state.latest_analysis = None
        st.session_state.medical_report_analysis = None
        st.success("تم مسح السجل اليومي!")

# ---------------------------------------------------------
# 5. User Profile & Health Diagnostics Section
# ---------------------------------------------------------
st.markdown("### 👤 الملف الصحي وتخصيص السعرات")

with st.expander(
    "📋 أدخل بياناتك الشخصية والتقارير الطبية للحصول على تحليل دقيق",
    expanded=True,
):
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)

    with col_p1:
        age = st.number_input("العمر (سنة):", min_value=10, max_value=100, value=30)
    with col_p2:
        gender = st.selectbox("الجنس:", ["ذكر", "أنثى"])
    with col_p3:
        weight = st.number_input(
            "الوزن (كجم):", min_value=30.0, max_value=250.0, value=75.0, step=0.5
        )
    with col_p4:
        height = st.number_input(
            "الطول (سم):", min_value=100.0, max_value=230.0, value=175.0, step=0.5
        )

    col_p5, col_p6 = st.columns(2)
    with col_p5:
        activity_level = st.selectbox(
            "مستوى النشاط البدني:",
            [
                "خامل (مكتب/بدون تمارين)",
                "نشاط خفيف (تمارين 1-3 أيام/أسبوع)",
                "نشاط متوسط (تمارين 3-5 أيام/أسبوع)",
                "نشاط عالٍ (تمارين شاقة يومياً)",
            ],
        )
    with col_p6:
        medical_conditions = st.multiselect(
            "الأمراض والحالات الصحية المشخصة (إن وجدت):",
            [
                "السكري (Type 2 / Type 1)",
                "ضغط الدم المرتفع",
                "خمول الغدة الدرقية",
                "تكيس المبايض (PCOS)",
                "ارتفاع الكوليسترول / الدهون الثلاثية",
                "مقاومة الانسولين",
                "الكبد الدهني",
                "لا توجد أمراض مزمنة",
            ],
        )

    st.markdown("---")
    st.markdown("##### 📄 تحميل تقرير طبي / تحاليل دم (اختياري للتحليل الذكي)")
    uploaded_report = st.file_uploader(
        "ارفع صورة التقرير الطبي أو صورة التحليل (CBC, Lipid Profile, Thyroid, HBA1c):",
        type=["jpg", "jpeg", "png"],
        key="medical_report",
    )

    # حساب السعرات الحرارية التلقائي بناءً على المعادلات المقبولة طبياً
    base_bmr = calculate_bmr(weight, height, age, gender)
    activity_multipliers = {
        "خامل (مكتب/بدون تمارين)": 1.2,
        "نشاط خفيف (تمارين 1-3 أيام/أسبوع)": 1.375,
        "نشاط متوسط (تمارين 3-5 أيام/أسبوع)": 1.55,
        "نشاط عالٍ (تمارين شاقة يومياً)": 1.725,
    }
    calculated_tdee = int(base_bmr * activity_multipliers[activity_level])

    # تحليلات التقارير الطبية وتراكم الدهون بالذكاء الاصطناعي
    if uploaded_report is not None and st.button(
        "تحليل التقرير الطبي وتوليد التوصيات الصحية 🧬"
    ):
        if not api_key:
            st.error("⚠️ يرجى إدخال OpenRouter API Key في الشريط الجانبي أولاً!")
        else:
            with st.spinner("جاري فحص التقرير الطبي وتحليل المؤشرات الحيوية... ⚡"):
                try:
                    rep_img = Image.open(uploaded_report)
                    opt_rep_img = optimize_image(rep_img)
                    base64_rep = encode_image_to_base64(opt_rep_img)

                    report_prompt = f"""
                    أنت طبيب واستشاري تغذية علاجية ومتخصص في تحليل الفحوصات والتقارير الطبية.
                    بيانات المريض الأساسية:
                    - العمر: {age} | الجنس: {gender} | الوزن: {weight} كجم | الطول: {height} سم
                    - الحالات التشخيصية المحددة: {', '.join(medical_conditions) if medical_conditions else 'لا يوجد'}

                    افحص الصورة المرفقة (التقرير الطبي / التحليل) بتمعن واكتب تقريراً طليقاً ومباشراً يحتوي على:
                    1. **ملخص نتائج التقرير الطبي:** (قراءة المؤشرات المرتفعة أو المنخفضة وأسبابها).
                    2. **توزيع وتركز الدهون المتوقع في الجسم:** (حدد أين تتركز الدهون غالبًا بناءً على حالة المريض، هل هي دهون أحشاء بطنية Visceral Fat، أم دهون محيطية أسفل الجسم، ومدى ارتباطها بهرمونات مثل الأنسولين/الكورتيزول).
                    3. **السعرات الحرارية والماكروز الموصى بها طبياً:** (استناداً إلى احتياج {calculated_tdee} سعرة، حدد ما إذا كان يجب تقليل السعرات والتوزيع المناسب للبروتين والدهون الصحية والنشويات).
                    4. **محاذير وتوصيات غذائية حازمة:** (أطعمة ممنوعة تماماً لحالته وأطعمة موصى بها).
                    """

                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://streamlit.io",
                        "X-Title": "Medical Diagnostics Guard",
                        "Content-Type": "application/json",
                    }

                    payload = {
                        "model": selected_model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": report_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_rep}"
                                    },
                                },
                            ],
                        }],
                    }

                    res = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        data=json.dumps(payload),
                        timeout=45,
                    )

                    if res.status_code == 200:
                        st.session_state.medical_report_analysis = res.json()[
                            "choices"
                        ][0]["message"]["content"]
                        st.success("✅ تم تحليل التقرير الطبي بنجاح!")
                    else:
                        st.error(f"حدث خطأ أثناء تحليل التقرير: {res.text}")
                except Exception as e:
                    st.error(f"خطأ في الاتصال: {e}")

# عرض نتائج التقرير الطبي إذا كانت متوفرة
if st.session_state.medical_report_analysis:
    st.info("🩺 **نتائج التحليل الطبي وتوزيع الدهون وتوصيات السعرات:**")
    st.markdown(st.session_state.medical_report_analysis)

st.markdown("---")

# ---------------------------------------------------------
# 6. Dashboard Metrics & Fasting Timer
# ---------------------------------------------------------
daily_target = calculated_tdee
consumed_calories = sum(
    meal["calories"] for meal in st.session_state.meals_history
)
remaining_calories = daily_target - consumed_calories

st.markdown("### 📊 الميزانية اليومية للوجبات والسعرات")
metric_c1, metric_c2, metric_c3, metric_c4 = st.columns(4)

metric_c1.metric("المعدل الأيضي الأساسي (BMR)", f"{base_bmr} Kcal")
metric_c2.metric("الاحتياج اليومي المستهدف", f"{daily_target} Kcal")
metric_c3.metric("المستهلك حتى الآن", f"{consumed_calories} Kcal")

if remaining_calories >= 0:
    metric_c4.metric(
        "المتبقي اليوم",
        f"{remaining_calories} Kcal",
        delta=f"{remaining_calories} Kcal",
    )
else:
    metric_c4.metric(
        "تجاوزت الحد بـ",
        f"{abs(remaining_calories)} Kcal",
        delta=f"-{abs(remaining_calories)} Kcal",
        delta_color="inverse",
    )

# عداد الصيام المتقطع
if st.session_state.fast_start_time:
    elapsed_time = datetime.now() - st.session_state.fast_start_time
    required_hours = timedelta(hours=fasting_plan)

    if elapsed_time < required_hours:
        remaining_time = required_hours - elapsed_time
        hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.warning(
            f"⏳ أنت الآن في فترة صيام متقطع ({fasting_plan} ساعة). الوقت"
            f" المتبقي: {hours:02d}:{minutes:02d}:{seconds:02d}"
        )
    else:
        st.success("🎉 تهانينا! أكملت فترة الصيام المتقطع بنجاح.")

st.markdown("---")

# ---------------------------------------------------------
# 7. Meal Image Acquisition & Vision Analysis Engine
# ---------------------------------------------------------
st.markdown("### 📸 فحص الوجبات عبر كاميرا الذكاء الاصطناعي")

input_method = st.radio(
    "اختر طريقة إدخال صورة الوجبة:",
    ["📷 الكاميرا المباشرة", "🖼️ رفع صورة من المعرض / الجهاز"],
    horizontal=True,
)

uploaded_meal_img = None
if input_method == "📷 الكاميرا المباشرة":
    uploaded_meal_img = st.camera_input("التقط صورة للوجبة مباشرة:")
else:
    uploaded_meal_img = st.file_uploader(
        "اختر صورة الوجبة من الاستوديو:",
        type=["jpg", "jpeg", "png"],
        key="meal_upload",
    )

if uploaded_meal_img is not None:
    raw_img = Image.open(uploaded_meal_img)
    opt_meal_img = optimize_image(raw_img)

    if input_method == "🖼️ رفع صورة من المعرض / الجهاز":
        st.image(
            opt_meal_img, caption="الوجبة المراد تحليلها", width=350
        )

    meal_custom_name = st.text_input("اسم الوجبة (اختياري):", value="وجبة مسجلة")

    if st.button("تحليل الوجبة وإضافتها للسجل 🔍", type="primary"):
        if not api_key:
            st.error("⚠️ يرجى إدخال OpenRouter API Key في القائمة الجانبية!")
        else:
            with st.spinner("جاري تحليل الوجبة بصرياً ومطابقتها مع حالتك الصحية... ⚡"):
                try:
                    b64_meal = encode_image_to_base64(opt_meal_img)
                    meal_data_url = f"data:image/jpeg;base64,{b64_meal}"

                    meal_prompt = f"""
                    [Req_ID: {time.time()}]
                    أنت أخصائي تغذية علاجية صارم جداً ومحترف.
                    سياق المريض الصحي:
                    - العمر: {age} | الوزن: {weight} كجم | الأمراض المشخصة: {', '.join(medical_conditions) if medical_conditions else 'لا يوجد'}

                    افحص هذه الصورة بدقة شديدة:
                    - إذا كانت الصورة تعبر عن ماء أو كوب فارغ/مشروب خالي من السعرات، اجعل الإجمالي 0 سعرة.
                    - اكتب التقرير بوضوح وفق الهيكل المحدد:

                    الإجمالي التقديري للسعرات: [اكتب الرقم فقط ثم كلمة سعرة، مثال: 0 سعرة أو 450 سعرة]

                    1. **المكونات والسعرات:** (تحديد الأطعمة والمكونات الظاهرة وحساب سعرات كل مكون).
                    2. **القيم الغذائية:** (البروتين / الكربوهيدرات / الدهون بالجرام).
                    3. **التأثير الصحي والملاءمة بحسب حالتك:** (هل هذه الوجبة مناسبة لحالته الصحية والأمراض التي يعاني منها وكيف تؤثر على نسبة الدهون والمؤشر الجلايسيمي).
                    4. **النقد الصارم والحكم النهائي:** (نصيحة صارمة ومباشرة بدون مجاملة في 3 أسطر).
                    """

                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://streamlit.io",
                        "X-Title": "Nutrition Vision Guard",
                        "Content-Type": "application/json",
                    }

                    payload = {
                        "model": selected_model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": meal_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": meal_data_url},
                                },
                            ],
                        }],
                    }

                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        data=json.dumps(payload),
                        timeout=40,
                    )

                    if response.status_code == 200:
                        analysis_text = response.json()["choices"][0][
                            "message"
                        ]["content"]

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
                            "name": meal_custom_name,
                            "calories": extracted_calories,
                            "details": analysis_text,
                        })

                        st.session_state.latest_analysis = analysis_text
                        st.success("✅ تم تحليل الوجبة وتسجيلها بنجاح!")
                    else:
                        st.error(
                            f"فشل الاتصال بـ OpenRouter ({response.status_code}): {response.text}"
                        )

                except Exception as e:
                    st.error(f"حدث خطأ أثناء معالجة الصورة: {e}")

# عرض التقرير الأخير للوجبة
if st.session_state.latest_analysis:
    st.markdown("#### 📋 تقرير الوجبة الأخيرة:")
    st.info(st.session_state.latest_analysis)

# ---------------------------------------------------------
# 8. Daily Log History
# ---------------------------------------------------------
if st.session_state.meals_history:
    st.markdown("---")
    st.markdown("### 📋 سجل الوجبات المسجلة اليوم")
    for idx, meal in enumerate(reversed(st.session_state.meals_history), 1):
        with st.expander(
            f"🍽️ {meal['name']} - {meal['calories']} Kcal ({meal['time']})"
        ):
            st.markdown(meal["details"])

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b;'>Developed & Designed by:"
    " <b>Mustafa Khalid Jasim</b></div>",
    unsafe_allow_html=True,
)
