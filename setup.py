import os

def setup_environment():
    # Check if environment variables are set
    gemini_key = os.environ.get("GOOGLE_API_KEY")
    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    
    if not gemini_key:
        print("⚠️ GOOGLE_API_KEY is not set")
        print("Please get your API key from: https://makersuite.google.com/app/apikey")
        gemini_key = input("Enter your Gemini API key: ")
    
    if not maps_key:
        print("⚠️ GOOGLE_MAPS_API_KEY is not set")
        print("Please get your API key from: https://console.cloud.google.com/google/maps-apis/credentials")
        maps_key = input("Enter your Google Maps API key: ")
    
    # Save to .env file
    with open('.env', 'w') as f:
        f.write(f'GOOGLE_API_KEY={gemini_key}\n')
        f.write(f'GOOGLE_MAPS_API_KEY={maps_key}\n')
    
    print("✅ Environment variables are saved to .env file!")
    print("You can now run 'python main.py' to start the server")

if __name__ == "__main__":
    setup_environment() 