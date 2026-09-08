import requests, json

def test():
    prompts = [
        "Write Python code to add two numbers", # Should succeed immediately
        "Write an intentionally incorrect factorial function that fails a basic test", # Should fail test and repair
        "Write code with a syntax error intentionally", # Should fail syntax and repair
    ]
    for prompt in prompts:
        print(f"Testing: {prompt}")
        response = requests.post("http://127.0.0.1:8000/generate", json={"prompt": prompt})
        try:
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print("Failed to decode json:", response.text)

if __name__ == "__main__":
    test()
