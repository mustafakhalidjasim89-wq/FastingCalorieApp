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
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="حارس التغذية والصحة | Health & Nutrition Guard",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 2. Session State Initialization
# ---------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "العربية"

if "meals_history" not in st.session_state:
    st.session_state.meals_history = []

if "fast_start_time" not in st.session_state:
    st.session_state.fast_start_time = None

if "latest_analysis" not in st.session_state:
    st.session_state.latest_analysis = None

if "medical_report_analysis" not in st.session_state:
    st.session_state.medical_report_analysis = None

# حالة تخزين حسابات السعرات بعد الضغط على الزر
if "profile_calculated" not in st.session_state:
    st.session_state.profile_calculated = False
if "user_bmr" not in st.session_state:
    st.session_state.user_bmr = 0
if "user_tdee" not in st.session_state:
    st.session_state.user_tdee = 0

# ---------------------------------------------------------
# 3. Sidebar Setup
# ---------------------------------------------------------
with st.sidebar:
    st.header("🌐 Language / اللغة")
    selected_lang = st.radio(
        "Select Language / اختر اللغة:",
        ["العربية", "English"],
        index=0 if st.session_state.lang == "العربية" else 1,
    )
    st.session_state.lang = selected_lang

is_ar = st.session_state.lang == "العربية"

# Apply Dynamic RTL / LTR CSS with Streamlit Columns Fix
direction_css = f"""
<style>
    .main, [data-testid="stSidebar"], .stApp {{
        direction: {('rtl' if is_ar else 'ltr')};
        text-align: {('right' if is_ar else 'left')};
    }}
    
    {'''
    [data-testid="column"] {
        direction: rtl !important;
        text-align: right !important;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row-reverse !important;
    }
    ''' if is_ar else ''}

    .main-title {{
        background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        text-align: center;
        margin-bottom: 0.2rem;
    }}
    .sub-title {{
        text-align: center;
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }}
    div[data-testid="stMetricValue"] {{
        font-weight: 700;
    }}
</style>
"""

st.markdown(direction_css, unsafe_allow_html=True)

