import openai
import base64
import os
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO
from openai import OpenAI
from ..utilities import read_config
from ..database import con_db

# 從配置文件中讀取 tokens
config = read_config('config/config.txt')
ai_db = con_db(config)

XAI_clice = OpenAI(    
    api_key=config['XAI_API_KEY'],
    base_url="https://api.x.ai/v1",    
)
model_target = "grok-4-latest" #grok-2-latest #nalang-turbo-v19


collection = ai_db.ai_his
role_collection = ai_db.ai_role_xai_his

# 定義一個函數來轉換每條記錄為 
def convert_to_openai_format(collection_name):
    c_collection = ai_db[collection_name]
    history = list(c_collection.find())    
    # 使用列表解析進行轉換
    formatted_messages = [
        {
            "role": str(h.get("role", "user")),
            "content": str(h.get("content", ""))
        }
        for h in history
    ]
    return formatted_messages

def generate_summary(user_input, collection_name="ai_his"):
    collection_his = ai_db[collection_name] 
    user_message = {"role": "user", "content": user_input}
    collection_his.insert_one(user_message)
    conversation_history = convert_to_openai_format(collection_name)        
    response = XAI_clice.chat.completions.create(
        messages=conversation_history,
        model=model_target        
    )
    assistant_message = response.choices[0].message.content
    collection_his.insert_one({"role": "assistant", "content": assistant_message})

    return assistant_message

def clear_conversation_history(collection_name="ai_his",system_message="請用繁體中文回答"):
    collection_history = ai_db[collection_name]
    collection_history.delete_many({})
    collection_history.insert_one({"role": "system", "content": system_message})    

def analyze_sentiment(text):
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=[
            {"role": "system", "content": "你是一個情感分析器，判定語錄是正能量還是負能量。"},
            {"role": "user", "content": f"這句話：'{text}' 是正能量還是負能量？"}
        ]
    )       
    return response.choices[0].message.content.strip().lower()

def analyze_stock(his_data, now_data):
    historical_data_strs = [f"這是股票的歷史紀錄：\n{record}" for record in his_data]
    messages = [{"role": "system", "content": "你是一個股票的專業技術分析專家，給你股票歷史紀錄與現況幫我分析趨勢"}]
    for record_str in historical_data_strs:
        messages.append({"role": "user", "content": record_str})

    messages.append({"role": "user", "content": f"這是該股現況 {now_data}"})
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=messages
    )       
    return response.choices[0].message.content.strip().lower()    

def analyze_stock_inoutpoint(his_data, now_data):
    historical_data_strs = [f"這是股票的歷史紀錄：\n{record}" for record in his_data]
    messages = [{"role": "system", "content": "你是一個股票的專業技術分析專家，給你股票歷史紀錄，提供我長中短期交易買點建議"}]
    for record_str in historical_data_strs:
        messages.append({"role": "user", "content": record_str})

    messages.append({"role": "user", "content": f"這是該股現況 {now_data}"})
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=messages
    )       
    return response.choices[0].message.content.strip().lower()    

def  painting(text):
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=[
            {"role": "system", "content": "你是翻譯官，幫我將文字描述翻譯為英文用來提供給StabilityAI繪圖用"},
            {"role": "user", "content": f"幫我轉化：'{text}' "}
        ]
    )       
    return response.choices[0].message.content.strip().lower()

def create_greet(member,types):
    # 呼叫 XAI API 生成問候
    response = XAI_clice.chat.completions.create(
        model=model_target,
        messages=[
            {"role": "system", "content": f"你是一個有趣的上下線通知生成器，給你成員名稱，幫我生成一句{types}通知"},
            {"role": "user", "content": f"成員名稱：'{member}' "}
        ]
    )       
    return response.choices[0].message.content.strip().lower()
