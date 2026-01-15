from fyers_apiv3 import fyersModel

# Step 1: Configuration Setup
redirect_uri = "http://127.0.0.1"
client_id = "PLE8T7ZKRQ-100"
secret_key = "C79RJCCJ95"
grant_type = "authorization_code"
response_type = "code"

#  ============================================
# PASTE AUTH CODE FROM STEP 1 HERE
# ============================================
AUTH_CODE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJQTEU4VDdaS1JRIiwidXVpZCI6IjdlMWE4MWFjYTRhMjRhZjhiY2VmMWY4M2ZkNTUzNzhlIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IkZBSDk0NzIwIiwib21zIjoiSzEiLCJoc21fa2V5IjoiOWY1YjNkNjU0ODdiODEyYjQ4NzRkYTI3YWYzNDViYmMyODVkOWYyNjlhMTJkZTc1OGQxOTE4MWQiLCJpc0RkcGlFbmFibGVkIjoiTiIsImlzTXRmRW5hYmxlZCI6Ik4iLCJhdWQiOiJbXCJkOjFcIixcImQ6MlwiLFwieDowXCIsXCJ4OjFcIixcIng6MlwiXSIsImV4cCI6MTc2ODUyODk5OCwiaWF0IjoxNzY4NDk4OTk4LCJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJuYmYiOjE3Njg0OTg5OTgsInN1YiI6ImF1dGhfY29kZSJ9.fWXYesiMWQnJDokiSyz88meKz2nL5NsyXbpExtibY5s"

# ============================================
# GENERATE ACCESS TOKEN
# ============================================
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type="code",
    grant_type="authorization_code"
)

session.set_token(AUTH_CODE)
response = session.generate_token()

# ============================================
# SAVE ACCESS TOKEN
# ============================================
if 'access_token' in response:
    access_token = response['access_token']
    
    # Save to file
    with open("access_token.txt", "w") as f:
        f.write(access_token)
    
    print("=" * 80)
    print("SUCCESS! Access Token Generated")
    print("=" * 80)
    print(f"\nAccess Token: {access_token}")
    print(f"\nToken saved to: access_token.txt")
    print("\nNow run step3_download_data.py")
    print("=" * 80)
else:
    print("ERROR:", response)
    print("\nMake sure you:")
    print("1. Used a fresh auth code (they expire quickly)")
    print("2. Copied the ENTIRE auth code correctly")
    print("3. Updated CLIENT_ID and SECRET_KEY")
