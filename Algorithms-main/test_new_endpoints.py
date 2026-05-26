"""测试新的 AI 助手端点"""
import json
import urllib.request

def test_health():
    """测试健康检查端点"""
    response = urllib.request.urlopen("http://127.0.0.1:8000/health")
    data = json.loads(response.read().decode("utf-8"))
    print("Health check:", data)

def test_ai_ask():
    """测试 AI 问答端点"""
    try:
        body = json.dumps({"question": "什么是贪心图染色算法？"}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8000/assistant/ask",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode("utf-8"))
        print("AI Ask:", data)
    except Exception as e:
        print("AI Ask Error:", e)

def test_analyze():
    """测试分析端点"""
    try:
        body = json.dumps({
            "courses": [
                {"id": "C1", "name": "数据结构", "teacherId": "T1", "classGroupIds": ["G1"], "weeklyHours": 2}
            ],
            "timeSlots": [
                {"id": "D1-S1", "weekday": 1, "startSection": 1, "endSection": 2}
            ]
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8000/assistant/analyze",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode("utf-8"))
        print("Analyze:", data.get("success", False))
    except Exception as e:
        print("Analyze Error:", e)

if __name__ == "__main__":
    print("Testing API endpoints...")
    test_health()
    test_analyze()
    test_ai_ask()