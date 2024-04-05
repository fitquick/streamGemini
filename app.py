import os
import streamlit as st
import google.generativeai as genai
import google.ai.generativelanguage as glm

# API キーの読み込み
api_key = os.environ.get("GENERATIVEAI_API_KEY")
genai.configure(api_key=api_key)

# ページ設定
st.set_page_config(
    page_title="Chat with Gemini 1.5Pro",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Chat with Gemini 1.5Pro")

# 安全設定
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# セッション状態の初期化
if "chat_session" not in st.session_state:
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    st.session_state["chat_session"] = model.start_chat(
        history=[
            glm.Content(
                role="user",
                parts=[
                    glm.Part(
                        text="あなたは優秀なAIアシスタントです。どのような話題も適切に詳細に答えます。時々偉人や哲学者の名言を日本語で引用してください。"
                    )
                ],
            ),
            glm.Content(role="model", parts=[glm.Part(text="わかりました。")]),
        ]
    )
    st.session_state["chat_history"] = []

# チャット履歴の表示
for message in st.session_state["chat_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザー入力の処理
if prompt := st.chat_input("ここに入力してください"):
    # ユーザーの入力を表示
    with st.chat_message("user"):
        st.markdown(prompt)

    # ユーザーの入力をチャット履歴に追加
    st.session_state["chat_history"].append({"role": "user", "content": prompt})

    # Gemini Pro にメッセージ送信 (ストリーミング)
    try:
        # ログを記録
        logger.log_text(f"Sending message to Gemini 1.5 Pro: {prompt}", severity="INFO")
        
        response = st.session_state["chat_session"].send_message(
            prompt, stream=True, timeout=300, safety_settings=safety_settings
        )
        
        # ログを記録
        logger.log_text(f"Received response from Gemini 1.5 Pro", severity="INFO")
        
        # Gemini Pro のレスポンスを表示 (ストリーミング)
        with st.chat_message("assistant"):
            response_text_placeholder = st.empty()
            full_response_text = ""
            for chunk in response:
                if chunk.text:
                    full_response_text += chunk.text
                    response_text_placeholder.markdown(full_response_text)
                    # チャンクをログに記録
                    logger.log_text(f"Received chunk: {chunk.text}", severity="INFO")
                elif chunk.finish_reason == "safety_ratings":
                    # 安全性チェックでブロックされた場合
                    full_response_text += "現在アクセスが集中しております。しばらくしてから再度お試しください。"
                    logger.log_text(f"Blocked by safety check", severity="WARNING")
                    break

            # 最終的なレスポンスを表示
            response_text_placeholder.markdown(full_response_text)

        # Gemini Pro のレスポンスをチャット履歴に追加
        st.session_state["chat_history"].append(
            {"role": "assistant", "content": full_response_text}
        )

    except Exception as e:
        # エラー発生時もユーザーフレンドリーなメッセージを返す
        st.session_state["chat_history"].append(
            {"role": "assistant", "content": "現在アクセスが集中しております。しばらくしてから再度お試しください。"}
        )
        # エラーの詳細をログに記録する
        logger.log_text(f"Error occurred: {str(e)}", severity="ERROR")
        st.error(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    from streamlit.web.cli import main
    from flask import Flask

    app = Flask(__name__)

    @app.route("/")
    def index():
        # Streamlitアプリケーションを実行する
        try:
            main()
        except SystemExit as e:
            if e.code != 0:
                return "Error", 500
        except Exception as e:
            # その他の例外が発生した場合のエラーハンドリング
            return str(e), 500

        # 正常終了時のレスポンスを返す
        return "OK", 200

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