# Language Specific Translations
t = {
    "title": "🥗 حارس التغذية والصحة الذكي"
    if is_ar
    else "🥗 Smart Health & Nutrition Guard",
    "subtitle": (
        "نظام المتابعة التغذوية والتحليل الطبي الشامل | Designed by: Mustafa"
        " Khalid Jasim"
    )
    if is_ar
    else (
        "Comprehensive Nutrition Tracking & Medical Analysis | Designed by:"
        " Mustafa Khalid Jasim"
    ),
    "api_header": "🔑 إعدادات النموذج" if is_ar else "🔑 Model Settings",
    "api_key_label": "أدخل OpenRouter API Key:"
    if is_ar
    else "Enter OpenRouter API Key:",
    "select_model": "اختر نموذج الذكاء الاصطناعي:"
    if is_ar
    else "Select AI Model:",
    "fasting_header": "⏱️ نظام الصيام المتقطع"
    if is_ar
    else "⏱️ Intermittent Fasting",
    "fasting_plan": "خطة الصيام (ساعة):"
    if is_ar
    else "Fasting Plan (Hours):",
    "start_fast": "بدء الصيام 🚀" if is_ar else "Start Fast 🚀",
    "end_fast": "إنهاء الصيام 🛑" if is_ar else "End Fast 🛑",
    "reset_day": "🗑️ إعادة ضبط سجل اليوم" if is_ar else "🗑️ Reset Daily Log",
    "profile_header": "👤 أدخل بياناتك الشخصية لحساب السعرات المناسبة"
    if is_ar
    else "👤 Enter Your Details to Calculate Calories",
    "age": "العمر (سنة):" if is_ar else "Age (years):",
    "gender": "الجنس:" if is_ar else "Gender:",
    "gender_opts": ["ذكر", "أنثى"] if is_ar else ["Male", "Female"],
    "weight": "الوزن (كجم):" if is_ar else "Weight (kg):",
    "height": "الطول (سم):" if is_ar else "Height (cm):",
    "activity": "مستوى النشاط البدني:" if is_ar else "Activity Level:",
    "activity_opts": [
        "خامل (مكتب/بدون تمارين)",
        "نشاط خفيف (تمارين 1-3 أيام/أسبوع)",
        "نشاط متوسط (تمارين 3-5 أيام/أسبوع)",
        "نشاط عالٍ (تمارين شاقة يومياً)",
    ]
    if is_ar
    else [
        "Sedentary (Office/No Exercise)",
        "Lightly Active (1-3 days/week)",
        "Moderately Active (3-5 days/week)",
        "Very Active (Daily Heavy Exercise)",
    ],
    "conditions": "الأمراض والحالات الصحية المشخصة:"
    if is_ar
    else "Diagnosed Medical Conditions:",
    "conditions_opts": [
        "السكري (Type 2 / Type 1)",
        "ضغط الدم المرتفع",
        "خمول الغدة الدرقية",
        "تكيس المبايض (PCOS)",
        "ارتفاع الكوليسترول / الدهون الثلاثية",
        "مقاومة الانسولين",
        "الكبد الدهني",
        "لا توجد أمراض مزمنة",
    ]
    if is_ar
    else [
        "Diabetes (Type 1 / Type 2)",
        "Hypertension (High BP)",
        "Hypothyroidism",
        "PCOS",
        "High Cholesterol / Triglycerides",
        "Insulin Resistance",
        "Fatty Liver",
        "None",
    ],
    "upload_report": "📄 تحميل تقرير طبي / تحاليل دم (اختياري)"
    if is_ar
    else "📄 Upload Medical Report / Blood Test (Optional)",
    "btn_calc_profile": "📊 تحليل البيانات وحساب السعرات المناسبة"
    if is_ar
    else "📊 Calculate Recommended Calories",
    "dashboard_header": "📊 الميزانية اليومية للوجبات والسعرات"
    if is_ar
    else "📊 Daily Calories & Meal Dashboard",
    "bmr": "المعدل الأيضي (BMR)" if is_ar else "BMR",
    "target": "الاحتياج المستهدف" if is_ar else "Target Intake",
    "consumed": "المستهلك" if is_ar else "Consumed",
    "remaining": "المتبقي اليوم" if is_ar else "Remaining",
    "over_limit": "تجاوزت الحد بـ" if is_ar else "Exceeded By",
    "meal_header": "📸 فحص الوجبات عبر كاميرا الذكاء الاصطناعي"
    if is_ar
    else "📸 AI Food & Meal Scanner",
    "input_method": "اختر طريقة إدخال صورة الوجبة:"
    if is_ar
    else "Choose image source:",
    "source_opts": ["📷 الكاميرا المباشرة", "🖼️ رفع صورة من المعرض / الجهاز"]
    if is_ar
    else ["📷 Live Camera", "🖼️ Upload from Gallery"],
    "meal_name": "اسم الوجبة (اختياري):" if is_ar else "Meal Name (Optional):",
    "btn_analyze_meal": "تحليل الوجبة وإضافتها للسجل 🔍"
    if is_ar
    else "Analyze Meal & Save Log 🔍",
    "latest_report_title": "📋 التقرير والتحليل الأخير:"
    if is_ar
    else "📋 Latest Meal Report:",
    "history_header": "📋 سجل الوجبات المسجلة اليوم"
    if is_ar
    else "📋 Today's Meal History",
}

