import json
import requests

with open("BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json") as f:
    data = json.load(f)

for case in data["cases"]:
    response = requests.post(
        "http://127.0.0.1:8000/optimize-energy",
        json=case["input"],
    )

    print(f"{case['id']}: {response.status_code}")

    if response.status_code != 200:
        print(response.text)