import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def test_deepseek_connection():
    api_key = os.getenv("VOLC_API_KEY")
    model_id = os.getenv("VOLC_DEEPSEEK_MODEL_ID")
    alt_model_id = os.getenv("VOLC_MODEL_ID")
    base_url = "https://ark.cn-beijing.volces.com/api/v3"

    print(f"--- 正在测试火山引擎 DeepSeek 连通性 ---")
    print(f"API Key: {api_key[:8]}...{api_key[-4:] if api_key else 'None'}")
    
    models_to_test = [
        ("VOLC_DEEPSEEK_MODEL_ID", model_id),
        ("VOLC_MODEL_ID", alt_model_id)
    ]

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )

    for name, mid in models_to_test:
        print(f"\n测试模型 {name}: {mid}")
        if not mid:
            print(f"跳过 {name} (未设置)")
            continue
            
        try:
            print("正在发送测试请求...")
            response = await client.chat.completions.create(
                model=mid,
                messages=[
                    {"role": "user", "content": "你好，请确认你是否是 DeepSeek 模型，并回复 '连接成功'。"}
                ],
                stream=False
            )
            
            content = response.choices[0].message.content
            print(f"模型回复: {content}")
            print(f"✅ {name} 测试成功！")
        except Exception as e:
            print(f"❌ {name} 测试失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_deepseek_connection())
