import openai
from openai import OpenAI
from .utilities import read_config
# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
OpenAI_clice = OpenAI(    
    api_key=config['OPENAI_API_KEY']
)
model_target = "gpt-4o"
def generate_summary(user_input):
    response = OpenAI_clice.chat.completions.create(
        messages=[
            {"role": "system", "content": "請用繁體中文回答"},
            {
                "role": "user",
                "content": user_input,
            }
        ],
        model=model_target,            
    )
    return response.choices[0].message.content

def validate_with_openai(text):
    # 使用 OpenAI 的 API 進行檢查
    response = OpenAI_clice.chat.completions.create(
        messages=[
            {"role": "system", "content": "你是繁體中文錯別字檢查器，只會回答正確或是修正錯別字"},
            {"role": "system", "content": "請用檢查文中是否有錯字 如果沒有請回答'正確'，有錯請回答修正錯字後的句子 "},
            {
                "role": "user",
                "content": text,
            }
        ],
        model=model_target,         
    )    
    print(response.choices[0].message.content)
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

def  painting(text):
    response = OpenAI_clice.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是翻譯官，幫我將文字描述翻譯為英文用來提供給StabilityAI繪圖用"},
            {"role": "user", "content": f"幫我轉化：'{text}' "}
        ]
    )       
    return response.choices[0].message.content.strip().lower()