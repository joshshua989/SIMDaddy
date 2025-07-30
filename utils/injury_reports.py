# utils/injury_reports.py

import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_injury_reports():
    urls = [
        "https://www.fantasypros.com/nfl/injury-news.php",
        "https://www.fantasypros.com/nfl/injury-news.php?page=2",
        "https://www.fantasypros.com/nfl/injury-news.php?page=3",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    injury_data = []

    for url in urls:
        print(f"Scraping: {url}")
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.find_all("div", class_="player-news-item")

        for article in articles:
            try:
                headline_tag = article.find("div", class_="player-news-header").find("a")
                headline = headline_tag.text.strip() if headline_tag else None

                date_tag = article.find("div", class_="player-news-header").find("p")
                date = date_tag.text.strip().split("By")[0].strip() if date_tag else None

                ten_columns_div = article.find("div", class_="ten columns")
                p_tags = ten_columns_div.find_all("p", recursive=False)

                description = None
                fantasy_impact = None
                found_description = False

                for p in p_tags:
                    text = p.get_text(strip=True)
                    if not found_description and "Fantasy Impact" not in text and "By" not in text:
                        description = text
                        found_description = True
                    elif "Fantasy Impact" in text:
                        fantasy_impact = text.replace("Fantasy Impact:", "").strip()
                        break

                injury_data.append({
                    "headline": headline,
                    "date": date,
                    "description": description,
                    "fantasy_impact": fantasy_impact
                })

            except Exception as e:
                print(f"Error parsing article: {e}")

    df = pd.DataFrame(injury_data)

    if not df.empty and 'headline' in df.columns:
        df.insert(0, 'player_name', df['headline'].apply(lambda x: " ".join(x.split()[:2]) if isinstance(x, str) else None))

    print("✅ Loaded injuries DataFrame:", df.shape)
    return df
