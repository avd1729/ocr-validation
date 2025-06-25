import requests

url = "http://localhost:5000/validate"
file_path = "documents/sample.pdf"

with open(file_path, "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

print("Status Code:", response.status_code)
print("Response:")
print(response.json())
