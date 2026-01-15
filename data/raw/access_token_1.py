from fyers_apiv3 import fyersModel

redirect_uri = "http://127.0.0.1"
client_id = "PLE8T7ZKRQ-100"
secret_key = "C79RJCCJ95"
grant_type = "authorization_code"
response_type = "code"


### Connect to the sessionModel object here with the required input parameters
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type=response_type,
    grant_type=grant_type
)

auth_url = session.generate_authcode()

print("=" * 80)
print("STEP 1: AUTHORIZATION")
print("=" * 80)
print("\n1. Open this URL in your browser:")
print(f"\n{auth_url}\n")
print("2. Accept all permissions")
print("3. You'll be redirected to a URL like:")
print("   http://127.0.0.1:5000?code=AUTH_CODE&state=...")
print("\n4. Copy ONLY the AUTH_CODE part (between 'code=' and '&state=')")
print("5. Paste it in step2_generate_token.py")
print("=" * 80)


# http://127.0.0.1/?s=ok&code=200&auth_code=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJQTEU4VDdaS1JRIiwidXVpZCI6IjdlMWE4MWFjYTRhMjRhZjhiY2VmMWY4M2ZkNTUzNzhlIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IkZBSDk0NzIwIiwib21zIjoiSzEiLCJoc21fa2V5IjoiOWY1YjNkNjU0ODdiODEyYjQ4NzRkYTI3YWYzNDViYmMyODVkOWYyNjlhMTJkZTc1OGQxOTE4MWQiLCJpc0RkcGlFbmFibGVkIjoiTiIsImlzTXRmRW5hYmxlZCI6Ik4iLCJhdWQiOiJbXCJkOjFcIixcImQ6MlwiLFwieDowXCIsXCJ4OjFcIixcIng6MlwiXSIsImV4cCI6MTc2ODUyODk5OCwiaWF0IjoxNzY4NDk4OTk4LCJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJuYmYiOjE3Njg0OTg5OTgsInN1YiI6ImF1dGhfY29kZSJ9.fWXYesiMWQnJDokiSyz88meKz2nL5NsyXbpExtibY5s&state=None