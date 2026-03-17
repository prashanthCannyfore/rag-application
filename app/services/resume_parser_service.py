"""
Resume parsing service to extract location, cost, and other details from resume content
"""
import re
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Fix garbled PDF text by inserting spaces at word boundaries"""
    if not text:
        return text
    # Insert space before uppercase letters that follow lowercase (CamelCase merge)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Insert space before digits that follow letters and vice versa
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    # Fix common PDF artifacts: words glued with punctuation missing spaces
    text = re.sub(r'([a-z]{2,})((?:and|or|in|to|of|for|with|the|is|are|was|were|has|have|that|this|from|by|on|at|as|an|a)\b)', r'\1 \2', text, flags=re.IGNORECASE)
    # Collapse multiple spaces and clean up
    text = re.sub(r' {2,}', ' ', text)
    # Fix missing space after punctuation
    text = re.sub(r'([.,;:])([A-Za-z])', r'\1 \2', text)
    return text.strip()

class ResumeParserService:
    """Service for parsing resume content to extract structured information"""
    
    def __init__(self):
        # Common Indian cities and variations
        self.indian_cities = [
            'bangalore', 'bengaluru', 'chennai', 'mumbai', 'delhi', 'hyderabad', 
            'pune', 'coimbatore', 'kolkata', 'gurgaon', 'noida', 'ahmedabad',
            'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore', 'thane', 'bhopal',
            'visakhapatnam', 'pimpri', 'patna', 'vadodara', 'ludhiana', 'agra',
            'nashik', 'faridabad', 'meerut', 'rajkot', 'kalyan', 'vasai',
            'varanasi', 'srinagar', 'aurangabad', 'dhanbad', 'amritsar',
            'navi mumbai', 'allahabad', 'ranchi', 'howrah', 'jabalpur',
            'gwalior', 'vijayawada', 'jodhpur', 'madurai', 'raipur', 'kota',
            'chandigarh', 'guwahati', 'solapur', 'hubli', 'tiruchirappalli',
            'bareilly', 'mysore', 'tiruppur', 'salem', 'mira', 'bhiwandi',
            'saharanpur', 'gorakhpur', 'bikaner', 'amravati', 'jamshedpur',
            'bhilai', 'cuttack', 'firozabad', 'kochi', 'nellore', 'bhavnagar',
            'dehradun', 'durgapur', 'asansol', 'rourkela', 'nanded', 'kolhapur',
            'ajmer', 'akola', 'gulbarga', 'jamnagar', 'ujjain', 'loni',
            'siliguri', 'jhansi', 'ulhasnagar', 'jammu', 'sangli', 'mangalore',
            'erode', 'belgaum', 'ambattur', 'tirunelveli', 'malegaon', 'gaya',
            'jalgaon', 'udaipur', 'maheshtala'
        ]
        
        # Currency patterns for Indian context
        self.currency_patterns = [
            r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',  # ₹50,000 or ₹50000
            r'rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',  # Rs. 50000
            r'inr\s*(\d+(?:,\d+)*(?:\.\d+)?)',  # INR 50000
            r'(\d+(?:,\d+)*)\s*(?:rs|rupees|inr|₹)',  # 50000 Rs
            r'(\d+(?:,\d+)*)\s*(?:lpa|per\s*annum)',  # 5 LPA
            r'(\d+(?:,\d+)*)\s*(?:k|thousand)\s*(?:per\s*month|pm|monthly)?',  # 50k per month
            r'(\d+(?:,\d+)*)\s*(?:l|lakh|lakhs)\s*(?:per\s*annum|pa|annually)?'  # 5 lakh per annum
        ]
    
    def extract_location(self, resume_text: str) -> Optional[str]:
        """Extract location information from resume text"""
        if not resume_text:
            return None
        
        text_lower = resume_text.lower()
        
        # Location patterns to search for
        location_patterns = [
            r'(?:address|location|based\s+in|residing\s+in|current\s+location|city)[\s:]+([^\n,]+)',
            r'(?:phone|mobile|contact)[\s:]+[+\d\s()-]+[\s,]+([a-zA-Z\s]+)',
            r'(?:email|mail)[\s:]+[^\s@]+@[^\s,]+[\s,]+([a-zA-Z\s]+)',
            r'\b(?:' + '|'.join(self.indian_cities) + r')\b'
        ]
        
        found_locations = []
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    location = match.group(1).strip()
                else:
                    location = match.group(0).strip()
                
                # Clean up the location
                location = re.sub(r'[^\w\s]', ' ', location)
                location = ' '.join(location.split())
                
                # Check if it's a valid city
                if any(city in location.lower() for city in self.indian_cities):
                    found_locations.append(location.title())
        
        # Return the most likely location (first valid city found)
        if found_locations:
            return found_locations[0]
        
        return None
    
    def extract_salary(self, resume_text: str) -> Optional[str]:
        """Extract salary/cost information from resume text"""
        if not resume_text:
            return None
        
        text_lower = resume_text.lower()
        
        # Salary context patterns
        salary_contexts = [
            r'(?:salary|compensation|package|ctc|expected\s+salary|current\s+salary|pay)[\s:]+([^\n]+)',
            r'(?:earning|income|remuneration)[\s:]+([^\n]+)',
            r'(?:budget|rate|cost)[\s:]+([^\n]+)'
        ]
        
        found_salaries = []
        
        # First, look for salary in context
        for context_pattern in salary_contexts:
            context_matches = re.finditer(context_pattern, text_lower, re.IGNORECASE)
            for context_match in context_matches:
                context_text = context_match.group(1)
                
                # Look for currency patterns within this context
                for currency_pattern in self.currency_patterns:
                    currency_matches = re.finditer(currency_pattern, context_text, re.IGNORECASE)
                    for currency_match in currency_matches:
                        amount = currency_match.group(1)
                        # Clean up amount
                        amount = re.sub(r'[^\d,.]', '', amount)
                        if amount:
                            found_salaries.append(self._format_salary(amount))
        
        # If no contextual salary found, look for any currency patterns
        if not found_salaries:
            for currency_pattern in self.currency_patterns:
                currency_matches = re.finditer(currency_pattern, text_lower, re.IGNORECASE)
                for currency_match in currency_matches:
                    amount = currency_match.group(1)
                    # Clean up amount
                    amount = re.sub(r'[^\d,.]', '', amount)
                    if amount and self._is_likely_salary(amount):
                        found_salaries.append(self._format_salary(amount))
        
        # Return the most reasonable salary found
        if found_salaries:
            return found_salaries[0]
        
        return None
    
    def _is_likely_salary(self, amount_str: str) -> bool:
        """Check if the amount is likely to be a salary"""
        try:
            # Remove commas and convert to float
            amount = float(amount_str.replace(',', ''))
            
            # Reasonable salary range (in INR per month or per annum)
            # Monthly: 10,000 to 10,00,000 (10k to 10L)
            # Annual: 1,20,000 to 1,20,00,000 (1.2L to 1.2Cr)
            return 10000 <= amount <= 12000000
        except:
            return False
    
    def _format_salary(self, amount_str: str) -> str:
        """Format salary amount consistently"""
        try:
            amount = float(amount_str.replace(',', ''))
            
            if amount >= 100000:  # 1 lakh or more
                if amount >= 10000000:  # 1 crore or more
                    return f"₹{amount/10000000:.1f} Cr"
                else:
                    return f"₹{amount/100000:.1f} L"
            else:
                return f"₹{amount:,.0f}"
        except:
            return f"₹{amount_str}"
    
    def extract_experience(self, resume_text: str) -> Optional[str]:
        """Extract years of experience from resume text"""
        if not resume_text:
            return None
        
        text_lower = resume_text.lower()
        
        # Enhanced experience patterns to catch more variations
        experience_patterns = [
            # Standard patterns
            r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?\s+(?:of\s+)?(?:total\s+)?experience',
            r'(?:total\s+)?experience[\s:]+(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?',
            r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*yrs?\s+(?:of\s+)?(?:experience|exp)',
            
            # New patterns for the resume formats found
            r'(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?(?:hands-on\s+)?experience',
            r'having\s+(?:around\s+)?(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?(?:hands-on\s+)?experience',
            r'(\d+(?:\.\d+)?)\s*\+?\s*years?\s+exp\s+as',
            r'with\s+over\s+(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?\s+(?:of\s+)?(?:expertise|experience)',
            r'experienced\s+\w+\s+developer\s+with\s+over\s+(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?',
            
            # Additional comprehensive patterns
            r'(?:over|more than|above)\s+(\d+(?:\.\d+)?)\s*years?\s+(?:of\s+)?experience',
            r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?\s+(?:in|of)\s+(?:software|development|programming|web)',
            r'experience\s*:\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?',
            r'(\d+(?:\.\d+)?)\s*years?\s+(?:of\s+)?(?:professional\s+)?(?:work\s+)?experience'
        ]
        
        max_experience = 0
        found_experience = False
        
        for pattern in experience_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                try:
                    years = float(match.group(1))
                    if years > max_experience and years <= 50:  # Reasonable upper limit
                        max_experience = years
                        found_experience = True
                except (ValueError, IndexError):
                    continue
        
        if found_experience:
            return f"{int(max_experience)} years" if max_experience == int(max_experience) else f"{max_experience} years"
        
        return None
    
    def extract_experience_years(self, resume_text: str) -> Optional[int]:
        """Extract years of experience as integer"""
        experience_str = self.extract_experience(resume_text)
        if experience_str:
            # Extract number from string like "5 years"
            match = re.search(r'(\d+(?:\.\d+)?)', experience_str)
            if match:
                return int(float(match.group(1)))
        return None
    
    def extract_email(self, resume_text: str) -> Optional[str]:
        """Extract email address from resume text"""
        if not resume_text:
            return None
        match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text)
        return match.group(0).lower() if match else None

    def extract_phone(self, resume_text: str) -> Optional[str]:
        """Extract phone number from resume text"""
        if not resume_text:
            return None
        patterns = [
            r'(?:\+91[\s-]?)?[6-9]\d{9}',           # Indian mobile
            r'(?:\+91[\s-]?)?\d{3,5}[\s-]\d{6,8}',  # Landline
            r'\+\d{1,3}[\s-]\d{6,12}'                # International
        ]
        for pattern in patterns:
            match = re.search(pattern, resume_text)
            if match:
                return re.sub(r'[\s-]', '', match.group(0))
        return None

    def extract_education(self, resume_text: str) -> List[str]:
        """Extract education qualifications from resume text"""
        if not resume_text:
            return []

        degrees = []
        patterns = [
            r'\b(b\.?tech|b\.?e\.?|bachelor\s+of\s+\w+|b\.?sc\.?)\b',
            r'\b(m\.?tech|m\.?e\.?|master\s+of\s+\w+|m\.?sc\.?|mba|m\.?b\.?a\.?)\b',
            r'\b(ph\.?d\.?|doctorate)\b',
            r'\b(diploma\s+in\s+[\w\s]+)\b',
            r'\b(b\.?c\.?a\.?|m\.?c\.?a\.?)\b',
        ]
        seen = set()
        for pattern in patterns:
            for match in re.finditer(pattern, resume_text, re.IGNORECASE):
                degree = match.group(0).strip().upper()
                if degree not in seen:
                    seen.add(degree)
                    degrees.append(degree)
        return degrees

    def extract_certifications(self, resume_text: str) -> List[str]:
        """Extract certifications from resume text"""
        if not resume_text:
            return []

        cert_keywords = [
            r'aws\s+certified[\w\s]*',
            r'azure\s+certified[\w\s]*',
            r'google\s+cloud[\w\s]*certified[\w\s]*',
            r'pmp[\w\s]*certification',
            r'cissp[\w\s]*',
            r'oracle\s+certified[\w\s]*',
            r'scrum\s+master[\w\s]*',
            r'itil[\w\s]*',
            r'ibm\s+certified[\w\s]*',
            r'red\s+hat[\w\s]*certified[\w\s]*',
            r'certified\s+[\w\s]+(?:developer|architect|engineer|professional|associate)',
        ]
        found = []
        seen = set()
        for pattern in cert_keywords:
            for match in re.finditer(pattern, resume_text, re.IGNORECASE):
                cert = ' '.join(match.group(0).split()).title()
                if cert not in seen:
                    seen.add(cert)
                    found.append(cert)
        return found

    def extract_companies(self, resume_text: str) -> List[str]:
        """Extract previous companies/employers from resume text"""
        if not resume_text:
            return []

        # Clean the text first to fix merged words from PDF
        resume_text = clean_text(resume_text)

        companies = []
        patterns = [
            r'(?:worked\s+at|employed\s+(?:at|by|with)|company\s*[:–-]|employer\s*[:–-]|organization\s*[:–-])\s*([A-Z][A-Za-z0-9\s&.,]+)',
            r'(?:^|\n)\s*([A-Z][A-Za-z0-9\s&.]+(?:Pvt\.?\s*Ltd\.?|Inc\.?|Corp\.?|Technologies|Solutions|Systems|Consulting|Services|Software))',
        ]
        seen = set()
        for pattern in patterns:
            for match in re.finditer(pattern, resume_text, re.MULTILINE):
                company = match.group(1).strip().rstrip('.,')
                if company and len(company) > 3 and len(company) < 60 and company not in seen:
                    seen.add(company)
                    companies.append(company)
        return companies[:5]  # Return top 5

    def extract_summary(self, resume_text: str) -> Optional[str]:
        """Extract professional summary/objective from resume"""
        if not resume_text:
            return None

        patterns = [
            r'(?:professional\s+summary|summary|objective|profile|about\s+me)\s*[:\n]+\s*([^\n]{50,500})',
            r'(?:career\s+objective|career\s+summary)\s*[:\n]+\s*([^\n]{50,500})',
        ]
        for pattern in patterns:
            match = re.search(pattern, resume_text, re.IGNORECASE | re.DOTALL)
            if match:
                summary = ' '.join(match.group(1).split())
                return clean_text(summary)[:400]

        # Fallback: first meaningful paragraph (50+ chars)
        lines = [l.strip() for l in resume_text.split('\n') if len(l.strip()) > 50]
        if lines:
            return clean_text(lines[0])[:400]
        return None

    def extract_notice_period(self, resume_text: str) -> Optional[str]:
        """Extract notice period from resume"""
        if not resume_text:
            return None
        patterns = [
            r'notice\s+period\s*[:\-]?\s*([^\n,]{3,30})',
            r'(\d+\s+(?:days?|weeks?|months?))\s+notice',
            r'available\s+(?:to\s+join\s+)?(?:in|within)\s+([^\n,]{3,30})',
            r'immediate(?:ly)?\s+available',
        ]
        for pattern in patterns:
            match = re.search(pattern, resume_text, re.IGNORECASE)
            if match:
                return match.group(0).strip().title()
        return None

    def parse_resume(self, resume_text: str, filename: str = "") -> Dict:
        """
        Parse resume text and extract structured information

        Returns:
            Dictionary with extracted information
        """
        # Clean garbled PDF text (merged words) before any extraction
        cleaned = clean_text(resume_text) if resume_text else resume_text
        return {
            "name": self._extract_name_from_filename(filename),
            "location": self.extract_location(cleaned),
            "salary": self.extract_salary(cleaned),
            "experience": self.extract_experience(cleaned),
            "skills": self._extract_skills_summary(cleaned),
            "email": self.extract_email(cleaned),
            "phone": self.extract_phone(cleaned),
            "education": self.extract_education(cleaned),
            "certifications": self.extract_certifications(cleaned),
            "companies": self.extract_companies(cleaned),
            "summary": self.extract_summary(cleaned),
            "notice_period": self.extract_notice_period(cleaned),
        }
    
    def _extract_name_from_filename(self, filename: str) -> str:
        """Extract candidate name from filename"""
        if not filename:
            return "Unknown"
        
        # Remove file extension and common suffixes
        name = filename.replace('.pdf', '').replace('.doc', '').replace('.docx', '')
        name = re.sub(r'(?i)(_profile|_resume|_cv|\s+profile|\s+resume|\s+cv)', '', name)
        
        # Replace underscores and hyphens with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Clean up spacing
        name = ' '.join(name.split())
        
        return name.title() if name else "Unknown"
    
    def _extract_skills_summary(self, resume_text: str) -> str:
        """Extract a brief skills summary from resume text"""
        if not resume_text:
            return "See resume content"
        
        text_lower = resume_text.lower()
        
        # Common technical skills to look for
        common_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'aws', 'azure',
            'docker', 'kubernetes', 'git', 'jenkins', 'spring', 'django',
            'flask', 'express', 'html', 'css', 'typescript', 'php', 'c++',
            'c#', 'ruby', 'go', 'rust', 'scala', 'kotlin', 'swift', 'ibm',
            'iib', 'ace', 'mq', 'websphere', 'esql', 'soap', 'rest', 'api'
        ]
        
        found_skills = []
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill.upper() if skill in ['sql', 'api', 'aws', 'ibm', 'iib'] else skill.title())
        
        if found_skills:
            return ', '.join(found_skills[:8])  # Limit to first 8 skills
        
        return "See resume content"

# Global instance
resume_parser_service = ResumeParserService()