# ===== ここから書き換え =====
import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import os

# ==========================================
# 設定エリア
# ==========================================
st.set_page_config(page_title="English Exam Generator", layout="wide")
st.title("📊 English Exam Generator")
st.caption("Created by [あなたの名前]") # ←ここにかっこいい名前を入れてもOK

# APIキーの取得（シークレット機能対応）
# サーバーにキーが設定されていればそれを使い、なければ入力欄を出す
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.sidebar.header("Settings")
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
# ===== ここまで書き換え =====

# ==========================================
# ロジックエリア
# ==========================================
if api_key:
    genai.configure(api_key=api_key)

    # --- モデル選択 ---
    st.sidebar.subheader("Model Selection")
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_names = [m.replace('models/', '') for m in models]
        model_names.sort()
        default_index = 0
        for i, name in enumerate(model_names):
            if "1.5-flash" in name:
                default_index = i
                break
        
        selected_model = st.sidebar.selectbox("Select Model", model_names, index=default_index)
        
        # JSONモード設定
        model = genai.GenerativeModel(
            selected_model,
            generation_config={"response_mime_type": "application/json"}
        )
    except Exception as e:
        st.sidebar.error(f"Error fetching models: {e}")
        model = genai.GenerativeModel('gemini-1.5-flash')
    # -----------------------

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Input Source")
        input_type = st.radio("Choose Input Type:", ["Text Paste", "PDF Upload"], horizontal=True)
        
        user_input_data = None
        input_mime_type = None

        if input_type == "Text Paste":
            source_text = st.text_area("Paste topic or text here:", height=300)
            if source_text:
                user_input_data = source_text
                input_mime_type = "text/plain"
        else:
            uploaded_file = st.file_uploader("Upload PDF file", type=['pdf'])
            if uploaded_file is not None:
                user_input_data = uploaded_file.getvalue()
                input_mime_type = "application/pdf"
                st.success(f"PDF Loaded: {uploaded_file.name}")

        generate_btn = st.button("Generate Long Exam", type="primary")

    with col2:
        st.subheader("2. Generated Exam")

        if "chart_quiz_data" not in st.session_state:
            st.session_state.chart_quiz_data = None

        if generate_btn and user_input_data:
            with st.spinner("Writing a long passage, creating data, and questions..."):
                try:
                    # ★修正ポイント：長文を指定し、設問数を増やす指示に変更
                    system_prompt = """
                    You are an expert English Exam Creator for the Japanese Common Test (Kyotsu Test).
                    Create a "Long Reading Comprehension with Chart Interpretation" problem.
                    
                    Your Task:
                    1. Analyze the input topic.
                    2. Create a FICTIONAL dataset related to the topic (for a graph).
                    3. **Write a substantial English reading passage (approx. 500-600 words)**.
                       - The level should be CEFR B1/B2 (Standard University Entrance Exam level).
                       - The passage MUST discuss the data shown in the chart.
                    4. Create **4 to 5 questions** that require reading BOTH the text and the graph.

                    [Output Format (JSON)]
                    You must output a single JSON object with this exact structure:
                    {
                        "title": "Title of the passage",
                        "passage": "Full English text content (make it long)...",
                        "chart_config": {
                            "type": "bar", 
                            "title": "Graph Title",
                            "x_label": "Category Name",
                            "y_label": "Value Name",
                            "data": {"Label A": 10, "Label B": 25, "Label C": 15}
                        },
                        "questions": [
                            {
                                "id": 1,
                                "text": "Question text...",
                                "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                                "answer": "Option 2",
                                "explanation": "Explanation in Japanese..."
                            },
                            {
                                "id": 2,
                                ...
                            }
                        ]
                    }
                    """

                    content_parts = [system_prompt]
                    if input_mime_type == "application/pdf":
                        content_parts.append({"mime_type": "application/pdf", "data": user_input_data})
                    else:
                        content_parts.append(f"\n[Input Topic/Text]\n{user_input_data}")

                    response = model.generate_content(content_parts)
                    st.session_state.chart_quiz_data = json.loads(response.text)

                except Exception as e:
                    st.error(f"Error: {e}")

        # --- 結果表示 ---
        data = st.session_state.chart_quiz_data
        
        if data:
            st.markdown(f"### {data.get('title', 'No Title')}")
            # 本文をスクロールできるようにするか、そのまま全表示
            st.write(data.get('passage', ''))
            
            st.markdown("---")
            # グラフ描画
            chart_info = data.get('chart_config', {})
            st.markdown(f"**Figure 1: {chart_info.get('title', 'Chart')}**")
            
            raw_data = chart_info.get('data', {})
            if raw_data:
                df = pd.DataFrame(list(raw_data.items()), columns=[chart_info.get('x_label', 'Category'), chart_info.get('y_label', 'Value')])
                df = df.set_index(chart_info.get('x_label', 'Category'))
                
                if chart_info.get('type') == 'line':
                    st.line_chart(df)
                else:
                    st.bar_chart(df)
            
            st.markdown("---")
            
            st.subheader("Questions")
            for q in data.get('questions', []):
                st.markdown(f"**Q{q['id']}. {q['text']}**")
                for opt in q['options']:
                    st.write(f"- {opt}")
                
                with st.expander(f"Show Answer Q{q['id']}"):
                    st.markdown(f"**正解:** {q['answer']}")
                    st.markdown(f"**解説:** {q['explanation']}")