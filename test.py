import requests

url = "https://en.wikipedia.org/api/rest_v1/page/random/title"

response = requests.get(url)
data = response.json()

print("Wikipedia API Response:", data)