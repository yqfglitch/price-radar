import streamlit as st
import google.generativeai as genai
import requests
import json
import time

# ==========================================
# 🎨 页面基础配置与高级 CSS 样式 (必须放在最前面)
# ==========================================
st.set_page_config(page_title="Global Pricing Radar", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    /* 引入高级无衬线字体，减轻字重，缩小默认字号提升优雅感 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=Noto+Sans+JP:wght@300;400&family=Noto+Sans+SC:wght@300;400&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans SC', 'Noto Sans JP', sans-serif !important;
        font-weight: 300;
    }
    h1, h2, h3 {
        font-weight: 400 !important;
        letter-spacing: 0.5px;
    }
    p, li, .stMarkdown {
        font-size: 15px !important;
        line-height: 1.6 !important;
    }
    /* 优化密码框和输入框的视觉 */
    .stTextInput input {
        font-weight: 300;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🌐 全局多语言字典 (i18n)
# ==========================================
lang_choice = st.sidebar.radio("🌐 Select Language", ["English", "中文", "日本語"], index=0)

UI = {
    "English": {
        "lock_title": "🔒 Access Restricted",
        "lock_sub": "This is a private pricing radar. Please enter the password to access.",
        "lock_pwd": "🔑 Password:",
        "lock_btn": "Unlock",
        "lock_err": "❌ Incorrect password!",
        "title": "🔍 Global Visual Pricing Radar",
        "sub": "Upload an image, and our AI will provide calculated pricing using **Live Global Exchange Rates**.",
        "col1_h": "1. Item Info",
        "cond": "🏷️ Select Item Condition",
        "cond_opts": ["Vintage", "Antique", "New", "Used"],
        "up": "📸 Drag & Drop Image",
        "cap": "Image to analyze",
        "col2_h": "2. AI Pricing Report",
        "btn": "🚀 Start Global Radar Scan",
        "s1": "Step 1/3: Uploading image...",
        "s2": "Step 2/3: Google Lens scanning...",
        "s3": "Step 3/3: AI calculating with live exchange rates...",
        "done": "✅ Analysis Complete!",
        "fail_img": "⚠️ No highly matched results found. Please try a clearer image.",
        "wait": "👈 Please upload an image on the left to start."
    },
    "中文": {
        "lock_title": "🔒 访问受限",
        "lock_sub": "这是私人专属的比价雷达，需要输入密码才能使用。",
        "lock_pwd": "🔑 专属密码：",
        "lock_btn": "解锁",
        "lock_err": "❌ 密码错误！",
        "title": "🔍 全球视觉比价雷达",
        "sub": "上传一张商品图片，AI 将结合**实时全球汇率**进行精准比价及进货建议。",
        "col1_h": "1. 货品信息",
        "cond": "🏷️ 货品属性",
        "cond_opts": ["中古 (Vintage)", "古董 (Antique)", "全新 (New)", "二手 (Used)"],
        "up": "📸 拖拽或上传图片",
        "cap": "待分析图片",
        "col2_h": "2. AI 极速分析报告",
        "btn": "🚀 启动全球雷达扫描",
        "s1": "步骤 1/3: 正在安全上传图片...",
        "s2": "步骤 2/3: Google Lens 全网深度检索中...",
        "s3": "步骤 3/3: AI 接入实时汇率并精算定价...",
        "done": "✅ 报告生成完毕！",
        "fail_img": "⚠️ 未能匹配到足够的数据，请更换更清晰的图片。",
        "wait": "👈 请先在左侧上传需要分析的商品图片。"
    },
    "日本語": {
        "lock_title": "🔒 アクセス制限",
        "lock_sub": "これはプライベートな価格比較レーダーです。パスワードを入力してください。",
        "lock_pwd": "🔑 パスワード：",
        "lock_btn": "ロック解除",
        "lock_err": "❌ パスワードが間違っています！",
        "title": "🔍 グローバル視覚価格レーダー",
        "sub": "画像をアップロードすると、AIが**リアルタイムの為替レート**を使用して価格を分析します。",
        "col1_h": "1. 商品情報",
        "cond": "🏷️ 商品の状態",
        "cond_opts": ["ヴィンテージ (Vintage)", "アンティーク (Antique)", "新品 (New)", "中古 (Used)"],
        "up": "📸 画像をドラッグ＆ドロップ",
        "cap": "解析する画像",
        "col2_h": "2. AI 分析レポート",
        "btn": "🚀 グローバルスキャンを開始",
        "s1": "ステップ 1/3: 画像をアップロード中...",
        "s2": "ステップ 2/3: Google Lensでスキャン中...",
        "s3": "ステップ 3/3: AIが為替レートを計算中...",
        "done": "✅ 分析完了！",
        "fail_img": "⚠️ 一致する結果が見つかりませんでした。別の画像でお試しください。",
        "wait": "👈 左側で画像をアップロードして分析を開始してください。"
    }
}

t = UI[lang_choice] # 简写变量，方便调用当前语言字典

# ==========================================
# 🔒 专属密码保护拦截 
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title(t["lock_title"])
    st.markdown(t["lock_sub"])
    
    password = st.text_input(t["lock_pwd"], type="password")
    
    if st.button(t["lock_btn"]):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state["logged_in"] = True
            st.rerun() 
        else:
            st.error(t["lock_err"])
    st.stop()

# ==========================================
# 🔑 API 配置
# ==========================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY.strip())

# ==========================================
# 🌐 核心功能函数
# ==========================================
@st.cache_data(ttl=3600) 
def fetch_live_exchange_rates():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10).json()
        return res.get("rates", {})
    except Exception as e:
        return {}

def upload_to_imgbb(image_bytes):
    try:
        url = "https://api.imgbb.com/1/upload"
        res = requests.post(url, params={"key": IMGBB_API_KEY}, files={"image": image_bytes}, timeout=15).json()
        return res.get('data', {}).get('url')
    except Exception:
        return None

def fetch_detailed_comparison_data(image_url):
    params = {"engine": "google_lens", "url": image_url, "api_key": SERPAPI_KEY}
    try:
        res = requests.get("https://serpapi.com/search.json", params=params, timeout=20).json()
        visual_matches = res.get("visual_matches", [])
        comparison_list = []
        for item in visual_matches:
            price_info = item.get("price", {})
            link = item.get("link", "")
            source = item.get("source", "Unknown Shop")
            
            is_us = True
            if any(ext in link for ext in [".jp", ".co.jp", ".de", ".uk", ".fr", "mercari.com/jp", "yahoo.co.jp"]):
                is_us = False
            elif "ebay.com" in link or "etsy.com" in link:
                is_us = True
                
            entry = {
                "title": item.get("title", "No Title"),
                "source": source,
                "price": price_info.get("extracted_value", "N/A"),
                "currency": price_info.get("currency", "$"),
                "link": link,
                "is_us_region": is_us
            }
            if entry["price"] != "N/A":
                comparison_list.append(entry)
        return comparison_list[:15]
    except Exception:
        return []

def generate_comparison_report(raw_matches, category, rates, lang):
    model = genai.GenerativeModel('gemini-3-flash-preview')
    data_context = json.dumps(raw_matches, indent=2)
    
    jpy_rate = rates.get("JPY", 150.0)
    eur_rate = rates.get("EUR", 0.92)
    gbp_rate = rates.get("GBP", 0.78)
    cny_rate = rates.get("CNY", 7.2)
    
    prompt = f"""
    Role: Senior E-commerce Pricing Analyst.
    Task: Compare prices for an item declared as: *** {category} ***.

    [DATA]: {data_context}
    
    [LIVE EXCHANGE RATES (1 USD equals)]:
    JPY: {jpy_rate}, EUR: {eur_rate}, GBP: {gbp_rate}, CNY: {cny_rate}

    [STRICT RULES]:
    1. Filter results that best match the "{category}" attribute.
    2. Group results into US Local and Global Matches.
    3. Pick the SINGLE most cost-effective/available link for US, and one for Global.
    4. EVALUATE VALUE IN USD: For foreign prices, use the LIVE EXCHANGE RATES to calculate their exact USD value before comparing deals.
    5. CURRENCY DISPLAY FORMAT: Display original foreign price, followed by its converted USD amount. Example: "¥15,000 (~$100.00 USD)".
    6. OUTPUT LANGUAGE: You MUST generate the entire response/report in {lang}. Do not use bilingual output.

    [REPORT STRUCTURE]:
    # 📊 Global Visual Pricing Radar Report 
    
    ## 🇺🇸 US Local Matches
    [List items]
    **🛒 Best Deal Link**: [Link + 1 sentence reason]
    
    ## 🌍 Global Matches
    [List items... Format: Original Price (~$Converted USD)]
    **🛒 Best Global Deal Link**: [Link + 1 sentence reason]
    
    ## 📦 International Shipping Est.
    [List est. shipping cost to US (1lb/3lb/5lb)]
    
    ## 💡 Expert Summary
    [Explain price factors and market condition]

    ## 📍 Pricing Suggestion
    [Final suggested listing price range in USD]
    """
    
    for attempt in range(3):
        try:
            return model.generate_content(prompt).text
        except Exception as e:
            if any(err in str(e) for err in ["429", "Quota", "504"]):
                time.sleep((attempt + 1) * 5)
            else:
                return f"❌ Error: {e}"
    return "❌ Timeout or Rate limit exceeded. Please try again."

# ==========================================
# 🎨 Web 页面构建 
# ==========================================
st.title(t["title"])
st.markdown(t["sub"])

col1, col2 = st.columns([1, 2])

with col1:
    st.header(t["col1_h"])
    selected_category = st.selectbox(t["cond"], t["cond_opts"])
    uploaded_file = st.file_uploader(t["up"], type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption=t["cap"], use_column_width=True)

with col2:
    st.header(t["col2_h"])
    if uploaded_file is not None:
        if st.button(t["btn"], use_container_width=True):
            live_rates = fetch_live_exchange_rates()
            
            with st.spinner(t["s1"]):
                img_url = upload_to_imgbb(uploaded_file.getvalue())
                
            if img_url:
                with st.spinner(t["s2"]):
                    matches = fetch_detailed_comparison_data(img_url)
                    
                if matches:
                    with st.spinner(t["s3"]):
                        # 动态传入当前选择的语言给 AI
                        report = generate_comparison_report(matches, selected_category, live_rates, lang_choice)
                        st.success(t["done"])
                        st.markdown(report)
                else:
                    st.warning(t["fail_img"])
    else:
        st.info(t["wait"])