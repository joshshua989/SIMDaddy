
# utils/phone_verification.py

# Mock phone verification logic
# Replace with real Twilio Verify integration later

VERIFICATION_STORE = {}

def send_sms_code(phone):
    # In a real system, this would call Twilio Verify API
    print(f"📱 Sending mock SMS to {phone}... Code is '123456'")
    VERIFICATION_STORE[phone] = "123456"
    return True

def verify_sms_code(phone, code):
    return VERIFICATION_STORE.get(phone) == code
