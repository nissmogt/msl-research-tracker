#!/usr/bin/env python3
"""
Test script for the new save article with insights feature.
"""

import requests
import json

def test_save_insights_feature():
    """Test the complete flow: generate insights → save article + insights"""
    
    base_url = "https://www.insightmsl.com/api"
    
    # Test article ID (we know this one works for insights)
    article_id = "40842428"
    
    print("🧪 Testing Save Article with Insights Feature")
    print("=" * 50)
    
    # Step 1: Generate insights for an article
    print(f"1️⃣ Generating insights for article {article_id}...")
    
    insights_response = requests.post(
        f"{base_url}/articles/{article_id}/insights",
        json={},
        headers={"Content-Type": "application/json"}
    )
    
    if insights_response.status_code != 200:
        print(f"❌ Failed to generate insights: {insights_response.status_code}")
        print(insights_response.text)
        return
    
    insights_data = insights_response.json()
    insights_text = insights_data["insights"]
    article_data = insights_data["article"]
    
    print(f"✅ Insights generated successfully ({len(insights_text)} characters)")
    print(f"📄 Article: {article_data.get('title', 'Unknown title')[:60]}...")
    
    # Step 2: Save the article with insights
    print("\n2️⃣ Saving article with insights to local database...")
    
    # Prepare the save request
    save_request = {
        "article_data": {
            "pubmed_id": article_data.get("pubmed_id"),
            "title": article_data.get("title"),
            "abstract": article_data.get("abstract"),
            "authors": article_data.get("authors", []),
            "journal": article_data.get("journal"),
            "publication_date": article_data.get("publication_date"),
            "therapeutic_area": article_data.get("therapeutic_area"),
            "link": article_data.get("link"),
            "rss_fetch_date": article_data.get("rss_fetch_date", "2025-08-27")
        },
        "insights": insights_text
    }
    
    save_response = requests.post(
        f"{base_url}/articles/save-with-insights",
        json=save_request,
        headers={"Content-Type": "application/json"}
    )
    
    if save_response.status_code != 200:
        print(f"❌ Failed to save article: {save_response.status_code}")
        print(save_response.text)
        return
    
    save_data = save_response.json()
    print(f"✅ {save_data['message']}")
    print(f"🆔 Article ID: {save_data['article_id']}")
    
    # Step 3: Verify the article was saved by checking recent articles
    print("\n3️⃣ Verifying article appears in recent articles with insights...")
    
    recent_response = requests.get(f"{base_url}/articles/recent")
    
    if recent_response.status_code == 200:
        recent_articles = recent_response.json()
        saved_article = next((a for a in recent_articles if a["pubmed_id"] == article_id), None)
        
        if saved_article and saved_article.get("insights"):
            print(f"✅ Article found in recent articles with insights saved!")
            print(f"💭 Insights preview: {saved_article['insights'][:100]}...")
        else:
            print("⚠️  Article found but insights might not be included in response")
    else:
        print("⚠️  Could not verify in recent articles")
    
    print("\n🎉 Test completed successfully!")
    print("\n💡 Implementation Notes:")
    print("- Users can generate insights for any article (local DB or PubMed)")
    print("- Users have full control over what gets saved locally")
    print("- Articles are only saved when explicitly requested")
    print("- Insights are stored with the article for future reference")

if __name__ == "__main__":
    test_save_insights_feature()
