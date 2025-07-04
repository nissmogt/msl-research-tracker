import requests
import json
from typing import List, Dict, Optional
from datetime import datetime

class ClinicalTrialsService:
    def __init__(self):
        self.base_url = "https://classic.clinicaltrials.gov/ct2/results"
    
    def search_trials(self, query: str, max_results: int = 20) -> List[Dict]:
        """Search clinical trials by condition, therapeutic area, or keyword"""
        try:
            # Use a simpler approach with the results API
            params = {
                'term': query,
                'recrs': 'a',  # All studies
                'type': 'Intr',  # Interventional studies
                'rslt': 'With',  # With results
                'displayxml': 'false'
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # For now, return mock data to test the frontend
            # In a real implementation, you would parse the XML response
            mock_trials = [
                {
                    'nct_id': 'NCT12345678',
                    'title': f'Clinical Trial for {query} Treatment',
                    'official_title': f'A Phase 2 Study of Novel Treatment for {query}',
                    'condition': query,
                    'intervention': 'Drug: Experimental Treatment',
                    'phase': 'Phase 2',
                    'sponsor': 'University Medical Center',
                    'sponsor_class': 'Other',
                    'status': 'Recruiting',
                    'start_date': 'January 2024',
                    'completion_date': 'December 2025',
                    'enrollment': '100',
                    'study_type': 'Interventional',
                    'study_design': {'Allocation': 'Randomized', 'Intervention Model': 'Parallel Assignment'},
                    'description': f'This is a clinical trial investigating a new treatment approach for {query}. The study aims to evaluate the safety and efficacy of the experimental treatment compared to standard care.',
                    'link': 'https://clinicaltrials.gov/study/NCT12345678',
                    'source': 'ClinicalTrials.gov'
                },
                {
                    'nct_id': 'NCT87654321',
                    'title': f'Advanced {query} Therapy Study',
                    'official_title': f'Evaluation of Advanced Therapeutic Approaches in {query}',
                    'condition': query,
                    'intervention': 'Biological: Advanced Therapy',
                    'phase': 'Phase 3',
                    'sponsor': 'Pharmaceutical Company',
                    'sponsor_class': 'Industry',
                    'status': 'Active, not recruiting',
                    'start_date': 'March 2023',
                    'completion_date': 'June 2026',
                    'enrollment': '500',
                    'study_type': 'Interventional',
                    'study_design': {'Allocation': 'Randomized', 'Intervention Model': 'Crossover Assignment'},
                    'description': f'This Phase 3 study evaluates the effectiveness of advanced therapeutic approaches for {query} patients. The study includes multiple treatment arms and comprehensive safety monitoring.',
                    'link': 'https://clinicaltrials.gov/study/NCT87654321',
                    'source': 'ClinicalTrials.gov'
                }
            ]
            
            return mock_trials[:max_results]
            
        except Exception as e:
            print(f"Error searching ClinicalTrials.gov: {e}")
            # Return mock data for testing
            return [
                {
                    'nct_id': 'NCT12345678',
                    'title': f'Clinical Trial for {query} Treatment',
                    'official_title': f'A Phase 2 Study of Novel Treatment for {query}',
                    'condition': query,
                    'intervention': 'Drug: Experimental Treatment',
                    'phase': 'Phase 2',
                    'sponsor': 'University Medical Center',
                    'sponsor_class': 'Other',
                    'status': 'Recruiting',
                    'start_date': 'January 2024',
                    'completion_date': 'December 2025',
                    'enrollment': '100',
                    'study_type': 'Interventional',
                    'study_design': {'Allocation': 'Randomized', 'Intervention Model': 'Parallel Assignment'},
                    'description': f'This is a clinical trial investigating a new treatment approach for {query}. The study aims to evaluate the safety and efficacy of the experimental treatment compared to standard care.',
                    'link': 'https://clinicaltrials.gov/study/NCT12345678',
                    'source': 'ClinicalTrials.gov'
                }
            ]
    
    def _format_trial(self, study: Dict) -> Optional[Dict]:
        """Format a single trial from the API response"""
        try:
            # Extract basic info from StudyFields format
            fields = study.get('StudyFields', {})
            nct_id = fields.get('NCTId', [''])[0] if fields.get('NCTId') else ''
            brief_title = fields.get('BriefTitle', [''])[0] if fields.get('BriefTitle') else ''
            official_title = fields.get('OfficialTitle', [''])[0] if fields.get('OfficialTitle') else ''
            condition = fields.get('Condition', [])
            intervention = fields.get('InterventionName', [])
            phase = fields.get('Phase', [])
            sponsor = fields.get('LeadSponsorName', [''])[0] if fields.get('LeadSponsorName') else ''
            sponsor_class = fields.get('LeadSponsorClass', [''])[0] if fields.get('LeadSponsorClass') else ''
            status = fields.get('OverallStatus', [''])[0] if fields.get('OverallStatus') else ''
            start_date = fields.get('StartDate', [''])[0] if fields.get('StartDate') else ''
            completion_date = fields.get('CompletionDate', [''])[0] if fields.get('CompletionDate') else ''
            enrollment = fields.get('EnrollmentCount', [''])[0] if fields.get('EnrollmentCount') else ''
            study_type = fields.get('StudyType', [''])[0] if fields.get('StudyType') else ''
            study_design = fields.get('StudyDesignInfo', [{}])[0] if fields.get('StudyDesignInfo') else {}
            description = fields.get('DetailedDescription', [''])[0] if fields.get('DetailedDescription') else ''
            
            # Format dates
            start_date_formatted = self._format_date(start_date)
            completion_date_formatted = self._format_date(completion_date)
            
            # Build trial data
            trial_data = {
                'nct_id': nct_id,
                'title': brief_title or official_title,
                'official_title': official_title,
                'condition': ', '.join(condition) if condition else '',
                'intervention': ', '.join(intervention) if intervention else '',
                'phase': ', '.join(phase) if phase else '',
                'sponsor': sponsor,
                'sponsor_class': sponsor_class,
                'status': status,
                'start_date': start_date_formatted,
                'completion_date': completion_date_formatted,
                'enrollment': enrollment,
                'study_type': study_type,
                'study_design': study_design,
                'description': description,
                'link': f"https://clinicaltrials.gov/study/{nct_id}",
                'source': 'ClinicalTrials.gov'
            }
            
            return trial_data
            
        except Exception as e:
            print(f"Error formatting trial {study.get('NCTId', 'unknown')}: {e}")
            return None
    
    def _format_date(self, date_str: str) -> str:
        """Format date string from API to readable format"""
        if not date_str:
            return ''
        
        try:
            # ClinicalTrials.gov dates are typically in YYYY-MM-DD format
            if len(date_str) >= 10:
                date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
                return date_obj.strftime('%B %Y')
            return date_str
        except:
            return date_str
    
    def get_trial_details(self, nct_id: str) -> Optional[Dict]:
        """Get detailed information for a specific trial"""
        try:
            # For now, return mock data
            return {
                'nct_id': nct_id,
                'title': f'Detailed Trial Information for {nct_id}',
                'official_title': f'Comprehensive Study of Treatment for {nct_id}',
                'condition': 'Oncology',
                'intervention': 'Drug: Experimental Treatment',
                'phase': 'Phase 2',
                'sponsor': 'University Medical Center',
                'sponsor_class': 'Other',
                'status': 'Recruiting',
                'start_date': 'January 2024',
                'completion_date': 'December 2025',
                'enrollment': '100',
                'study_type': 'Interventional',
                'study_design': {'Allocation': 'Randomized', 'Intervention Model': 'Parallel Assignment'},
                'description': f'This is a detailed clinical trial investigating a new treatment approach. The study aims to evaluate the safety and efficacy of the experimental treatment compared to standard care. This trial represents a significant advancement in the field and has the potential to change treatment paradigms.',
                'link': f'https://clinicaltrials.gov/study/{nct_id}',
                'source': 'ClinicalTrials.gov'
            }
            
        except Exception as e:
            print(f"Error getting trial details for {nct_id}: {e}")
            return None

# Example usage
if __name__ == "__main__":
    service = ClinicalTrialsService()
    
    # Search for oncology trials
    trials = service.search_trials("oncology", max_results=5)
    
    print(f"Found {len(trials)} trials")
    for trial in trials[:2]:  # Show first 2
        print(f"\nTitle: {trial['title']}")
        print(f"NCT ID: {trial['nct_id']}")
        print(f"Status: {trial['status']}")
        print(f"Phase: {trial['phase']}")
        print(f"Sponsor: {trial['sponsor']}") 