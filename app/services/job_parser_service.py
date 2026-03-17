"""
Job description parser service for RAG
"""
import os
import re
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)


class JobParserService:
    """Service for parsing job descriptions"""
    
    def __init__(self):
        self.skills_keywords = {
            "python": ["python", "py", "python3"],
            "react": ["react", "reactjs"],
            "django": ["django", "django rest", "drf"],
            "flask": ["flask"],
            "rest_api": ["rest api", "restful", "restful api", "rest"],
            "mysql": ["mysql"],
            "postgresql": ["postgresql", "postgres", "pg"],
            "mongodb": ["mongodb", "mongo", "nosql"],
            "fastapi": ["fastapi"],
            "fullstack": ["fullstack", "full stack", "full-stack"],
            "ibm": ["ibm", "ibm integration bus", "iib", "websphere", "ace", "app connect enterprise", "esql", "extended sql", "mq", "message queue"],
            "java": ["java", "j2ee", "spring", "hibernate"],
            "javascript": ["javascript", "js", "node", "nodejs"],
            "angular": ["angular", "angularjs"],
            "vue": ["vue", "vuejs"],
            "sql": ["sql", "mysql", "postgresql", "oracle", "oracle sql", "plsql", "pl/sql", "tsql", "mssql", "sqlserver"],
            "oracle": ["oracle", "oracle sql", "plsql", "pl/sql", "oracle database", "oracle db"],
            "aws": ["aws", "amazon web services", "ec2", "s3"],
            "azure": ["azure", "microsoft azure"],
            "docker": ["docker", "containerization"],
            "kubernetes": ["kubernetes", "k8s"],
            "esql": ["esql", "extended sql"]
        }
        
        # Role synonyms for better matching
        self.role_synonyms = {
            "oracle developer": ["sql developer", "database developer", "oracle sql developer", "plsql developer"],
            "sql developer": ["oracle developer", "database developer", "db developer"],
            "database developer": ["sql developer", "oracle developer", "db developer"],
            "ibm developer": ["ibm integration developer", "iib developer", "websphere developer"],
            "integration developer": ["ibm developer", "iib developer", "middleware developer"]
        }
    
    def parse_job_description(self, job_description: str) -> Dict[str, any]:
        """
        Parse job description and extract requirements
        
        Args:
            job_description: The job description text
            
        Returns:
            Dictionary with parsed requirements
        """
        result = {
            "role": None,
            "skills": [],
            "location": None,
            "cost": None,
            "experience": None,
            "raw_text": job_description
        }
        
        # Extract role/title - enhanced with Oracle/SQL patterns and typo tolerance
        role_patterns = [
            r"(?i)(mongodb|mongo)\s*develop[er]*",  # MongoDB developer variations - check this first
            r"(?i)(oracle|sql|database|db)\s*develop[er]*",  # Oracle/SQL developer variations
            r"(?i)(full\s*stack|fullstack)\s*develop?[eor]*",  # Full stack developer variations - check this early
            r"(?i)(python|react|java|node|backend|frontend|ibm|angular|vue)\s*develop?[eor]*",  # Handle typos like "develoeper"
            r"(?i)(software\s*engineer|devops\s*engineer|data\s*engineer)",
            r"(?i)(role[:\s]+)([A-Za-z\s]+?)(?=\n|$)",
            r"(?i)\b(mongodb|mongo|oracle|sql|database|python|react|java|node|backend|frontend|full\s*stack|fullstack|ibm|angular|vue)\s+develop[eor]*\b",
            r"(?i)\b(mongodb|mongo|oracle|sql|database|python|react|java|node|backend|frontend|full\s*stack|fullstack|ibm|angular|vue)\b"
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, job_description)
            if match:
                matched_text = match.group(0).strip().lower()
                
                # Handle Full Stack -> Full Stack developer mapping (check early)
                if "full stack" in matched_text or "fullstack" in matched_text:
                    result["role"] = "full stack developer"
                # Handle MongoDB -> MongoDB developer mapping (check first)
                if "mongodb" in matched_text or "mongo" in matched_text:
                    result["role"] = "mongodb developer"
                # Handle Oracle -> SQL developer mapping
                elif "oracle" in matched_text:
                    result["role"] = "sql developer"  # Map Oracle to SQL developer
                elif "database" in matched_text or "db" in matched_text:
                    result["role"] = "sql developer"
                elif "develop" in matched_text:
                    # Extract the technology part and add "developer"
                    tech_match = re.search(r"(?i)(python|react|java|node|backend|frontend|full\s*stack|fullstack|ibm|angular|vue|sql|mongodb|mongo)", matched_text)
                    if tech_match:
                        tech = tech_match.group(1).lower()
                        # Map mongo to mongodb for consistency
                        if tech == "mongo":
                            tech = "mongodb"
                        # Handle full stack variations
                        elif "full" in tech and "stack" in tech:
                            tech = "full stack"
                        result["role"] = f"{tech} developer"
                else:
                    result["role"] = matched_text.lower()
                break
        
        # If no role found but skills are detected, create role from skills
        if not result["role"]:
            skills = self._extract_skills(job_description)
            if skills:
                result["role"] = f"{skills[0]} developer"
        
        # Extract skills
        result["skills"] = self._extract_skills(job_description)
        
        # Extract location - improved pattern matching with better validation
        location_patterns = [
            r"(?i)(?:in|at|from|based in|located in)\s+([A-Za-z\s]+?)(?:\s|$|,|\.|;)",
            r"(?i)\b(bangalore|bengaluru|chennai|mumbai|delhi|hyderabad|pune|coimbatore|kolkata|gurgaon|noida|ahmedabad|jaipur|lucknow|kanpur|nagpur|indore|thane|bhopal|visakhapatnam|pimpri|patna|vadodara|ludhiana|agra|nashik|faridabad|meerut|rajkot|kalyan|vasai|varanasi|srinagar|aurangabad|dhanbad|amritsar|navi mumbai|allahabad|ranchi|howrah|jabalpur|gwalior|vijayawada|jodhpur|madurai|raipur|kota|chandigarh|guwahati|solapur|hubli|tiruchirappalli|bareilly|mysore|tiruppur|gurgaon|salem|mira|bhiwandi|saharanpur|gorakhpur|bikaner|amravati|noida|jamshedpur|bhilai|cuttack|firozabad|kochi|nellore|bhavnagar|dehradun|durgapur|asansol|rourkela|nanded|kolhapur|ajmer|akola|gulbarga|jamnagar|ujjain|loni|siliguri|jhansi|ulhasnagar|jammu|sangli|mangalore|erode|belgaum|ambattur|tirunelveli|malegaon|gaya|jalgaon|udaipur|maheshtala)\b"
        ]
        
        # Avoid false positives - words that are NOT locations
        non_location_words = {
            'react', 'javascript', 'java', 'python', 'node', 'angular', 'vue', 
            'frontend', 'backend', 'fullstack', 'developer', 'experience', 
            'years', 'plus', 'minimum', 'maximum', 'least', 'most'
        }
        
        for pattern in location_patterns:
            location_match = re.search(pattern, job_description)
            if location_match:
                location = location_match.group(1).strip() if len(location_match.groups()) > 0 else location_match.group(0).strip()
                # Clean up common words
                location = re.sub(r'\b(in|at|from|based|located)\b', '', location, flags=re.IGNORECASE).strip()
                
                # Validate location - avoid false positives
                if location and len(location) > 2 and location.lower() not in non_location_words:
                    result["location"] = location.title()
                    break
        
        # Extract cost/salary
        cost_match = re.search(r"(?i)(cost|salary)[:\s]+(\d+)", job_description)
        if cost_match:
            result["cost"] = int(cost_match.group(2))
        
        # Extract experience - enhanced patterns
        experience_patterns = [
            r"(?i)(\d+)\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)",  # "8+ years experience", "5 years of experience"
            r"(?i)(\d+)\s*plus\s+years?\s+(?:of\s+)?(?:experience|exp)",  # "8 plus years experience"
            r"(?i)(?:experience|exp)[:\s]+(\d+)\+?\s*years?",  # "experience: 8+ years"
            r"(?i)(?:minimum|min|at least)\s+(\d+)\s*years?",  # "minimum 8 years"
            r"(?i)(\d+)\s*to\s*\d+\s*years?",  # "5 to 8 years" - take minimum
            r"(?i)(\d+)\s*-\s*\d+\s*years?",  # "5-8 years" - take minimum
        ]
        
        for pattern in experience_patterns:
            exp_match = re.search(pattern, job_description)
            if exp_match:
                result["experience"] = int(exp_match.group(1))
                break
        
        return result
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        found_skills = []
        text_lower = text.lower()
        
        for skill, keywords in self.skills_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if skill not in found_skills:
                        found_skills.append(skill)
                    break
        
        return found_skills
    
    def match_candidate(self, candidate: Dict, job_requirements: Dict) -> Dict:
        """
        Match a candidate against job requirements
        
        Args:
            candidate: Candidate data from CSV
            job_requirements: Parsed job requirements
            
        Returns:
            Match score and details
        """
        score = 0
        matches = []
        missing = []
        
        # Check role match - case insensitive, exact match required
        if job_requirements.get("role"):
            job_role = job_requirements["role"].lower().strip()
            candidate_role = candidate.get("role", "").lower().strip()
            
            # Extract main role keyword (before "developer" or "engineer")
            job_role_main = job_role
            if "developer" in job_role:
                job_role_main = job_role.replace("developer", "").strip()
            elif "engineer" in job_role:
                job_role_main = job_role.replace("engineer", "").strip()
            
            candidate_role_main = candidate_role
            if "developer" in candidate_role:
                candidate_role_main = candidate_role.replace("developer", "").strip()
            elif "engineer" in candidate_role:
                candidate_role_main = candidate_role.replace("engineer", "").strip()
            
            # Check if main role keywords match (exact match required)
            if job_role_main and job_role_main == candidate_role_main:
                score += 30
                matches.append("Role match")
            else:
                missing.append("Role mismatch")
        
        # Check skills match
        candidate_skills = candidate.get("skills", "").lower()
        required_skills = job_requirements.get("skills", [])
        
        for skill in required_skills:
            if skill in candidate_skills:
                score += 20
                matches.append(f"Skill: {skill}")
        
        # Check location match - case insensitive
        if job_requirements.get("location"):
            job_location = job_requirements["location"].lower()
            candidate_location = candidate.get("location", "").lower()
            if job_location in candidate_location:
                score += 25
                matches.append("Location match")
            else:
                missing.append("Location mismatch")
        
        # Check cost match
        if job_requirements.get("cost"):
            try:
                candidate_cost = int(candidate.get("cost", 0))
                job_cost = job_requirements["cost"]
                if candidate_cost <= job_cost:
                    score += 25
                    matches.append("Cost within budget")
                else:
                    missing.append("Cost exceeds budget")
            except (ValueError, TypeError):
                pass
        
        return {
            "score": score,
            "matches": matches,
            "missing": missing,
            "is_match": score >= 50
        }


# Singleton instance
job_parser_service = JobParserService()
