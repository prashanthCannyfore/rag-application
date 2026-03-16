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
            "mongodb": ["mongodb", "mongo"],
            "fastapi": ["fastapi"],
            "ibm": ["ibm", "ibm integration bus", "iib", "websphere"],
            "java": ["java", "j2ee", "spring", "hibernate"],
            "javascript": ["javascript", "js", "node", "nodejs"],
            "angular": ["angular", "angularjs"],
            "vue": ["vue", "vuejs"],
            "sql": ["sql", "mysql", "postgresql", "oracle"],
            "aws": ["aws", "amazon web services", "ec2", "s3"],
            "azure": ["azure", "microsoft azure"],
            "docker": ["docker", "containerization"],
            "kubernetes": ["kubernetes", "k8s"]
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
        
        # Extract role/title - more flexible pattern with typo tolerance
        role_patterns = [
            r"(?i)(python|react|java|node|backend|frontend|fullstack|ibm|angular|vue)\s*develop[er]*",  # Handle typos like "develpoer"
            r"(?i)(software\s*engineer|devops\s*engineer|data\s*engineer)",
            r"(?i)(role[:\s]+)([A-Za-z\s]+?)(?=\n|$)",
            r"(?i)\b(python|react|java|node|backend|frontend|fullstack|ibm|angular|vue)\s+developer\b",  # More specific pattern
            r"(?i)\b(python|react|java|node|backend|frontend|fullstack|ibm|angular|vue)\b"  # Fallback: just the technology name
        ]
        for pattern in role_patterns:
            match = re.search(pattern, job_description)
            if match:
                matched_text = match.group(0).strip()
                # Clean up the match
                if "develop" in matched_text.lower():
                    # Extract the technology part and add "developer"
                    tech_match = re.search(r"(?i)(python|react|java|node|backend|frontend|fullstack|ibm|angular|vue)", matched_text)
                    if tech_match:
                        result["role"] = f"{tech_match.group(1).lower()} developer"
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
        
        # Extract location - look for city names after "in" or "at", or standalone city names
        location_patterns = [
            r"(?i)\bin\s+([A-Za-z]+)",  # "in Bangalore"
            r"(?i)\bat\s+([A-Za-z]+)",  # "at Bangalore"  
            r"(?i)\b(bangalore|chennai|mumbai|delhi|hyderabad|pune|coimbatore|kolkata)\b"  # Common Indian cities
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, job_description)
            if location_match:
                result["location"] = location_match.group(1).strip()
                break
        
        # Extract cost/salary
        cost_match = re.search(r"(?i)(cost|salary)[:\s]+(\d+)", job_description)
        if cost_match:
            result["cost"] = int(cost_match.group(2))
        
        # Extract experience
        exp_match = re.search(r"(?i)(experience|exp)[:\s]+(\d+)", job_description)
        if exp_match:
            result["experience"] = int(exp_match.group(2))
        
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
