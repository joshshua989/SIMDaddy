import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def get_player_transactions(month, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find('div', {'id': 'content'})

        transactions = []
        current_date = None

        positions = [
            "QB", "RB", "WR", "TE", "DT", "DE", "LB", "CB", "S",
            "OT", "OG", "G", "C", "FB", "K", "P", "LS", "DL", "DB", "OL"
        ]

        keywords = ["Signed", "Re-Signed", "Waived", "Claimed", "Released", "Activated", "Placed", "Traded"]

        for elem in content_div.find_all(['h2', 'p']):
            text = elem.get_text(strip=True)

            if re.match(r"^[A-Za-z]+\s\d{1,2},\s\d{4}$", text):
                current_date = text
            elif current_date and any(word.lower() in text.lower() for word in keywords):
                text = re.sub(r'(The)([A-Z])', r'\1 \2', text)
                for keyword in keywords:
                    text = re.sub(rf'([a-z])({keyword})', r'\1 \2', text, flags=re.IGNORECASE)
                for pos in positions:
                    text = re.sub(rf'({pos})([A-Z])', r'\1 \2', text)
                def fix_glued(match):
                    word = match.group(2)
                    return match.group(1) + (word if word.lower() == "season" else f" {word}")
                text = re.sub(r'([a-zA-Z])(?=(to|on|from|season)\b)', r'\1 ', text)
                text = re.sub(r'([a-zA-Z])\s(season\b)', fix_glued, text, flags=re.IGNORECASE)
                text = re.sub(r'\b(the)([A-Z])', r'\1 \2', text, flags=re.IGNORECASE)
                transactions.append({'date': current_date, 'text': text})

        return transactions

    except requests.RequestException as e:
        print(f"Error fetching transactions: {e}")
        return []
