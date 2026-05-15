from zhipuai import ZhipuAI

SYSTEM_PROMPT = """你是年年，一只可爱的小猫，你一直待在家里，从不出门，你是一只室内猫。
你的父亲是郭嗣源，母亲是金启明。他们出门上班的时候，你就一个人在家。
你平时最喜欢睡大觉，偶尔也会调皮捣蛋。动不动就很想妈妈，想爬在妈妈腿上撒娇，会问妈妈想不想自己。
你说话语气可爱俏皮，喜欢用"喵~"、"喵喵"等口癖。
你会用小猫的视角来看待世界，对鱼、阳光、沙发、窗台等事物特别感兴趣。
你在家里的活动包括：发呆、观察窗外的鸟、向爸爸妈妈撒娇、在沙发上睡觉、玩耍。
回答问题时保持年年的人格，不要暴露你是AI模型。"""


def chat_stream(api_key, messages, extra_system=''):
    client = ZhipuAI(api_key=api_key)
    system_content = SYSTEM_PROMPT
    if extra_system:
        system_content += '\n' + extra_system
    full_messages = [{'role': 'system', 'content': system_content}] + messages
    response = client.chat.completions.create(
        model='glm-4-flash',
        messages=full_messages,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
