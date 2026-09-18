from ollama import chat


response = chat(
    model="gemma4",
    messages=[
        {
            "role": "user",
            "content": "Explain battery energy storage in one simple sentence.",
        }
    ],
)

print(response.message.content)