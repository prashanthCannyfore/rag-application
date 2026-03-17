"""
Enhanced candidate matching service for RAG Resume Analyzer
"""
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

class CandidateMatchingService:
    """Service for matching candidates with job requirements"""
    
    def __init__(self):
        self.skill_synonyms = {
            "javascript": ["js", "javascript", "node", "nodejs"],
            "react": ["react", "reactjs", "react.js"],
            "python": ["python", "py", "python3"],
            "java": ["java", "j2ee", "spring"],
            "sql": ["sql", "mysql", "postgresql", "postgres", "oracle"],
            "aws": ["aws", "amazon web services", "ec2", "s3"],
            "docker": ["docker", "containerization"],
            "kubernetes": ["kubernetes", "k8s"],
            "angular": ["angular", "angularjs"],
            "vue": ["vue", "vuejs", "vue.js"],
            "typescript": ["typescript", "ts"],
            "mongodb": ["mongodb", "mongo"],
            "redis": ["redis"],
            "elasticsearch": ["elasticsearch", "elastic"],
            "graphql": ["graphql", "graph ql"],
            "rest": ["rest", "restful", "rest api"],
            "microservices": ["microservices", "micro services"],
            "ibm": ["ibm", "iib", "websphere", "ibm integration bus", "ace", "app connect enterprise", "esql", "extended sql"],
            "esql": ["esql", "extended sql"],
            "mq": ["mq", "message queue", "ibm mq"],
            "ace": ["ace", "app connect enterprise", "ibm ace"],
            "iib": ["iib", "integration bus", "ibm integration bus"],
            "websphere": ["websphere", "was", "websphere application server"],
            "datapower": ["datapower", "ibm datapower"],
            "api_connect": ["api connect", "apic", "ibm api connect"]
        }
    
    def normalize_name(self, name: str) -> str:
        """Normalize name for better matching"""
        if not name:
            return ""
        
        # Remove common suffixes and prefixes
        name = re.sub(r'\b(mr|mrs|ms|dr|prof)\.?\s*', '', name.lower())
        name = re.sub(r'\s+(jr|sr|ii|iii)\.?\s*$', '', name)
        
        # Clean up spacing and special characters
        name = re.sub(r'[^\w\s]', ' ', name)
        name = ' '.join(name.split())  # Normalize whitespace
        
        return name.strip()
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using multiple methods"""
        if not name1 or not name2:
            return 0.0
        
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # Split into parts
        parts1 = norm1.split()
        parts2 = norm2.split()
        
        if not parts1 or not parts2:
            return 0.0
        
        # Check for exact first name match
        if parts1[0] == parts2[0]:
            return 0.9
        
        # Check for substring match in first names
        if parts1[0] in parts2[0] or parts2[0] in parts1[0]:
            return 0.7
        
        # Use sequence matcher for overall similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost score if any name part matches exactly
        for p1 in parts1:
            for p2 in parts2:
                if p1 == p2 and len(p1) > 2:  # Avoid matching short words
                    similarity = max(similarity, 0.8)
        
        return similarity
    
    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name for better matching"""
        if not skill:
            return ""
        
        skill = skill.lower().strip()
        skill = re.sub(r'[^\w\s]', ' ', skill)
        skill = ' '.join(skill.split())
        
        # Check for synonyms
        for canonical, synonyms in self.skill_synonyms.items():
            if skill in synonyms:
                return canonical
        
        return skill
    
    def _is_valid_substring_match(self, req_skill: str, cand_skill: str) -> bool:
        """
        Check if substring match is valid, avoiding false positives like java/javascript
        """
        # Define problematic pairs that should NOT match
        false_positive_pairs = [
            ("java", "javascript"),
            ("script", "javascript"),  # Avoid "script" matching "javascript"
        ]
        
        # Check for known false positives
        for req, cand in false_positive_pairs:
            if (req_skill == req and cand_skill == cand) or (req_skill == cand and cand_skill == req):
                return False
        
        # Allow substring match only if:
        # 1. One skill is clearly an extension of another (like react/reactjs)
        # 2. The shorter skill is at least 4 characters (avoid very short matches)
        # 3. The match makes semantic sense
        
        if len(req_skill) < 4 and len(cand_skill) < 4:
            return False
            
        # Check if one is a clear extension of the other
        if req_skill in cand_skill:
            # Allow matches like: react -> reactjs, node -> nodejs, sql -> mysql
            # But not: java -> javascript (different technologies)
            if req_skill == "java" and "javascript" in cand_skill:
                return False
            return True
            
        if cand_skill in req_skill:
            # Allow reverse matches
            if cand_skill == "java" and "javascript" in req_skill:
                return False
            return True
            
        return False
    
    def calculate_skill_match(self, candidate_skills: str, required_skills: List[str]) -> Tuple[float, List[str]]:
        """Calculate skill match score and return matched skills"""
        if not candidate_skills or not required_skills:
            return 0.0, []
        
        # Parse candidate skills
        candidate_skill_list = [self.normalize_skill(s.strip()) 
                              for s in re.split(r'[,;|]', candidate_skills.lower())]
        candidate_skill_list = [s for s in candidate_skill_list if s]
        
        # Normalize required skills
        required_skill_list = [self.normalize_skill(s) for s in required_skills]
        required_skill_list = [s for s in required_skill_list if s]
        
        if not candidate_skill_list or not required_skill_list:
            return 0.0, []
        
        matched_skills = []
        total_matches = 0
        
        for req_skill in required_skill_list:
            best_match = 0
            best_match_skill = None
            
            # Special handling for fullstack - more restrictive
            if req_skill == "fullstack":
                # Modern web frontend skills
                frontend_skills = ["react", "angular", "vue", "javascript", "typescript", "html", "css"]
                # Modern web backend skills (exclude enterprise integration)
                backend_skills = ["nodejs", "python", "java", "sql", "mongodb", "postgresql", "mysql"]
                # Integration/Enterprise skills that disqualify fullstack
                integration_skills = ["iib", "ibm", "ace", "mq", "websphere", "esql", "datapower", "soap"]
                
                frontend_count = sum(1 for skill in frontend_skills if any(skill in cand_skill for cand_skill in candidate_skill_list))
                backend_count = sum(1 for skill in backend_skills if any(skill in cand_skill for cand_skill in candidate_skill_list))
                integration_count = sum(1 for skill in integration_skills if any(skill in cand_skill for cand_skill in candidate_skill_list))
                
                # Disqualify if primarily integration developer
                if integration_count >= 2:
                    best_match = 0.0  # Integration developers are not fullstack web developers
                    best_match_skill = None
                elif frontend_count >= 2 and backend_count >= 2:
                    best_match = 1.0  # Strong fullstack match
                    best_match_skill = "fullstack"
                elif frontend_count >= 1 and backend_count >= 1:
                    best_match = 0.8  # Moderate fullstack match
                    best_match_skill = "fullstack"
                elif frontend_count >= 2 or backend_count >= 2:
                    best_match = 0.6  # Partial fullstack match
                    best_match_skill = "fullstack"
            else:
                # Regular skill matching
                for cand_skill in candidate_skill_list:
                    # Exact match
                    if req_skill == cand_skill:
                        best_match = 1.0
                        best_match_skill = req_skill
                        break
                    
                    # Improved substring match - avoid false positives like java/javascript
                    elif self._is_valid_substring_match(req_skill, cand_skill):
                        match_score = 0.8
                        if match_score > best_match:
                            best_match = match_score
                            best_match_skill = req_skill
                    
                    # Fuzzy match for typos
                    else:
                        similarity = SequenceMatcher(None, req_skill, cand_skill).ratio()
                        if similarity > 0.8 and similarity > best_match:
                            best_match = similarity * 0.7  # Reduce score for fuzzy matches
                            best_match_skill = req_skill
            
            if best_match > 0.5:  # Threshold for considering a match
                total_matches += best_match
                if best_match_skill:
                    matched_skills.append(best_match_skill)
        
        # Calculate percentage of required skills matched
        match_percentage = total_matches / len(required_skill_list)
        
        return min(match_percentage, 1.0), matched_skills
    
    def calculate_location_match(self, candidate_location: str, required_location: str, strict: bool = False) -> float:
        """Calculate location match score"""
        if not candidate_location or not required_location:
            return 0.0 if strict else 0.5  # Neutral score if location not specified
        
        cand_loc = self.normalize_name(candidate_location)
        req_loc = self.normalize_name(required_location)
        
        if cand_loc == req_loc:
            return 1.0
        
        if strict:
            return 0.0  # Strict mode: must match exactly
        
        # Check for substring match (e.g., "Bangalore" matches "Bengaluru")
        if cand_loc in req_loc or req_loc in cand_loc:
            return 0.8
        
        # Use fuzzy matching for typos
        similarity = SequenceMatcher(None, cand_loc, req_loc).ratio()
        return similarity if similarity > 0.6 else 0.0
    
    def match_candidate_to_job(
        self, 
        candidate: Dict, 
        job_requirements: Dict, 
        strict_location: bool = False
    ) -> Dict:
        """
        Match a candidate against job requirements
        
        Returns:
            Dict with match score, details, and reasoning
        """
        match_details = {
            "is_match": False,
            "total_score": 0.0,
            "skill_score": 0.0,
            "location_score": 0.0,
            "role_score": 0.0,
            "matched_skills": [],
            "reasoning": []
        }
        
        # Role matching
        candidate_role = candidate.get("role", "")
        required_role = job_requirements.get("role", "")
        
        if candidate_role and required_role:
            role_similarity = SequenceMatcher(None, 
                                            candidate_role.lower(), 
                                            required_role.lower()).ratio()
            match_details["role_score"] = role_similarity
            
            if role_similarity > 0.7:
                match_details["reasoning"].append(f"Role match: {candidate_role} ≈ {required_role}")
        
        # Skill matching
        candidate_skills = candidate.get("skills", "")
        required_skills = job_requirements.get("skills", [])
        
        if required_skills:
            skill_score, matched_skills = self.calculate_skill_match(candidate_skills, required_skills)
            match_details["skill_score"] = skill_score
            match_details["matched_skills"] = matched_skills
            
            if matched_skills:
                match_details["reasoning"].append(f"Skills matched: {', '.join(matched_skills)}")
        
        # Location matching
        candidate_location = candidate.get("location", "")
        required_location = job_requirements.get("location", "")
        
        location_score = self.calculate_location_match(
            candidate_location, required_location, strict_location
        )
        match_details["location_score"] = location_score
        
        if location_score > 0.8:
            match_details["reasoning"].append(f"Location match: {candidate_location}")
        elif strict_location and location_score < 0.9:
            match_details["reasoning"].append(f"Location mismatch: {candidate_location} ≠ {required_location}")
            match_details["is_match"] = False
            return match_details
        
        # Experience validation - CRITICAL for filtering
        required_experience = job_requirements.get("experience")
        if required_experience:
            candidate_experience = self._extract_candidate_experience(candidate)
            
            if candidate_experience is None:
                # No experience data available - reduce score but don't eliminate
                match_details["reasoning"].append(f"Experience not specified (required: {required_experience}+ years)")
                # Apply penalty but don't eliminate completely
                experience_penalty = 0.2
            elif candidate_experience < required_experience:
                # Insufficient experience - eliminate candidate
                match_details["reasoning"].append(f"Insufficient experience: {candidate_experience} years < {required_experience} years required")
                match_details["is_match"] = False
                return match_details
            else:
                # Sufficient experience - bonus points
                match_details["reasoning"].append(f"Experience requirement met: {candidate_experience}+ years")
                experience_penalty = 0  # No penalty
        else:
            experience_penalty = 0  # No experience requirement
        
        # Calculate total score
        weights = {
            "role": 0.3,
            "skills": 0.5,
            "location": 0.2
        }
        
        total_score = (
            match_details["role_score"] * weights["role"] +
            match_details["skill_score"] * weights["skills"] +
            match_details["location_score"] * weights["location"]
        )
        
        # Apply experience penalty if applicable
        if 'experience_penalty' in locals():
            total_score = max(0, total_score - experience_penalty)
        
        match_details["total_score"] = total_score
        
        # Determine if it's a match - increased threshold for better quality
        threshold = 0.5  # Increased from 0.4 to filter out poor matches
        match_details["is_match"] = total_score >= threshold
        
        if not match_details["is_match"]:
            match_details["reasoning"].append(f"Score {total_score:.2f} below threshold {threshold}")
        
        return match_details
    
    def find_best_resume_match(
        self, 
        candidate_name: str, 
        resume_candidates: List[Dict]
    ) -> Optional[Dict]:
        """Find the best matching resume for a CSV candidate"""
        if not candidate_name or not resume_candidates:
            return None
        
        best_match = None
        best_score = 0.0
        
        for resume in resume_candidates:
            resume_name = resume.get("name", "")
            similarity = self.calculate_name_similarity(candidate_name, resume_name)
            
            if similarity > best_score and similarity > 0.6:  # Minimum threshold
                best_score = similarity
                best_match = resume
        
        return best_match
    
    def _extract_candidate_experience(self, candidate: Dict) -> Optional[int]:
        """
        Extract experience from candidate data
        
        Args:
            candidate: Candidate dictionary
            
        Returns:
            Years of experience or None if not found
        """
        # Check if experience is directly provided
        experience = candidate.get("experience")
        if experience:
            try:
                # Handle string like "5 years" or direct number
                if isinstance(experience, str):
                    match = re.search(r'(\d+)', experience)
                    if match:
                        return int(match.group(1))
                else:
                    return int(experience)
            except (ValueError, TypeError):
                pass
        
        # For resume candidates, we could parse the resume content here
        # But for now, we'll rely on the resume parser during the search process
        return None

# Global instance
candidate_matching_service = CandidateMatchingService()