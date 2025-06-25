import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
from sqlalchemy.orm import Session
import json

from models import Article
from services import ArticleService

class PubMedService:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.api_key = None  # Optional: Get from https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/
        self.delay = 0.34  # NCBI requires 3 requests per second max
    
    def search_articles(self, therapeutic_area: str, days_back: int = 7) -> List[Dict]:
        """Search PubMed for articles in the specified therapeutic area"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for PubMed
            start_date_str = start_date.strftime("%Y/%m/%d")
            end_date_str = end_date.strftime("%Y/%m/%d")
            
            # Build search query
            query = f'"{therapeutic_area}"[Title/Abstract] AND ("{start_date_str}"[Date - Publication] : "{end_date_str}"[Date - Publication])'
            
            # Search for article IDs
            search_url = f"{self.base_url}/esearch.fcgi"
            params = {
                'db': 'pubmed',
                'term': query,
                'retmode': 'xml',
                'retmax': 50,  # Limit results
                'sort': 'date'
            }
            
            if self.api_key:
                params['api_key'] = self.api_key
            
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            
            # Parse search results
            root = ET.fromstring(response.content)
            id_list = root.find('.//IdList')
            
            if id_list is None or len(id_list) == 0:
                print(f"No articles found for {therapeutic_area}")
                return []
            
            # Get article IDs
            article_ids = [id_elem.text for id_elem in id_list.findall('Id')]
            
            # Fetch article details
            articles = []
            for article_id in article_ids:
                article_data = self._fetch_article_details(article_id)
                if article_data:
                    articles.append(article_data)
                time.sleep(self.delay)  # Respect NCBI rate limits
            
            return articles
            
        except Exception as e:
            print(f"Error searching PubMed: {e}")
            return []
    
    def _fetch_article_details(self, pubmed_id: str) -> Optional[Dict]:
        """Fetch detailed information for a specific article"""
        try:
            fetch_url = f"{self.base_url}/efetch.fcgi"
            params = {
                'db': 'pubmed',
                'id': pubmed_id,
                'retmode': 'xml'
            }
            
            if self.api_key:
                params['api_key'] = self.api_key
            
            response = requests.get(fetch_url, params=params)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            article = root.find('.//PubmedArticle')
            
            if article is None:
                return None
            
            # Extract article information
            medline_citation = article.find('.//MedlineCitation')
            pubmed_data = article.find('.//PubmedData')
            
            # Title
            title_elem = medline_citation.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title available"
            
            # Abstract
            abstract_elem = medline_citation.find('.//Abstract/AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else ""
            
            # Authors
            authors = []
            author_list = medline_citation.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('Author'):
                    last_name = author.find('LastName')
                    first_name = author.find('ForeName')
                    if last_name is not None and first_name is not None:
                        authors.append(f"{first_name.text} {last_name.text}")
                    elif last_name is not None:
                        authors.append(last_name.text)
            
            # Journal
            journal_elem = medline_citation.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Publication date
            pub_date = medline_citation.find('.//PubDate')
            publication_date = ""
            if pub_date is not None:
                year = pub_date.find('Year')
                month = pub_date.find('Month')
                day = pub_date.find('Day')
                
                if year is not None:
                    publication_date = year.text
                    if month is not None:
                        publication_date += f"-{month.text}"
                        if day is not None:
                            publication_date += f"-{day.text}"
            
            # Create article data
            article_data = {
                'pubmed_id': pubmed_id,
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'journal': journal,
                'publication_date': publication_date,
                'link': f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                'rss_fetch_date': datetime.now().strftime("%Y-%m-%d"),
                'therapeutic_area': self._extract_therapeutic_area(title, abstract)
            }
            
            return article_data
            
        except Exception as e:
            print(f"Error fetching article {pubmed_id}: {e}")
            return None
    
    def _extract_therapeutic_area(self, title: str, abstract: str) -> str:
        """Extract therapeutic area from title and abstract"""
        text = f"{title} {abstract}".lower()
        
        therapeutic_areas = {
            'oncology': ['cancer', 'tumor', 'carcinoma', 'leukemia', 'lymphoma', 'oncology'],
            'cardiovascular': ['heart', 'cardiac', 'cardiovascular', 'vascular', 'hypertension'],
            'neurology': ['brain', 'neurological', 'neurology', 'stroke', 'alzheimer', 'parkinson'],
            'immunology': ['immune', 'immunology', 'autoimmune', 'inflammation'],
            'rare diseases': ['rare disease', 'orphan', 'genetic disorder'],
            'infectious diseases': ['infection', 'viral', 'bacterial', 'pathogen'],
            'endocrinology': ['diabetes', 'hormone', 'endocrine', 'metabolic'],
            'dermatology': ['skin', 'dermatology', 'dermatological'],
            'psychiatry': ['mental', 'psychiatric', 'depression', 'anxiety'],
            'respiratory': ['lung', 'respiratory', 'asthma', 'copd']
        }
        
        for area, keywords in therapeutic_areas.items():
            if any(keyword in text for keyword in keywords):
                return area.title()
        
        return "General Medicine"
    
    def save_articles_to_db(self, db: Session, articles: List[Dict]) -> int:
        """Save articles to database"""
        article_service = ArticleService(db)
        saved_count = 0
        
        for article_data in articles:
            try:
                # Check if article already exists
                existing = db.query(Article).filter(Article.pubmed_id == article_data['pubmed_id']).first()
                if not existing:
                    # Convert authors list to JSON string
                    authors_list = article_data['authors'] if isinstance(article_data['authors'], list) else []
                    article_data['authors'] = json.dumps(authors_list)
                    
                    # Create new article
                    article = Article(**article_data)
                    db.add(article)
                    saved_count += 1
                    print(f"✅ Saved article: {article_data['title'][:50]}...")
                else:
                    print(f"⏭️  Article already exists: {article_data['title'][:50]}...")
                    
            except Exception as e:
                print(f"❌ Error saving article: {e}")
                continue
        
        try:
            db.commit()
            print(f"🎉 Successfully saved {saved_count} new articles to database")
        except Exception as e:
            print(f"❌ Error committing to database: {e}")
            db.rollback()
            saved_count = 0
        
        return saved_count

# Example usage
if __name__ == "__main__":
    pubmed_service = PubMedService()
    
    # Search for oncology articles from the last 7 days
    articles = pubmed_service.search_articles("Oncology", days_back=7)
    
    print(f"Found {len(articles)} articles")
    for article in articles[:3]:  # Show first 3
        print(f"\nTitle: {article['title']}")
        print(f"Authors: {', '.join(article['authors'][:3])}")
        print(f"Journal: {article['journal']}")
        print(f"Date: {article['publication_date']}")
        print(f"PubMed ID: {article['pubmed_id']}") 