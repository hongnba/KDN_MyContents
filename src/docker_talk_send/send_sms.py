import requests
import urllib

url = 'http://10.100.21.128:17878/sendSmsJson'

data = {
    "sendNo": urllib.parse.quote('01044683990'),
    "callBackNo": urllib.parse.quote('0619317114'),
    "systemKey": urllib.parse.quote('222046-caas01'),
    "projectId": urllib.parse.quote('KDN-3570-23-0001'),
    "content": "test"
}

response = requests.post(url, data=data)
print(response)