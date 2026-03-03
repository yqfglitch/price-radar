import streamlit as st
import google.generativeai as genai
import requests
import json
import time

# ==========================================
# 🔒 专属密码保护拦截 (防白嫖机制 / Anti-freeloader lock)
# ==========================================
# 检查 session 状态 / Check session state
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# 如果没有登录，则显示密码输入框 / Show password input if not logged in
if not st.session_state["logged_in"]:
    st.title("🔒 访问受限 / Access Restricted")
    st.markdown("这是私人专属的比价雷达，需要输入密码才能使用。 \n\n*This is a private pricing radar. Please enter the password to access.*")
    
    password = st.text_input("🔑 请输入专属访问密码 / Please enter the access password:", type="password")
    
    if st.button("解锁进入 / Unlock"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state["logged_in"] = True
            st.rerun() 
        else:
            st.error("❌ 密码错误，拒绝访问！ / Incorrect password, access denied!")
            
    st.stop()

# ==========================================
# 🔑 API 配置 (使用 Streamlit Secrets 保护隐私)
# ==========================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY.strip())

# ==========================================
# 🌐 核心功能函数 / Core Functions
# ==========================================
def upload_to_imgbb(image_bytes):
    try:
        url = "https://api.imgbb.com/1/upload"
        res = requests.post(url, params={"key": IMGBB_API_KEY}, files={"image": image_bytes}, timeout=15).json()
        return res.get('data', {}).get('url')
    except Exception as e:
        st.error(f"图床上传失败 / Image upload failed: {e}")
        return None

def fetch_detailed_comparison_data(image_url):
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": SERPAPI_KEY
    }
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
    except Exception as e:
        st.error(f"搜索失败 / Search failed: {e}")
    return []

def generate_comparison_report(raw_matches, category):
    model = genai.GenerativeModel('gemini-1.5-flash')
    data_context = json.dumps(raw_matches, indent=2)
    
    # 🌟 修改了 Prompt，强制 AI 输出中英双语报告
    prompt = f"""
    Role: Senior E-commerce Pricing Analyst.
    Current Task: Compare prices for an item declared as: *** {category} ***.

    [DATA]: {data_context}

    [STRICT RULES]:
    1. Filter results that best match the "{category}" attribute.
    2. Group results clearly into US Local and Global Matches.
    3. You MUST pick the SINGLE most cost-effective/available link for US, and one for Global. Provide the direct URL.
    4. Separate the Expert Summary and the final Pricing Suggestion into two distinct sections.

    [REPORT FORMAT - BILINGUAL (CHINESE & ENGLISH)]:
    # 📊 全球视觉比价雷达报告 / Global Visual Pricing Radar Report 
    **(属性/Condition: {category})**
    
    ## 🇺🇸 美国本土参考 / US Local Matches
    [List...]
    **🛒 最划算推荐 / Best Deal Link**: [Provide direct link and 1 sentence reason in both EN & CN]
    
    ## 🌍 全球境外参考 / Global Matches
    [List...]
    **🛒 境外最划算推荐 / Best Global Deal Link**: [Provide direct link and 1 sentence reason in both EN & CN]
    
    ## 📦 跨境物流提示 / International Shipping Est.
    [List estimated international shipping cost (1lb/3lb/5lb), remind users to add this to the global price. Both EN & CN.]
    
    ## 💡 专家比价总结 / Expert Summary
    [Explain price driving factors and market supply/demand based on the {category} attribute. Both EN & CN.]

    ## 📍 核心定价建议 / Pricing Suggestion
    [Provide a final highly visible suggested listing price range considering shipping, condition, and sourcing. Both EN & CN.]
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if any(err in error_msg for err in ["429", "Quota", "504", "Deadline"]):
                wait_time = (attempt + 1) * 5 
                time.sleep(wait_time)
            else:
                return f"❌ 报告生成失败 / Report generation failed: {e}"
    return "❌ 报告生成失败: 连续多次触发限流或超时，请稍后再试。 / Generation failed due to rate limits or timeouts. Please try again later."

# ==========================================
# 🎨 Web 页面构建 / Streamlit UI
# ==========================================
st.set_page_config(page_title="Global Pricing Radar", page_icon="🔍", layout="wide")

st.title("🔍 全球视觉比价雷达 / Global Visual Pricing Radar")
st.markdown("上传一张古董或二手商品的图片，AI 将通过 Google Lens 扫描全球全网，为您提供精算的定价和进货建议。 \n\n*Upload an image of a vintage or used item, and our AI will scan the global web via Google Lens to provide calculated pricing and sourcing suggestions.*")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. 输入商品信息 / Item Info")
    selected_category = st.selectbox(
        "🏷️ 请选择货品属性 / Select Item Condition",
        ["Vintage (中古/年代物)", "Antique (古董/百年以上)", "New (全新)", "Used (普通二手)"]
    )
    
    uploaded_file = st.file_uploader("📸 拖拽或选择上传图片 / Drag & Drop or Browse Image", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="待查商品图片 / Image to analyze", use_column_width=True)

with col2:
    st.header("2. AI 分析报告 / AI Pricing Report")
    
    if uploaded_file is not None:
        if st.button("🚀 启动全网雷达扫描 / Start Global Radar Scan", use_container_width=True):
            
            with st.spinner('步骤 1/3: 正在将图片上传至服务器... / Step 1/3: Uploading image to server...'):
                img_bytes = uploaded_file.getvalue()
                img_url = upload_to_imgbb(img_bytes)
                
            if img_url:
                with st.spinner('步骤 2/3: Google Lens 正在进行全网比对... / Step 2/3: Google Lens is scanning the web...'):
                    matches = fetch_detailed_comparison_data(img_url)
                    
                if matches:
                    with st.spinner('步骤 3/3: AI 正在构建定价模型... / Step 3/3: AI is building the pricing model...'):
                        report = generate_comparison_report(matches, selected_category)
                        st.success("✅ 分析完成！ / Analysis Complete!")
                        st.markdown(report)
                else:
                    st.warning("⚠️ 未能找到高度匹配的结果，请尝试更清晰的图片。 / No highly matched results found. Please try a clearer image.")
    else:
        st.info("👈 请先在左侧上传商品图片以启动分析。 / Please upload an image on the left to start the analysis.")