# ---------------------------------------------------------
# Sidebar Elements
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.header(t["api_header"])

    raw_api_key = (
        st.secrets.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or ""
    )

    user_key_input = st.text_input(
        t["api_key_label"],
        value=raw_api_key,
        type="password",
    )
    api_key = user_key_input.strip() if user_key_input else ""

    selected_model = st.selectbox(
        t["select_model"],
        [
            "google/gemini-2.0-flash-001",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
        ],
        index=0,
    )

    st.markdown("---")
    st.header(t["fasting_header"])
    fasting_plan = st.selectbox(t["fasting_plan"], [12, 14, 16, 18, 20])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        if st.button(t["start_fast"], use_container_width=True):
            st.session_state.fast_start_time = datetime.now()
            st.success("Started!" if not is_ar else "تم بدء الصيام!")

    with col_f2:
        if st.button(t["end_fast"], use_container_width=True):
            st.session_state.fast_start_time = None
            st.warning("Ended." if not is_ar else "تم إنهاء الصيام.")

    st.markdown("---")
    if st.button(t["reset_day"], use_container_width=True):
        st.session_state.meals_history = []
        st.session_state.latest_analysis = None
        st.session_state.medical_report_analysis = None
        st.session_state.profile_calculated = False
        st.success("Cleared!" if not is_ar else "تم مسح البيانات والسجل!")

# ---------------------------------------------------------
# Main UI Header
# ---------------------------------------------------------
st.markdown(f'<div class="main-title">{t["title"]}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">{t["subtitle"]}</div>', unsafe_allow_html=True
)


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def optimize_image(img, max_size=900):
    img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return img


def encode_image_to_base64(pil_img):
    buffered = io.BytesIO()
    pil_img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def calculate_bmr(weight, height, age, gender_val):
    is_male = gender_val in ["ذكر", "Male"]
    if is_male:
        return int(10 * weight + 6.25 * height - 5 * age + 5)
    else:
        return int(10 * weight + 6.25 * height - 5 * age - 161)


# ---------------------------------------------------------
# 4. Profile Inputs & Calculation Trigger
# ---------------------------------------------------------
st.markdown(f"### {t['profile_header']}")

with st.expander("📝 اضغط هنا لإدخال بياناتك وضبط السعرات", expanded=True):
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)

    with col_p1:
        age = st.number_input(t["age"], min_value=10, max_value=100, value=30)
    with col_p2:
        gender = st.selectbox(t["gender"], t["gender_opts"])
    with col_p3:
        weight = st.number_input(
            t["weight"], min_value=30.0, max_value=250.0, value=75.0, step=0.5
        )
    with col_p4:
        height = st.number_input(
            t["height"], min_value=100.0, max_value=230.0, value=175.0, step=0.5
        )

    col_p5, col_p6 = st.columns(2)
    with col_p5:
        activity_level = st.selectbox(t["activity"], t["activity_opts"])
    with col_p6:
        medical_conditions = st.multiselect(
            t["conditions"], t["conditions_opts"]
        )

    st.markdown("---")
    st.markdown(f"##### {t['upload_report']}")
    uploaded_report = st.file_uploader(
        "Upload Medical Report / ارفع صورة التقرير الطبي:",
        type=["jpg", "jpeg", "png"],
        key="medical_report",
    )

    # زر إرسال البيانات ومعالجتها
    if st.button(t["btn_calc_profile"], type="primary"):
        # حساب السعرات
        base_bmr = calculate_bmr(weight, height, age, gender)
        act_index = t["activity_opts"].index(activity_level)
        multipliers = [1.2, 1.375, 1.55, 1.725]
        calculated_tdee = int(base_bmr * multipliers[act_index])

        st.session_state.user_bmr = base_bmr
        st.session_state.user_tdee = calculated_tdee
        st.session_state.profile_calculated = True

        # إذا قام المستخدم برفع تقرير طبي يتم تحليله عبر API
        if uploaded_report is not None:
            if not api_key:
                st.warning(
                    "⚠️ تم حساب السعرات! (لتحليل التقرير الطبي المرفق يرجى"
                    " أدخال API Key في القائمة الجانبية)."
                )
            else:
                with st.spinner("جاري تحليل التقرير الطبي وتوليد التوصيات... ⚡"):
                    try:
                        rep_img = Image.open(uploaded_report)
                        opt_rep = optimize_image(rep_img)
                        b64_rep = encode_image_to_base64(opt_rep)

                        lang_instruction = (
                            "أجب باللغة العربية حصراً وبصيغة من اليمين إلى"
                            " اليسار."
                            if is_ar
                            else "Respond strictly in English in LTR format."
                        )

                        report_prompt = f"""
                        [Instruction: {lang_instruction}]
                        You are a clinical nutritionist and medical expert.
                        Patient Details: Age {age}, Gender {gender}, Weight {weight}kg, Height {height}cm.
                        Conditions: {', '.join(medical_conditions) if medical_conditions else 'None'}.
                        Calculated Target Calories: {calculated_tdee} Kcal.

                        Analyze the attached medical report image and detail:
                        1. **Medical Summary & Biomarkers.**
                        2. **Expected Body Fat Distribution** (Visceral vs Subcutaneous fat).
                        3. **Caloric & Macro Plan.**
                        4. **Strict Allowed & Prohibited Foods.**
                        """

                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "HTTP-Referer": "https://streamlit.io",
                            "X-Title": "Medical Guard",
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
                                            "url": (
                                                "data:image/jpeg;base64,"
                                                f"{b64_rep}"
                                            )
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
                            st.session_state.medical_report_analysis = (
                                res.json()["choices"][0]["message"]["content"]
                            )
                    except Exception as e:
                        st.error(f"Error analyzing report: {e}")

        st.success(
            "✅ تم حساب السعرات الموصى بها بنجاح وتحديث الميزانية!"
            if is_ar
            else "✅ Recommended calories successfully calculated!"
        )

