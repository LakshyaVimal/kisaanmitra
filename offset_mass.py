from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from requests.auth import HTTPBasicAuth
import requests
import os

app = Flask(__name__)

# ==== 🔐 Set your credentials here ==== #
ROBOFLOW_API_KEY = "ckMI9aYYCuCHtSqAwrun"
ROBOFLOW_MODEL_ID = "crop-disease-identifier/4"
TWILIO_ACCOUNT_SID = "AC5acdc47c163cb233a148b34c4a6556d5"
TWILIO_AUTH_TOKEN = "2465662c59ee3a2c76dd2033a24fd5a8"
OPENWEATHER_API_KEY = "067e1f6a40b94a43a7f3b9fca73d11df"
# ===================================== #

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.values.get("Body", "").strip()
    media_url = request.values.get("MediaUrl0", "")
    media_type = request.values.get("MediaContentType0", "")

    print("📩 Incoming message:", incoming_msg)

    resp = MessagingResponse()
    msg = resp.message()

    if media_url and media_type.startswith("image/"):
        msg.body("📷 Thanks! Analyzing your crop image...")

        try:
            prediction = detect_crop_disease(media_url)

            if isinstance(prediction, dict) and prediction:
                # Filter predictions with confidence >= 5%
                filtered = {
                    label: round(data["confidence"] * 100, 2)
                    for label, data in prediction.items()
                    if data["confidence"] >= 0.05
                }

                if filtered:
                    responses = [
                        f"🦠 *{label}*: {confidence}%" for label, confidence in filtered.items()
                    ]
                    msg.body("📊 Disease Predictions:\n" + "\n".join(responses) +
                             "\n💡 Suggestion: Consult an agri expert or use appropriate treatment.")
                else:
                    msg.body("✅ Your crop looks healthy! No strong signs of disease.")
            else:
                msg.body("⚠️ No predictions received from model.")

        except Exception as e:
            msg.body(f"❌ Error while processing image: {str(e)}")

        return str(resp)

    elif incoming_msg.isdigit() and len(incoming_msg) == 6:
        pin = incoming_msg
        print("📍 PIN code received:", pin)

        location = get_coordinates_from_pin(pin)
        print("📍 Location (lat, lon):", location)

        if not location:
            msg.body("❌ Sorry, couldn’t find that PIN code.")
            return str(resp)

        lat, lon = location
        weather = get_weather(lat, lon)
        print("🌦️ Weather fetched:", weather)

        if weather:
            msg.body(
                f"📍 Weather for PIN {pin}\n"
                f"☁️ {weather['description'].title()}\n"
                f"🌡️ Temp: {weather['temp']}\u00b0C\n"
                f"💧 Humidity: {weather['humidity']}%\n"
                f"🌐 Advice: {weather['advice']}"
            )
            return str(resp)
        else:
            msg.body("⚠️ Couldn’t fetch weather right now. Try later.")
    else:
        msg.body("🙏 Namaste! Welcome to KisaanMitra 🌾\nSend a *tomato crop photo* 📷 or your 6-digit PIN code to get started.")

    return str(resp)


def detect_crop_disease(image_url):
    response = requests.get(image_url, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    if response.status_code != 200:
        print("❌ Failed to fetch image from Twilio:", response.status_code)
        return {}

    url = f"https://detect.roboflow.com/{ROBOFLOW_MODEL_ID}?api_key={ROBOFLOW_API_KEY}"
    roboflow_response = requests.post(url, files={"file": response.content})

    try:
        result = roboflow_response.json()
        print("Roboflow Response:", result)
    except ValueError:
        print("⚠️ Roboflow returned non-JSON response:", roboflow_response.text)
        return {}

    if "predictions" in result and isinstance(result["predictions"], dict):
        return result["predictions"]
    else:
        print("⚠️ No predictions key or wrong format in response.")
        return {}


def get_coordinates_from_pin(pin):
    try:
        url = f"https://nominatim.openstreetmap.org/search?postalcode={pin}&country=India&format=json"
        headers = {"User-Agent": "KisaanMitraBot/1.0"}
        r = requests.get(url, headers=headers)
        if r.status_code != 200 or not r.json():
            return None
        data = r.json()[0]
        return float(data["lat"]), float(data["lon"])
    except:
        return None


def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_API_KEY}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    return {
        "temp": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "description": data["weather"][0]["description"],
        "advice": "Avoid irrigation during peak afternoon 🌞" if data["main"]["temp"] > 32 else "Suitable time for irrigation 💧"
    }


if __name__ == "__main__":
    app.run(debug=True)
