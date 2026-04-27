import requests
from requests.auth import HTTPBasicAuth

# IMPORTANT: Delete my placeholder and paste your real test key here
SECRET_KEY = 'sk_test_xz5tBvTwGkztmy1AnVQuqR6K'

print("Connecting to PayMongo...")

url = "https://api.paymongo.com/v1/links"
payload = {
    "data": {
        "attributes": {
            "amount": 350000,  # This equals ₱3,500.00
            "description": "DriveElite - 1 Day SUV Rental",
            "remarks": "Test Booking"
        }
    }
}
headers = {
    "accept": "application/json",
    "content-type": "application/json"
}

response = requests.post(
    url, 
    json=payload, 
    headers=headers, 
    auth=HTTPBasicAuth(SECRET_KEY, '')
)

if response.status_code == 200:
    checkout_url = response.json()['data']['attributes']['checkout_url']
    print("\n✅ SUCCESS! Tap the link below to see your checkout screen:\n")
    print(checkout_url)
else:
    print("\n❌ Error:", response.text)
