import asyncio
from myUtils.auth import check_cookie

async def test_single_account():
    # 测试单个账号
    result = await check_cookie(1, "00885756-4dad-11f0-83a3-4925f36afe0f.json")  # 1是小红书
    print(f"验证结果: {result}")

if __name__ == "__main__":
    asyncio.run(test_single_account())
