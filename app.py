import os
import streamlit as st
import google.generativeai as genai
import google.ai.generativelanguage as glm

# APIキーを環境変数から読み込む
api_key = os.environ.get("GENERATIVEAI_API_KEY")

# APIキー設定
genai.configure(api_key=api_key)

# タイトルを設定する
st.set_page_config(
    page_title="Chat with Gemini 1.5Pro",
    page_icon="🤖",
    layout="wide" # レスポンシブデザインのためのレイアウト設定
)
st.title("🤖 Chat with Gemini 1.5Pro")

# セーフティ設定
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    }
]

# セッション状態の初期化
if "chat_session" not in st.session_state:
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    st.session_state["chat_session"] = model.start_chat(history=[
        glm.Content(role="user", parts=[glm.Part(text="あなたは優秀なAIアシスタントです。どのような話題も適切に詳細に答えます。時々偉人や哲学者の名言を日本語で引用してください。")]),
        glm.Content(role="model", parts=[glm.Part(text="わかりました。")])
    ])
    st.session_state["chat_history"] = []

# チャット履歴を全て表示
for message in st.session_state["chat_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザー入力送信後処理
if prompt := st.chat_input("ここに入力してください"):
    # ユーザの入力を表示する
    with st.chat_message("user"):
        st.markdown(prompt)

    # ユーザの入力をチャット履歴に追加する
    st.session_state["chat_history"].append({"role": "user", "content": prompt})

    try:
        # Genimi Proにメッセージ送信（ストリーミング）
        response = st.session_state["chat_session"].send_message(
            prompt, 
            stream=True, 
            timeout=None  # timeoutをNoneに設定し、無制限にする
        )

        # Genimi Proのレスポンスを表示（ストリーミング）
        with st.chat_message("assistant"):
            response_text_placeholder = st.empty()
            full_response_text = ""
            for chunk in response:
                full_response_text += chunk.text
                response_text_placeholder.markdown(full_response_text)

        # 最終的なレスポンステキストを表示
        response_text_placeholder.markdown(full_response_text)

        # Genimi Proのレスポンスをチャット履歴に追加する
        st.session_state["chat_history"].append({"role": "assistant", "content": full_response_text})

    except Exception as e:
        # エラーをキャッチし、エラーメッセージを表示
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
                return 'Error', 500
        except Exception as e:
            # その他の例外が発生した場合のエラーハンドリング
            return str(e), 500
        # 正常終了時のレスポンスを返す
        return 'OK', 200

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
