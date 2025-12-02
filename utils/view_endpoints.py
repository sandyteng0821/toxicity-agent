import requests
import json

# Replace with your actual URL
response = requests.get("http://localhost:8000/openapi.json")
data = response.json()

# Print all endpoints
for path, methods in data["paths"].items():
    for method in methods.keys():
        print(f"{method.upper():<7} {path}")