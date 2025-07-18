"""
Backup Manager for BlendPro: AI Co-Pilot
Automatic scene backup and restore functionality
"""

import os
import time
import glob
import shutil
from typing import List, Optional, Dict, Any
from datetime import datetime
import bpy

from ..config.settings import get_settings

class BackupError(Exception):
    """Custom exception for backup-related errors"""

    def __init__(self, message: str, backup_path: Optional[str] = None, operation: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.backup_path = backup_path
        self.operation = operation

    def __str__(self) -> str:
        if self.operation and self.backup_path:
            return f"Backup Error during {self.operation} at {self.backup_path}: {self.message}"
        elif self.operation:
            return f"Backup Error during {self.operation}: {self.message}"
        return f"Backup Error: {self.message}"

class BackupManager:
    """Manages automatic scene backups and restore functionality"""
    
    def __init__(self):
        self.settings = get_settings()
        self.backup_dir = self._get_backup_directory()
        self._ensure_backup_directory()
        self._last_backup_time = 0
    
    def _get_backup_directory(self) -> str:
        """Get the backup directory path"""
        user_data_dir = bpy.utils.user_resource('DATAFILES')
        backup_dir = os.path.join(user_data_dir, "blendpro_backups")
        return backup_dir
    
    def _ensure_backup_directory(self) -> None:
        """Ensure backup directory exists"""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
        except Exception as e:
            raise BackupError(f"Failed to create backup directory: {e}")
    
    def _generate_backup_filename(self) -> str:
        """Generate a unique backup filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scene_name = bpy.path.basename(bpy.data.filepath) or "untitled"
        scene_name = os.path.splitext(scene_name)[0]  # Remove extension
        return f"blendpro_backup_{scene_name}_{timestamp}.blend"
    
    def should_create_backup(self) -> bool:
        """Check if a backup should be created based on settings and timing"""
        if not self.settings.enable_auto_backup:
            return False
        
        current_time = time.time()
        time_since_last = current_time - self._last_backup_time
        
        return time_since_last >= self.settings.backup_interval
    
    def create_backup(self, force: bool = False) -> Optional[str]:
        """Create a backup of the current scene"""
        try:
            if not force and not self.should_create_backup():
                return None
            
            backup_filename = self._generate_backup_filename()
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Save current scene to backup location
            bpy.ops.wm.save_as_mainfile(filepath=backup_path, copy=True)
            
            self._last_backup_time = time.time()
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            print(f"BlendPro: Backup created at {backup_path}")
            return backup_path
            
        except Exception as e:
            raise BackupError(f"Failed to create backup: {e}")
    
    def get_recent_backups(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get list of recent backups with metadata"""
        try:
            if limit is None:
                limit = self.settings.max_backups
            
            backup_pattern = os.path.join(self.backup_dir, "blendpro_backup_*.blend")
            backup_files = glob.glob(backup_pattern)
            
            # Sort by modification time (newest first)
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            backups = []
            for backup_file in backup_files[:limit]:
                stat = os.stat(backup_file)
                backups.append({
                    "path": backup_file,
                    "filename": os.path.basename(backup_file),
                    "created": datetime.fromtimestamp(stat.st_mtime),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2)
                })
            
            return backups
            
        except Exception as e:
            raise BackupError(f"Failed to get backup list: {e}")
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore a backup file"""
        try:
            if not os.path.exists(backup_path):
                raise BackupError(f"Backup file not found: {backup_path}")
            
            # Open the backup file
            bpy.ops.wm.open_mainfile(filepath=backup_path)
            
            print(f"BlendPro: Restored backup from {backup_path}")
            return True
            
        except Exception as e:
            raise BackupError(f"Failed to restore backup: {e}")
    
    def delete_backup(self, backup_path: str) -> bool:
        """Delete a specific backup file"""
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                print(f"BlendPro: Deleted backup {backup_path}")
                return True
            return False
            
        except Exception as e:
            raise BackupError(f"Failed to delete backup: {e}")
    
    def _cleanup_old_backups(self) -> None:
        """Clean up old backups based on settings"""
        try:
            backups = self.get_recent_backups()
            
            if len(backups) > self.settings.max_backups:
                # Delete oldest backups
                backups_to_delete = backups[self.settings.max_backups:]
                
                for backup in backups_to_delete:
                    self.delete_backup(backup["path"])
                
                print(f"BlendPro: Cleaned up {len(backups_to_delete)} old backups")
                
        except Exception as e:
            print(f"BlendPro: Warning - Failed to cleanup old backups: {e}")
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup system statistics"""
        try:
            backups = self.get_recent_backups()
            total_size = sum(backup["size"] for backup in backups)
            
            return {
                "total_backups": len(backups),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "backup_directory": self.backup_dir,
                "auto_backup_enabled": self.settings.enable_auto_backup,
                "backup_interval": self.settings.backup_interval,
                "max_backups": self.settings.max_backups,
                "oldest_backup": backups[-1]["created"] if backups else None,
                "newest_backup": backups[0]["created"] if backups else None
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup_all_backups(self) -> int:
        """Delete all backups (use with caution)"""
        try:
            backups = self.get_recent_backups()
            deleted_count = 0
            
            for backup in backups:
                if self.delete_backup(backup["path"]):
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            raise BackupError(f"Failed to cleanup all backups: {e}")

# Global backup manager instance
_backup_manager: Optional[BackupManager] = None

def get_backup_manager() -> BackupManager:
    """Get global backup manager instance"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager

def create_backup(force: bool = False) -> Optional[str]:
    """Convenience function to create a backup"""
    return get_backup_manager().create_backup(force=force)

def get_recent_backups(limit: int = None) -> List[Dict[str, Any]]:
    """Convenience function to get recent backups"""
    return get_backup_manager().get_recent_backups(limit=limit)

def restore_backup(backup_path: str) -> bool:
    """Convenience function to restore a backup"""
    return get_backup_manager().restore_backup(backup_path)
