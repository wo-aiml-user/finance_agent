from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

load_dotenv('.env')

logger = logging.getLogger(__name__)


class FinanceMemoryManager:
    """
    Manages the finance_memory collection in MongoDB for storing user financial profiles and insights.
    """
    
    def __init__(self, connection_string: Optional[str] = None, database_name: str = None):
        """
        Initialize MongoDB connection for finance memory storage.
        
        Args:
            connection_string: MongoDB connection string (defaults to env variable)
            database_name: Name of the database to use
        """
        self.connection_string = connection_string or os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
        self.database_name = database_name or os.getenv("DATABASE_NAME", "finance_agent")
        self.client = None
        self.db = None
        self.collection = None
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection and get collection reference."""
        try:
            logger.info(
                f"Connecting to MongoDB at '{self.connection_string}', database='{self.database_name}', collection='finance_memory'"
            )
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db["finance_memory"]
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB database='{self.database_name}' successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            try:
                import mongomock
                self.client = mongomock.MongoClient()
                self.db = self.client[self.database_name]
                self.collection = self.db["finance_memory"]
                logger.warning("Using mongomock for testing/development")
            except ImportError:
                raise Exception("MongoDB connection failed and mongomock not available")
    
    def store_finance_profile(self, user_id: str, profile_data: Dict[str, Any], 
                            additional_insights: Dict[str, Any] = None, 
                            profile_summary: str = None) -> str:
        """
        Store or update a user's financial profile in the finance_memory collection.
        
        Args:
            user_id: Unique identifier for the user
            profile_data: The FinanceProfile data as dict
            additional_insights: Extra insights not covered by schema
            profile_summary: Summary paragraph of financial situation
            
        Returns:
            Document ID of the stored/updated profile
        """
        document = {
            "user_id": user_id,
            "finance_profile": profile_data,
            "additional_insights": additional_insights or {},
            "profile_summary": profile_summary,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "version": 1
        }
        logger.info(f"Storing finance profile for user_id='{user_id}'")
        existing = self.collection.find_one({"user_id": user_id})
        if existing:
            logger.info(f"Existing finance profile found for user_id='{user_id}', updating document")
            document["version"] = existing.get("version", 0) + 1
            document["created_at"] = existing.get("created_at", datetime.utcnow())
            result = self.collection.replace_one(
                {"user_id": user_id}, 
                document
            )
            doc_id = str(existing["_id"])
            logger.info(f"Updated finance profile for user_id='{user_id}', doc_id='{doc_id}', version={document['version']}")
            return doc_id
        else:
            logger.info(f"No existing profile for user_id='{user_id}', inserting new document")
            result = self.collection.insert_one(document)
            doc_id = str(result.inserted_id)
            logger.info(f"Inserted finance profile for user_id='{user_id}', doc_id='{doc_id}'")
            return doc_id
    
    def get_finance_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user's financial profile from the finance_memory collection.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Complete financial profile document or None if not found
        """
        logger.info(f"Fetching finance profile for user_id='{user_id}'")
        return self.collection.find_one({"user_id": user_id})
    
    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """
        Retrieve all financial profiles from the finance_memory collection.
        
        Returns:
            List of all financial profile documents
        """
        logger.info("Fetching all finance profiles")
        return list(self.collection.find())
    
    def update_profile_insights(self, user_id: str, new_insights: Dict[str, Any]) -> bool:
        """
        Update additional insights for a user's profile.
        
        Args:
            user_id: Unique identifier for the user
            new_insights: New insights to merge with existing ones
            
        Returns:
            True if update successful, False otherwise
        """
        logger.info(f"Updating additional_insights for user_id='{user_id}'")
        result = self.collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "additional_insights": new_insights,
                    "updated_at": datetime.utcnow()
                },
                "$inc": {"version": 1}
            }
        )
        modified = result.modified_count > 0
        logger.info(
            f"Update additional_insights for user_id='{user_id}' status={'success' if modified else 'no-op'}"
        )
        return modified
    
    def delete_profile(self, user_id: str) -> bool:
        """
        Delete a user's financial profile.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            True if deletion successful, False otherwise
        """
        logger.info(f"Deleting finance profile for user_id='{user_id}'")
        result = self.collection.delete_one({"user_id": user_id})
        success = result.deleted_count > 0
        logger.info(
            f"Delete finance profile for user_id='{user_id}' status={'success' if success else 'not-found'}"
        )
        return success
    
    def get_profile_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get historical versions of a user's profile (if versioning is implemented).
        
        Args:
            user_id: Unique identifier for the user
            limit: Maximum number of versions to return
            
        Returns:
            List of profile versions ordered by creation date
        """
        logger.info(f"Fetching profile history for user_id='{user_id}'")
        # For now, just return the current profile
        # In future, implement proper versioning
        current = self.get_finance_profile(user_id)
        return [current] if current else []
    
    def close_connection(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# Global instance for easy access
finance_memory = FinanceMemoryManager()


def get_finance_memory_manager() -> FinanceMemoryManager:
    """
    Get the global finance memory manager instance.
    
    Returns:
        FinanceMemoryManager instance
    """
    return finance_memory