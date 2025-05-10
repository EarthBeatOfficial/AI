import os
from dotenv import load_dotenv
import google.generativeai as genai
import requests
import json
from fastapi import FastAPI
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# ✅ API 키 로딩
GOOGLE_GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
print(GOOGLE_GEMINI_API_KEY)


# ✅ Gemini 모델 설정
genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-1.5-pro")

# ✅ 산책로 이름 추천
def get_trail_name_from_gemini(distance, theme, latitude, longitude):
    prompt = f"""
    You are a trail recommendation expert.
    User's starting location is at latitude: {latitude}, longitude: {longitude}.
    Desired conditions are:
    - Distance: {distance} (this is the total walking distance)
    - Theme: {theme} (this should strongly influence the type of trail and points of interest)

    Please respond with ONLY the trail name in text format.
    The name should reflect both the distance and theme.
    Example: "2km Nature Trail at Olympic Park" or "3km Historical Palace Route"
    """
    try:
        response = model.generate_content(prompt)
        text = response.candidates[0].content.parts[0].text.strip()
        print("📄 Recommended trail name:", text)
        return text
    except Exception as e:
        print("❌ Gemini API error:", e)
        return "Recommendation failed"

def clean_json_response(text):
    # Remove markdown code block if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    # Find the first { and last } to extract just the JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0:
        text = text[start:end]
    
    return text.strip()

# ✅ 상세 설명
def get_trail_detail_from_gemini(trail_name):
    prompt = f"""
    Please provide information about the trail "{trail_name}" in the following JSON format. Do not include any other text or markdown formatting.
    {{
      "trail_name": "{trail_name}",
      "main_features": "Describe the natural or atmospheric characteristics of this trail",
      "estimated_time": "Estimated walking time (e.g., about 45 minutes)",
      "route_guide": "Detailed guide from start to finish"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = clean_json_response(response.candidates[0].content.parts[0].text)
        print("📋 Detail response:", text)
        return json.loads(text)
    except Exception as e:
        print("❌ Gemini detail error:", e)
        return {}

# ✅ 순환 경로 지점 요청
def get_trail_waypoints_from_gemini(trail_name, latitude, longitude):
    # First, get the starting location name using reverse geocoding
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{latitude},{longitude}",
        "key": GOOGLE_MAPS_API_KEY,
        "region": "kr"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data["status"] == "OK":
            start_location = data["results"][0]["formatted_address"]
        else:
            start_location = "Starting Point"
    except Exception as e:
        print(f"❌ Reverse geocoding error: {e}")
        start_location = "Starting Point"

    prompt = f"""
    Please provide the representative waypoints for the trail "{trail_name}" in the following JSON format. Do not include any other text or markdown formatting.
    
    Requirements:
    1. The trail MUST start and end at: {start_location}
    2. Include 8-10 intermediate points to create a detailed trail route
    3. The total walking distance should match the distance mentioned in the trail name
    4. The points of interest should strongly reflect the theme mentioned in the trail name
    5. Use English place names that can be found on Google Maps
    6. Always include "Seoul, South Korea" after each location name
    7. Use specific, well-known landmarks or attractions
    8. Make sure the points form a logical walking route
    9. The first and last points should be the exact starting location
    
    Respond with ONLY the JSON object, no other text:
    {{
      "waypoints": [
        "Olympic Park Peace Gate, Seoul, South Korea",
        "Olympic Park Rose Garden, Seoul, South Korea",
        "Olympic Park Wildflower Garden, Seoul, South Korea",
        "Olympic Park Lotus Pond, Seoul, South Korea",
        "Olympic Park Ecological Forest, Seoul, South Korea",
        "Olympic Park Bird Watching Area, Seoul, South Korea",
        "Olympic Park Butterfly Garden, Seoul, South Korea",
        "Olympic Park Wildflower Garden, Seoul, South Korea",
        "Olympic Park Rose Garden, Seoul, South Korea",
        "Olympic Park Peace Gate, Seoul, South Korea"
      ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = clean_json_response(response.candidates[0].content.parts[0].text)
        print("📍 Waypoints response:", text)
        return json.loads(text).get("waypoints", [])
    except Exception as e:
        print("❌ Waypoints extraction error:", e)
        print("Raw response:", response.candidates[0].content.parts[0].text)
        return []

# ✅ Google Maps 경로 요청 (경유지 포함)
def get_directions_coordinates_from_waypoints(waypoints):
    if len(waypoints) < 2:
        return []

    # First verify the API key with a simple request
    test_url = "https://maps.googleapis.com/maps/api/geocode/json"
    test_params = {
        "address": "Seoul Station, Seoul, South Korea",
        "key": GOOGLE_MAPS_API_KEY
    }
    
    try:
        test_response = requests.get(test_url, params=test_params)
        test_data = test_response.json()
        if test_data["status"] != "OK":
            print(f"❌ Google Maps API key verification failed: {test_data['status']}")
            print("Please check if your API key is valid and has the following APIs enabled:")
            print("- Directions API")
            print("- Geocoding API")
            return []
    except Exception as e:
        print(f"❌ Google Maps API key verification error: {e}")
        return []

    origin = waypoints[0]
    destination = waypoints[-1]
    middle = waypoints[1:-1]

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "walking",
        "key": GOOGLE_MAPS_API_KEY,
        "waypoints": "|".join(middle) if middle else "",
        "region": "kr"
    }

    try:
        print(f"🔍 Requesting directions from {origin} to {destination}")
        if middle:
            print(f"Via: {', '.join(middle)}")
            
        response = requests.get(url, params=params)
        data = response.json()

        if data["status"] == "OK":
            steps = data["routes"][0]["legs"]
            coordinates = []
            for leg in steps:
                for step in leg["steps"]:
                    coordinates.append([step["start_location"]["lng"], step["start_location"]["lat"]])
                coordinates.append([leg["steps"][-1]["end_location"]["lng"], leg["steps"][-1]["end_location"]["lat"]])
            return coordinates
        else:
            print(f"❌ Google Maps API error: {data['status']}")
            print(f"Requested waypoints: {waypoints}")
            if "error_message" in data:
                print(f"Error message: {data['error_message']}")
            return []
    except Exception as e:
        print(f"❌ Google Maps request error: {e}")
        return []

# ✅ GeoJSON 변환
def convert_to_geojson_line(coordinates):
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        },
        "properties": {}
    }

