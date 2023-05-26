from dotenv import load_dotenv
import openai
import os

load_dotenv()
openai.api_key = os.getenv('CHATGPT_API_KEY')

#проверяем длину контекста или запроса, чтобы ограничивать токены в запросе и не ловить ошибку) *
def check_symbols_inside(data: str|list) -> int:
    length = 0
    if isinstance(data, str):
        length = len(data)
    if isinstance(data, list):
        try:
            for item in data:
                length += len(item['content'])
        except:
            pass
    return length

# messages = 
            # [
            # {"role": "system", "content" : "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."},
            # {"role": "user", "content" : "Привет, меня зовут Павел, запомни это пожалуйста"},
            # {"role": "assistant", "content" : "Хорошо1 2, буду называть тебя Павел"},
            # {"role": "user", "content" : "Давай проверим, как меня зовут 1 2"},
            # ],

def chatgpt_response_turbo35(prompt: str, message_context: list):
    if isinstance(message_context, list):
        res = check_symbols_inside(message_context)
        tokens = 4096 - res - 100 #-100 на всякий случай)
        completion = ''
        try:
            completion = openai.ChatCompletion.create(
                    model = 'gpt-3.5-turbo',
                    messages=message_context,
                    temperature = 1,
                    max_tokens = tokens
            )
        except Exception as e:
            if "less" in e._message:
                print('! мало симв')
                return 1
            if "Rate limit".lower() in e._message:
                print('! время ожидания')
                return 2
        if completion and len(completion['choices'][0]['message']['content']) > 0:
            prompt_response = completion['choices'][0]['message']['content']
        else:
            prompt_response = "Много запросов, попробуйте позже"
        return prompt_response

#Список доступных моделей
#print(openai.Model.list())
