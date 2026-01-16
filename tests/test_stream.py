import httpx
import sys

question = "Summarize the termination clause"
url = "http://127.0.0.1:8000/ask/stream"

print(f"User: {question}\n")
print("AI: ", end="", flush=True)

with httpx.stream("GET", url, params={"question": question}, timeout=60.0) as response:
    for line in response.iter_lines():
        if line:
            if line.startswith("data: "):
                content = line.replace("data: ", "")
                
                if content == "[DONE]":
                    break
                
                sys.stdout.write(content)
                sys.stdout.flush()

print("\n\n Stream finished.")