# ✅ FastAPI 앱
app = FastAPI()

class TrailRequest(BaseModel):
    distance: str
    theme: str
    latitude: float
    longitude: float

def get_coordinates_for_waypoints(waypoints):
    if not waypoints:
        return []

    coordinates = []
    for waypoint in waypoints:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": waypoint,
            "key": GOOGLE_MAPS_API_KEY,
            "region": "kr"
        }

        try:
            print(f"🔍 Getting coordinates for: {waypoint}")
            response = requests.get(url, params=params)
            data = response.json()

            if data["status"] == "OK":
                location = data["results"][0]["geometry"]["location"]
                coordinates.append([location["lng"], location["lat"]])
            else:
                print(f"❌ Geocoding error for {waypoint}: {data['status']}")
                if "error_message" in data:
                    print(f"Error message: {data['error_message']}")
                return []
        except Exception as e:
            print(f"❌ Geocoding request error: {e}")
            return []

    return coordinates

@app.post("/recommend")
def recommend_trail(req: TrailRequest):
    trail_name = get_trail_name_from_gemini(req.distance, req.theme, req.latitude, req.longitude)
    if trail_name == "Recommendation failed":
        return {"error": "Gemini recommendation failed"}

    detail = get_trail_detail_from_gemini(trail_name)
    waypoints = get_trail_waypoints_from_gemini(trail_name, req.latitude, req.longitude)
    coords = get_coordinates_for_waypoints(waypoints)

    return {
        "route_name": trail_name,
        "coordinates": coords
    }

# ✅ 로컬 / Cloud Run 실행용
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
