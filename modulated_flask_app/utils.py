import hmac
import hashlib
import json

def verify_slack_request(data, timestamp, signature, signing_secret):
    req = str.encode('v0:' + str(timestamp) + ':') + data
    request_hash = 'v0=' + hmac.new(
        str.encode(signing_secret),
        req, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(request_hash, signature)

def load_lookup_table(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)