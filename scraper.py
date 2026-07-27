import requests
from bs4 import BeautifulSoup
import json

def scrape_swinburne_data():
    url = "https://swinburne-vn.edu.vn/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0",
        "Accept-Language": "vi-VN,vi;q=0.9"
    }
    
    # Step 1: The Request Handshake
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        return
    print("--- Connection Successful: Data Received ---")
    
    # Step 2: Target Identification
    soup = BeautifulSoup(response.content, 'html.parser')
    paragraphs = soup.find_all('p')
    
    # Step 3 & 4: Cleaning and Automated Object Creation with ID Tracking
    scraped_results = []
    current_id = 5001  # Starting ID as required by Lab 6
    
    for p in paragraphs:
        # Cleaning: stripping whitespace
        clean_text = p.get_text(strip=True).replace("\xa0", " ")
        
        # Only keep substantial information blocks
        if len(clean_text) > 20:
            # Create a dictionary representing our object
            info_object = {
                "id": current_id,
                "source": "Swinburne Homepage",
                "content": clean_text
            }
            scraped_results.append(info_object)
            current_id += 1
            
    print(f"Total count of successfully created objects: {len(scraped_results)}")
    
    # Step 5: Data Persistence (JSON Output)
    with open("scraped_data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_results, f, ensure_ascii=False, indent=4)
        
    print("✅ Saved to scraped_data.json")

if __name__ == "__main__":
    scrape_swinburne_data()