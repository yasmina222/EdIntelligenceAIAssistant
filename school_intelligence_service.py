"""
School Research Assistant - Intelligence Service
=================================================
Replaces: processor_premium.py

WHAT THIS FILE DOES:
- Orchestrates the entire flow: load data → generate insights → cache
- This is the "brain" that coordinates everything
- Calls the LangChain conversation chain
- Handles caching to avoid redundant LLM calls

HOW TO USE:
    service = SchoolIntelligenceService()
    
    # Get a school with conversation starters
    school = service.get_school_intelligence("Thomas Coram Centre")
    
    # Access the starters
    for starter in school.conversation_starters:
        print(starter.detail)
"""

import logging
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from models_v2 import School, ConversationStarter, ConversationStarterResponse
from data_loader import DataLoader, get_data_loader
from chains.conversation_chain import ConversationChain
from config_v2 import ENABLE_CACHE, CACHE_TTL_HOURS, CACHE_DIR, FEATURES

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple file-based cache for conversation starters.
    
    WHY WE CACHE:
    - LLM calls cost money (and take time)
    - If we already generated starters for a school, reuse them
    - Cache expires after CACHE_TTL_HOURS (default 24)
    
    FUTURE: Replace with LangChain's built-in caching for production
    """
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.enabled = ENABLE_CACHE
        
    def _get_cache_key(self, school_urn: str) -> str:
        """Generate cache key from school URN"""
        return hashlib.md5(f"starters_{school_urn}".encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"
    
    def get(self, school_urn: str) -> Optional[List[dict]]:
        """Get cached conversation starters if valid"""
        if not self.enabled:
            return None
            
        key = self._get_cache_key(school_urn)
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check if expired
            cached_at = datetime.fromisoformat(data['cached_at'])
            if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
                logger.info(f"🕐 Cache expired for {school_urn}")
                return None
            
            logger.info(f"📦 Cache HIT for {school_urn}")
            return data['starters']
            
        except Exception as e:
            logger.warning(f"⚠️ Cache read error: {e}")
            return None
    
    def set(self, school_urn: str, starters: List[ConversationStarter]) -> bool:
        """Save conversation starters to cache"""
        if not self.enabled:
            return False
            
        key = self._get_cache_key(school_urn)
        cache_path = self._get_cache_path(key)
        
        try:
            data = {
                'school_urn': school_urn,
                'cached_at': datetime.now().isoformat(),
                'starters': [s.model_dump() for s in starters]
            }
            
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"💾 Cached {len(starters)} starters for {school_urn}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Cache write error: {e}")
            return False
    
    def clear(self, school_urn: str = None) -> int:
        """Clear cache for one school or all schools"""
        count = 0
        
        if school_urn:
            key = self._get_cache_key(school_urn)
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
                count = 1
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        
        logger.info(f"🧹 Cleared {count} cache entries")
        return count


class SchoolIntelligenceService:
    """
    Main service that orchestrates everything.
    
    This is what the Streamlit app talks to.
    """
    
    def __init__(self):
        """Initialize all components"""
        self.data_loader = get_data_loader()
        self.conversation_chain = None  # Lazy load to avoid API calls at startup
        self.cache = SimpleCache()
        
        logger.info("✅ SchoolIntelligenceService initialized")
    
    def _get_chain(self) -> ConversationChain:
        """Lazy-load the conversation chain (avoids API calls at startup)"""
        if self.conversation_chain is None:
            self.conversation_chain = ConversationChain()
        return self.conversation_chain
    
    # =========================================================================
    # DATA ACCESS METHODS
    # =========================================================================
    
    def get_all_schools(self) -> List[School]:
        """Get all schools from the data source"""
        return self.data_loader.get_all_schools()
    
    def get_school_names(self) -> List[str]:
        """Get school names for dropdown"""
        return self.data_loader.get_school_names()
    
    def get_school_by_name(self, name: str) -> Optional[School]:
        """Get a school by name (without generating starters)"""
        return self.data_loader.get_school_by_name(name)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data statistics"""
        return self.data_loader.get_statistics()
    
    # =========================================================================
    # INTELLIGENCE METHODS (with LLM calls)
    # =========================================================================
    
    def get_school_intelligence(
        self, 
        school_name: str, 
        force_refresh: bool = False,
        num_starters: int = 5
    ) -> Optional[School]:
        """
        Get a school WITH conversation starters generated.
        
        This is the main method for the UI:
        1. Gets school data from cache/CSV
        2. Generates conversation starters using LLM
        3. Caches the results
        
        Args:
            school_name: Name of the school
            force_refresh: If True, regenerate starters even if cached
            num_starters: How many starters to generate
            
        Returns:
            School object with conversation_starters populated
        """
        # Get the school
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            logger.warning(f"⚠️ School not found: {school_name}")
            return None
        
        # Check if conversation starters are enabled
        if not FEATURES.get("conversation_starters", True):
            logger.info("ℹ️ Conversation starters disabled in config")
            return school
        
        # Check cache first
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                return school
        
        # Generate new starters using LLM
        try:
            chain = self._get_chain()
            response = chain.generate(school, num_starters)
            
            # Add starters to school
            school.conversation_starters = response.conversation_starters
            
            # Cache the results
            self.cache.set(school.urn, response.conversation_starters)
            
            return school
            
        except Exception as e:
            logger.error(f"❌ Error generating intelligence: {e}")
            # Return school without starters on error
            return school
    
    async def get_school_intelligence_async(
        self, 
        school_name: str, 
        force_refresh: bool = False,
        num_starters: int = 5
    ) -> Optional[School]:
        """
        Async version of get_school_intelligence.
        
        Use this when processing multiple schools in parallel.
        """
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            return None
        
        if not FEATURES.get("conversation_starters", True):
            return school
        
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                return school
        
        try:
            chain = self._get_chain()
            response = await chain.agenerate(school, num_starters)
            
            school.conversation_starters = response.conversation_starters
            self.cache.set(school.urn, response.conversation_starters)
            
            return school
            
        except Exception as e:
            logger.error(f"❌ Async error: {e}")
            return school
    
    def get_high_priority_schools(self, limit: int = 10) -> List[School]:
        """
        Get top priority schools for calling.
        
        Returns schools sorted by sales priority.
        """
        schools = self.data_loader.get_all_schools()
        
        # Sort by priority (HIGH first)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
        sorted_schools = sorted(
            schools, 
            key=lambda s: priority_order.get(s.get_sales_priority(), 3)
        )
        
        return sorted_schools[:limit]
    
    def get_schools_with_agency_spend(self) -> List[School]:
        """Get schools that spend on agency staff"""
        return self.data_loader.get_schools_with_agency_spend()
    
    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================
    
    def clear_cache(self, school_name: str = None) -> int:
        """Clear cache for one school or all schools"""
        if school_name:
            school = self.data_loader.get_school_by_name(school_name)
            if school:
                return self.cache.clear(school.urn)
            return 0
        return self.cache.clear()
    
    def refresh_data(self) -> List[School]:
        """Force reload data from source"""
        return self.data_loader.refresh()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_service_instance: Optional[SchoolIntelligenceService] = None

