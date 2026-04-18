from google_auth_oauthlib.flow import InstalledAppFlow

# The permissions your app needs
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents'
]

def generate_token():
    # This reads the file you just downloaded
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    
    # This will pop up a Google login window in your browser!
    creds = flow.run_local_server(port=0)
    
    # Save the resulting secure credentials to a new file
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("Success! Your token.json file has been created.")

if __name__ == '__main__':
    generate_token()
