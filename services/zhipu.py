from flask import current_app
from zhipuai import ZhipuAI


def get_client():
    return ZhipuAI(api_key=current_app.config['ZHIPU_API_KEY'])


def chat_stream(messages):
    """调用智谱GLM API，以流式方式返回生成器。"""
    client = get_client()
    response = client.chat.completions.create(
        model='glm-4-flash',
        messages=messages,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