def get_intelligence_service() -> SchoolIntelligenceService:
    """
    Get the global service instance.
    
    Usage:
        from school_intelligence_service import get_intelligence_service
        service = get_intelligence_service()
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SchoolIntelligenceService()
    return _service_instance


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the service
    service = SchoolIntelligenceService()
    
    # Get all school names
    names = service.get_school_names()
    print(f"\n📚 Available schools ({len(names)}):")
    for name in names[:5]:
        print(f"   • {name}")
    
    # Get statistics
    stats = service.get_statistics()
    print(f"\n📊 Statistics:")
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    # Get high priority schools
    high_priority = service.get_high_priority_schools(limit=3)
    print(f"\n🎯 High priority schools:")
    for school in high_priority:
        print(f"   • {school.school_name} ({school.get_sales_priority()})")
    
    # Test intelligence generation (this makes an LLM call!)
    print("\n🤖 Testing conversation starter generation...")
    print("   (This will make an API call to Claude/GPT)")
    
    # Uncomment to test:
    # school = service.get_school_intelligence("Thomas Coram Centre")
    # if school:
    #     print(f"\n💬 Starters for {school.school_name}:")
    #     for s in school.conversation_starters:
    #         print(f"\n   Topic: {s.topic}")
    #         print(f"   {s.detail}")
