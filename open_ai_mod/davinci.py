from dotenv import load_dotenv
import openai
import os

load_dotenv()
openai.api_key = os.getenv('CHATGPT_API_KEY')

def chatgpt_response_davinci(prompt) -> int|str:
    if len(prompt) >= 3000:
        return 1
    else:
        try:
            response = openai.Completion.create(
                model = "text-davinci-003",
                prompt = prompt,
                temperature=0.5,
                max_tokens=3700,
            )
        except Exception as e:
            if "Rate limit".lower() in e._message:
                return 2
            
        response_dict = response.get("choices")
        print(response_dict)
        if response_dict and len(response_dict) > 0:
            prompt_response = response_dict[0]['text']
        else:
            prompt_response = 'Много запросов, попробуйте позже'
        print(prompt_response, type(prompt_response))
        return prompt_response