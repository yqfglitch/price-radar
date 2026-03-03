import streamlit as st
import google.generativeai as genai
import requests
import json
import time

# ==========================================
# 🔑 API 配置 (使用 Streamlit Secrets 保护隐私)
# ==========================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY.strip())

# ==========================================
# 🌐 核心功能函数
# ==========================================
def upload_to_imgbb(image_bytes):
    try:
        url = "https://api.imgbb.com/1/upload"
        res = requests.post(url, params={"key": IMGBB_API_KEY}, files={"image": image_bytes}, timeout=15).json()
        return res.get('data', {}).get('url')
    except Exception as e:
        st.error(f"图床上传失败: {e}")
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
        st.error(f"搜索失败: {e}")
    return []

def generate_comparison_report(raw_matches, category):
    # 使用稳健的 1.5-flash 模型
    model = genai.GenerativeModel('gemini-1.5-flash')
    data_context = json.dumps(raw_matches, indent=2)
    
    prompt = f"""
    Role: Senior E-commerce Pricing Analyst.
    Current Task: Compare prices for an item declared as: *** {category} ***.

    [DATA]: {data_context}

    [STRICT RULES]:
    1. Filter results that best match the "{category}" attribute.
    2. Group results clearly into US Local and Global Matches.
    3. You MUST pick the SINGLE most cost-effective/available link for US, and one for Global. Provide the direct URL.
    4. Separate the Expert Summary and the final Pricing Suggestion into two distinct sections.

    [REPORT FORMAT - CHINESE]:
    # 📊 全球视觉比价雷达报告 (属性: {category})
    
    ## 🇺🇸 美国本土参考 (US Local Matches)
    [列表...]
    **🛒 本土最划算/推荐购买链接**: [提供具体的 Link 和一句推荐理由]
    
    ## 🌍 全球/境外参考 (Global Matches)
    [列表...]
    **🛒 境外最划算/推荐购买链接**: [提供具体的 Link 和一句推荐理由]
    
    ## 📦 跨境物流增值成本提示 (针对境外货源)
    [列出 1lb / 3lb / 5lb 的估算国际运费，提醒用户将此加到境外购买价上]
    
    ## 💡 专家比价总结
    [说明由于是 {category} 属性，价格受哪些因素影响最大，以及当前市场的供需情况]

    ## 📍 核心定价建议 (Pricing Suggestion)
    [结合物流、品相、货源，给出你的最终上架定价建议区间，要醒目]
    """
    
    # 🌟 优化点：指数退避重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if any(err in error_msg for err in ["429", "Quota", "504", "Deadline"]):
                wait_time = (attempt + 1) * 5 # 递增等待：5秒, 10秒, 15秒
                time.sleep(wait_time)
            else:
                return f"❌ 报告生成失败: {e}"
    return "❌ 报告生成失败: 连续多次触发限流或超时，请稍后再试。"

# ==========================================
# 🎨 Web 页面构建 (Streamlit UI)
# ==========================================
st.set_page_config(page_title="全球比价雷达", page_icon="🔍", layout="wide")

st.title("🔍 全球视觉比价雷达")
st.markdown("上传一张古董或二手商品的图片，AI 将通过 Google Lens 扫描全球全网，为您提供精算的定价和进货建议。")

# 左右分栏布局
col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. 输入商品信息")
    # 下拉菜单选择属性
    selected_category = st.selectbox(
        "🏷️ 请选择货品属性",
        ["Vintage (中古/年代物)", "Antique (古董/百年以上)", "New (全新)", "Used (普通二手)"]
    )
    
    # 拖拽上传图片框
    uploaded_file = st.file_uploader("📸 拖拽或选择上传图片", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="待查商品图片", use_column_width=True)

with col2:
    st.header("2. AI 比价分析报告")
    
    if uploaded_file is not None:
        if st.button("🚀 启动全网雷达扫描", use_container_width=True):
            
            # 使用 spinner 显示加载进度
            with st.spinner('步骤 1/3: 正在将图片上传至视觉识别服务器...'):
                img_bytes = uploaded_file.getvalue()
                img_url = upload_to_imgbb(img_bytes)
                
            if img_url:
                with st.spinner('步骤 2/3: Google Lens 正在进行像素级全网比对...'):
                    matches = fetch_detailed_comparison_data(img_url)
                    
                if matches:
                    with st.spinner('步骤 3/3: AI 正在构建定价模型，挑选最佳购买链接...'):
                        report = generate_comparison_report(matches, selected_category)
                        st.success("✅ 分析完成！")
                        # 完美渲染 Markdown 报告
                        st.markdown(report)
                else:
                    st.warning("⚠️ 未能找到高度匹配的视觉结果，请尝试换一个角度更清晰的图片。")
    else:
        st.info("👈 请先在左侧上传商品图片以启动分析。")