# عرض التقرير الطبي المترجم إذا توفر
if st.session_state.medical_report_analysis:
    st.info(st.session_state.medical_report_analysis)

st.markdown("---")

# ---------------------------------------------------------
# 5. Dashboard Metrics (تظهر فقط بعد إدخال البيانات والضغط على الزر)
# ---------------------------------------------------------
if not st.session_state.profile_calculated:
    st.warning(
        "👈 يرجى إدخال بياناتك (الوزن، الطول، العمر) ثم الضغط على زر [تحليل"
        " البيانات وحساب السعرات المناسبة] لعرض الميزانية اليومية للوجبات."
        if is_ar
        else "👈 Please enter your details above and click [Calculate Recommended"
        " Calories] to display your daily budget."
    )
else:
    daily_target = st.session_state.user_tdee
    base_bmr = st.session_state.user_bmr
    consumed_calories = sum(
        meal["calories"] for meal in st.session_state.meals_history
    )
    remaining_calories = daily_target - consumed_calories

    st.markdown(f"### {t['dashboard_header']}")
    metric_c1, metric_c2, metric_c3, metric_c4 = st.columns(4)

    metric_c1.metric(t["bmr"], f"{base_bmr} Kcal")
    metric_c2.metric(t["target"], f"{daily_target} Kcal")
    metric_c3.metric(t["consumed"], f"{consumed_calories} Kcal")

    if remaining_calories >= 0:
        metric_c4.metric(
            t["remaining"],
            f"{remaining_calories} Kcal",
            delta=f"{remaining_calories} Kcal",
        )
    else:
        metric_c4.metric(
            t["over_limit"],
            f"{abs(remaining_calories)} Kcal",
            delta=f"-{abs(remaining_calories)} Kcal",
            delta_color="inverse",
        )

    if st.session_state.fast_start_time:
        elapsed_time = datetime.now() - st.session_state.fast_start_time
        required_hours = timedelta(hours=fasting_plan)

        if elapsed_time < required_hours:
            remaining_time = required_hours - elapsed_time
            hours, remainder = divmod(
                int(remaining_time.total_seconds()), 3600
            )
            minutes, seconds = divmod(remainder, 60)
            st.warning(
                f"⏳ فترة الصيام المتقطع نشطة ({fasting_plan} ساعة). المتبقي:"
                f" {hours:02d}:{minutes:02d}:{seconds:02d}"
                if is_ar
                else f"⏳ Fasting Active ({fasting_plan}h). Remaining:"
                f" {hours:02d}:{minutes:02d}:{seconds:02d}"
            )
        else:
            st.success(
                "🎉 انتهت فترة الصيام المتقطع!"
                if is_ar
                else "🎉 Fasting Period Complete!"
            )

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. AI Meal Vision Scanner
    # ---------------------------------------------------------
    st.markdown(f"### {t['meal_header']}")

    input_method = st.radio(
        t["input_method"], t["source_opts"], horizontal=True
    )

    uploaded_meal_img = None
    if input_method == t["source_opts"][0]:
        uploaded_meal_img = st.camera_input("Capture meal / التقط صورة:")
    else:
        uploaded_meal_img = st.file_uploader(
            "Upload image / اختر صورة:",
            type=["jpg", "jpeg", "png"],
            key="meal_upload",
        )

    if uploaded_meal_img is not None:
        raw_img = Image.open(uploaded_meal_img)
        opt_meal_img = optimize_image(raw_img)

        if input_method == t["source_opts"][1]:
            st.image(opt_meal_img, caption="Meal Image", width=350)

        meal_custom_name = st.text_input(
            t["meal_name"], value="وجبة مسجلة" if is_ar else "Recorded Meal"
        )

        if st.button(t["btn_analyze_meal"], type="primary"):
            if not api_key:
                st.error("API Key Required!")
            else:
                with st.spinner("Analyzing Food... ⚡"):
                    try:
                        b64_meal = encode_image_to_base64(opt_meal_img)
                        meal_data_url = f"data:image/jpeg;base64,{b64_meal}"

                        lang_prompt_instruction = (
                            "أكتب التقرير والتحليل باللغة العربية حصراً وبصيغة"
                            " RTL"
                            if is_ar
                            else "Write the report in English in LTR layout."
                        )

                        meal_prompt = f"""
                        [Req_ID: {time.time()}]
                        [Instruction: {lang_prompt_instruction}]
                        You are a clinical nutrition expert.
                        Examine the food/beverage image closely:
                        - If the image contains pure water or zero-calorie beverage, set estimated calories strictly to 0 Kcal.
                        - Format the output EXACTLY as follows:

                        الإجمالي التقديري للسعرات: [x] سعرة  (or for English: Estimated Total Calories: [x] Kcal)

                        1. **{"المكونات والسعرات" if is_ar else "Ingredients & Calories"}:** (Detailed itemized list).
                        2. **{"القيم الغذائية" if is_ar else "Nutritional Values"}:** (Protein / Carbs / Fats in grams).
                        3. **{"التأثير الصحي والملاءمة" if is_ar else "Health Impact & Suitability"}:** (Compatibility with user profile).
                        4. **{"النقد الصارم والحكم النهائي" if is_ar else "Strict Verdict & Advice"}:** (Direct 3-line expert guidance).
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
                                r"(?:الإجمالي التقديري للسعرات|Estimated Total"
                                r" Calories):\s*(\d+)",
                                analysis_text,
                                re.IGNORECASE,
                            )
                            if not cal_match:
                                cal_match = re.search(
                                    r"(\d+)\s*(?:سعرة|Kcal)",
                                    analysis_text,
                                    re.IGNORECASE,
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
                            st.success(
                                "✅ تم تحليل الوجبة بنجاح!"
                                if is_ar
                                else "✅ Success!"
                            )
                        else:
                            st.error(
                                f"API Error ({response.status_code}):"
                                f" {response.text}"
                            )

                    except Exception as e:
                        st.error(f"Processing Error: {e}")

    if st.session_state.latest_analysis:
        st.markdown(f"#### {t['latest_report_title']}")
        st.info(st.session_state.latest_analysis)

    # ---------------------------------------------------------
    # 7. Today's Meal History Log
    # ---------------------------------------------------------
    if st.session_state.meals_history:
        st.markdown("---")
        st.markdown(f"### {t['history_header']}")
        for idx, meal in enumerate(
            reversed(st.session_state.meals_history), 1
        ):
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
