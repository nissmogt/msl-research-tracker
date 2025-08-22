import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
from sqlalchemy.orm import Session
import json
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import threading

from models import Article
from services import ArticleService

class PubMedService:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.api_key = None
        self.delay = 0.1
        self.max_results = 10  # Reduce from 30 to 10
        self.batch_size = 10
    
    def search_articles(self, therapeutic_area: str, days_back: int = 7) -> List[Dict]:
        """Search PubMed for articles - FAST VERSION"""
        start_time = time.time()
        print(f"🔍 Starting PubMed search for '{therapeutic_area}'...")
        
        try:
            # Step 1: Get article IDs
            ids_start = time.time()
            article_ids = self._get_article_ids(therapeutic_area, days_back)
            ids_time = time.time() - ids_start
            print(f"⏱️ Got {len(article_ids)} article IDs in {ids_time:.2f}s")
            
            if not article_ids:
                print("❌ No articles found")
                return []
            
            # Step 2: Batch fetch article details
            fetch_start = time.time()
            articles = self._batch_fetch_articles(article_ids)
            fetch_time = time.time() - fetch_start
            print(f"⏱️ Fetched {len(articles)} article details in {fetch_time:.2f}s")
            
            total_time = time.time() - start_time
            print(f"✅ Total search time: {total_time:.2f}s")
            return articles
            
        except Exception as e:
            total_time = time.time() - start_time
            print(f"❌ Error after {total_time:.2f}s: {e}")
            return []
    
    def _get_article_ids(self, therapeutic_area: str, days_back: int) -> List[str]:
        """Get article IDs from PubMed search"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        start_date_str = start_date.strftime("%Y/%m/%d")
        end_date_str = end_date.strftime("%Y/%m/%d")
        
        query = f'"{therapeutic_area}"[Title/Abstract] AND ("{start_date_str}"[Date - Publication] : "{end_date_str}"[Date - Publication])'
        
        search_url = f"{self.base_url}/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': query,
            'retmode': 'xml',
            'retmax': self.max_results,
            'sort': 'date'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        id_list = root.find('.//IdList')
        
        if id_list is None or len(id_list) == 0:
            return []
        
        return [id_elem.text for id_elem in id_list.findall('Id')]
    
    def _batch_fetch_articles(self, article_ids: List[str]) -> List[Dict]:
        """Fetch multiple articles in parallel - MUCH FASTER!"""
        if not article_ids:
            return []
        
        # Use PubMed's batch fetch API (up to 200 IDs at once!)
        fetch_url = f"{self.base_url}/efetch.fcgi"
        params = {
            'db': 'pubmed',
            'id': ','.join(article_ids),  # Comma-separated IDs
            'retmode': 'xml'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        try:
            response = requests.get(fetch_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse all articles at once
            return self._parse_batch_response(response.content)
            
        except Exception as e:
            print(f"Error in batch fetch: {e}")
            return []
    
    def _parse_batch_response(self, xml_content: bytes) -> List[Dict]:
        """Parse multiple articles from XML response"""
        articles = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Find all articles in the response
            for article in root.findall('.//PubmedArticle'):
                try:
                    article_data = self._parse_single_article(article)
                    if article_data and article_data.get('abstract') and article_data['abstract'].strip():
                        articles.append(article_data)
                except Exception as e:
                    print(f"Error parsing article: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error parsing XML: {e}")
        
        return articles
    
    def _parse_single_article(self, article) -> Optional[Dict]:
        """Parse a single article from XML"""
        try:
            medline_citation = article.find('.//MedlineCitation')
            if medline_citation is None:
                return None
            
            # Extract PubMed ID
            pmid_elem = medline_citation.find('.//PMID')
            pubmed_id = pmid_elem.text if pmid_elem is not None else ""
            
            # Extract title
            title_elem = medline_citation.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title available"
            
            # Extract abstract
            abstract_elem = medline_citation.find('.//Abstract/AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else ""
            
            # Extract authors
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
            
            # Extract journal
            journal_elem = medline_citation.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Extract publication date
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
            
            return {
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
            
        except Exception as e:
            print(f"Error parsing single article: {e}")
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