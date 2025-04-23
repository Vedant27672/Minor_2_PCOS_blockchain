import requests

# URL of the local server
url = 'http://127.0.0.1:9000/submit'

# Simulate file upload
files = {'v_file': open('app/static/Uploads/PCOS_data.csv', 'rb')}
data = {'user': 'test_user'}

response = requests.post(url, files=files, data=data)

print(response.status_code)
print(response.text)
