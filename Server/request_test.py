from requests import put, get, post
import time

# base = "http://apaulling.com/naloxalocate"
base = "http://localhost:5000"
url = "/api/v1.0/users"
# url = "/api/v1.0/users?latitude=53.302943&longitude=-6.219235"
print base

# data = {"latitude": 53.302943,"longitude": -6.219235}
# data = {"latitude": 53.302543,"longitude": -6.219635, "accuracy": 443.3, "last_updated": long(time.time()*1000)}
headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

# r = get(base+url, json=data, headers=headers)
# r = put(base+url, json=data, headers=headers)
# r = get(base+url)
r = post(base+url)
print r.content
