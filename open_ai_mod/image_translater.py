import os
import openai
openai.api_key = "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"
import base64
import json


def create_image(user_id, content, count_pictures):
    res = openai.Image.create(
    prompt=content,
    n=count_pictures,
    size="1024x1024",
    response_format = 'b64_json'
    )
    return res


# try:
#     file = open(r'test_context\test.json', 'w')
#     file.write(str(res))
# except Exception as e:
    

# with open(r'test_context\test.json') as f:
#     data = json.load(f)
# data_dict = dict(data)

# image_data = base64.b64decode(data_dict['data'][0]['b64_json'])
# with open('image.png', 'wb') as f:
#     f.write(image_data)



