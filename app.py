import os
import json
import streamlit as st
import streamlit_authenticator as stauth
import google.generativeai as genai
import google.ai.generativelanguage as glm
from google.generativeai.types import generation_types
import traceback
import time

# ページ設定
st.set_page_config(
    page_title="Chat with Gemini 1.5Pro",
    page_icon="🤖",
    layout="wide",
)

# ユーザー情報を環境変数から読み込む
users = json.loads(os.environ["STREAMLIT_AUTHENTICATOR_USERS"])

# パスワードを抽出してハッシュ化
passwords = [user["password"] for user in users]
hashed_passwords = stauth.Hasher(passwords).generate()

# ハッシュ化されたパスワードでユーザー情報を更新
for i, user in enumerate(users):
    user["password"] = hashed_passwords[i]

# ユーザー情報をstreamlit_authenticatorの形式に変換
credentials = {
    "usernames": {
        user["email"]: {
            "name": user["name"],
            "email": user["email"],
            "password": user["password"]
        } for user in users
    }
}

authenticator = stauth.Authenticate(
    credentials,
    os.environ["STREAMLIT_AUTHENTICATOR_COOKIE_NAME"],
    os.environ["STREAMLIT_AUTHENTICATOR_SIGNATURE_KEY"],
    cookie_expiry_days=int(os.environ["STREAMLIT_AUTHENTICATOR_EXPIRY_DAYS"]),
)

name, authentication_status, username = authenticator.login(fields=None)

if authentication_status:
    # APIキーの読み込み
    api_key = os.environ.get("GENERATIVEAI_API_KEY")
    genai.configure(api_key=api_key)

    st.write(f'Welcome *{name}*')

    st.title("🤖 Chat with Gemini 1.5Pro")

    # 安全設定
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    ]

    # セッション状態の初期化
    if "chat_session" not in st.session_state:
        # モデル名を修正
        model = genai.GenerativeModel("gemini-exp-1121")
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
            ],
        )

    if "chat_history" not in st.session_state:
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

        # Gemini Proにメッセージ送信 (ストリーミング)
        try:
            response = st.session_state["chat_session"].send_message(
                prompt, stream=True, safety_settings=safety_settings
            )

            # タイムアウト設定 (45秒)
            start_time = time.time()
            timeout = 45

            # Gemini Proのレスポンスを表示 (ストリーミング) 
            with st.chat_message("assistant"):
                response_text_placeholder = st.empty()
                full_response_text = ""

                for chunk in response:
                    if hasattr(chunk, 'parts') and chunk.parts:
                        for part in chunk.parts:
                            full_response_text += part.text
                            response_text_placeholder.markdown(full_response_text)
                    elif chunk.finish_reason == "safety_censor":
                        # 安全性チェックでブロックされた場合
                        full_response_text += "申し訳ありませんが、このリクエストにはお応えできません。"
                        break
                    else:
                        # 他の終了理由の処理
                        pass

                    # タイムアウトチェック
                    if time.time() - start_time > timeout:
                        response.resolve()
                        break  # ループを中断

                # 最終的なレスポンスを表示
                response_text_placeholder.markdown(full_response_text)

                # チャット履歴にレスポンスを追加
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": full_response_text}
                )

        except generation_types.BrokenResponseError as e:
            # ストリーミングレスポンスが中断された場合、最後のレスポンスを履歴に追加
            if 'full_response_text' in locals():
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": full_response_text}
                )

            # 前回のレスポンスのイテレーションが完了していない場合、巻き戻す
            st.session_state["chat_session"].rewind()

        except Exception as e:
            # エラー発生時、ユーザーフレンドリーなメッセージを追加
            st.session_state["chat_history"].append(
                {"role": "assistant", "content": "申し訳ありません。エラーが発生しました。しばらくしてから再度お試しください。"}
            )
            # エラーの詳細をログに記録する
            error_details = traceback.format_exc()
            st.error(f"エラーが発生しました: {str(e)}\n\nエラー詳細:\n{error_details}")

    authenticator.logout("Logout", "sidebar")

elif authentication_status is False:
    st.error('パスワードが違います')
elif authentication_status is None:
    st.warning('ユーザー名とパスワードを入力してください')

if __name__ == "__main__":
    from streamlit.web.cli import main

    # Streamlitアプリケーションを実行する 
    try:
        main()
    except SystemExit as e:
        if e.code != 0:
            pass  # エラー処理
    except Exception as e:
        # その他の例外が発生した場合のエラーハンドリング
        error_details = traceback.format_exc()
        st.error(f"エラー: {str(e)}\n\nエラー詳細:\n{error_details}")
