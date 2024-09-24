import openai
from openai import OpenAI
from .utilities import read_config
# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
OpenAI_clice = OpenAI(    
    api_key=config['OPENAI_API_KEY']
)
def generate_summary(user_input):
    response = OpenAI_clice.chat.completions.create(
        messages=[
            {"role": "system", "content": "請用繁體中文回答"},
            {
                "role": "user",
                "content": user_input,
            }
        ],
        model="gpt-4o",            
    )
    return response.choices[0].message.content

def analyze_sentiment(text):
    response = OpenAI_clice.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一個情感分析器，判定語錄是正能量還是負能量。"},
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )       
    return response.choices[0].message.content.strip().lower()