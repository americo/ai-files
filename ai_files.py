#!/usr/bin/env python3
"""
AI Smart File Organizer with Background Monitoring

This script uses local LLM models via Ollama to:
1. Intelligently categorize files based on content
2. Rename files with descriptive, standardized names
3. Organize everything into an "AI Library" structure  
4. Monitor Downloads folder for new files in background
5. Run efficiently with minimal resource usage
"""

import os
import json
import shutil
import pathlib
import subprocess
import time
import threading
import signal
import sys
from collections import defaultdict
import mimetypes
from typing import Dict, List, Optional, Any
import re
from datetime import datetime
import platform
# Native file monitoring without external dependencies


class AISmartOrganizer:
    def __init__(self, downloads_path: str = None, model: str = "gemma3:4b", library_name: str = "AI Library"):
        """Initialize the AI smart organizer with enhanced features."""
        if downloads_path is None:
            self.downloads_path = os.path.expanduser("~/Downloads")
        else:
            self.downloads_path = downloads_path
        
        self.model = model
        self.library_name = library_name
        self.library_path = os.path.join(self.downloads_path, library_name)
        self.manual_library_path = None  # Will be set in _ensure_library_exists
        
        # State tracking
        self.processed_files = []
        self.created_categories = set()
        self.errors = []
        self.ai_cache = {}
        self.rename_cache = {}
        self.running = False
        
        # Performance settings
        self.max_content_chars = 1500
        self.ai_timeout = 25
        self.cache_max_size = 500
        
        # Notification settings
        self.notifications_enabled = platform.system() == "Darwin"  # macOS only
        
        # Initialize
        mimetypes.init()
        self._verify_ollama()
        self._ensure_library_exists()

    def send_macos_notification(self, title: str, message: str, subtitle: str = ""):
        """Send native macOS notification using osascript."""
        if not self.notifications_enabled:
            print(f"[INFO] Notifications disabled (notifications_enabled: {self.notifications_enabled})")
            return
        
        print(f"[INFO] Sending notification...")
        
        try:
            # Escape quotes in the text
            title = title.replace('"', '\\"')
            message = message.replace('"', '\\"')
            subtitle = subtitle.replace('"', '\\"')
            
            # Create the AppleScript command
            script = f'''
            display notification "{message}" with title "{title}" subtitle "{subtitle}"
            '''
            
            print(f"[DEBUG] Executing AppleScript: {script}")
            
            # Execute the AppleScript
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            print(f"[DEBUG] AppleScript result - Return code: {result.returncode}")
            print(f"[DEBUG] AppleScript result - Stdout: {result.stdout}")
            print(f"[DEBUG] AppleScript result - Stderr: {result.stderr}")
            
            if result.returncode != 0:
                print(f"[ERROR] Notification failed: {result.stderr}")
            else:
                print(f"[SUCCESS] Notification sent successfully")
                
        except Exception as e:
            print(f"[ERROR] Error sending notification: {e}")

    def _verify_ollama(self):
        """Verify Ollama and model availability."""
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception("Ollama is not running or installed")
            
            if self.model not in result.stdout:
                print(f"[WARNING] Model '{self.model}' not found. Pulling it...")
                pull_result = subprocess.run(["ollama", "pull", self.model], capture_output=True, text=True)
                if pull_result.returncode != 0:
                    raise Exception(f"Failed to pull model '{self.model}': {pull_result.stderr}")
                print(f"[SUCCESS] Model '{self.model}' ready!")
            
        except subprocess.TimeoutExpired:
            raise Exception("Ollama appears to be unresponsive")
        except FileNotFoundError:
            raise Exception("Ollama not installed. Install from https://ollama.ai")

    def _ensure_library_exists(self):
        """Create the AI Library root folder."""
        if not os.path.exists(self.library_path):
            os.makedirs(self.library_path)
            print(f"[INFO] Created {self.library_name} at: {self.library_path}")
        
        # Create Manual Library folder
        self.manual_library_path = os.path.join(self.downloads_path, "Manual Library")
        if not os.path.exists(self.manual_library_path):
            os.makedirs(self.manual_library_path)
            print(f"[INFO] Created Manual Library at: {self.manual_library_path}")

    def _manage_cache_size(self):
        """Keep cache sizes manageable."""
        if len(self.ai_cache) > self.cache_max_size:
            # Remove oldest entries (simple FIFO)
            items_to_remove = len(self.ai_cache) - self.cache_max_size + 100
            keys_to_remove = list(self.ai_cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self.ai_cache[key]
        
        if len(self.rename_cache) > self.cache_max_size:
            items_to_remove = len(self.rename_cache) - self.cache_max_size + 100
            keys_to_remove = list(self.rename_cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self.rename_cache[key]

    def _query_ai(self, prompt: str, max_tokens: int = 100) -> str:
        """Query AI with caching and timeout management."""
        cache_key = hash(prompt + self.model)
        if cache_key in self.ai_cache:
            return self.ai_cache[cache_key]
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.1
                }
            }
            
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate",
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps(payload)],
                capture_output=True,
                text=True,
                timeout=self.ai_timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Ollama API error: {result.stderr}")
            
            response = json.loads(result.stdout)
            ai_response = response.get("response", "").strip()
            
            # Cache and manage size
            self.ai_cache[cache_key] = ai_response
            self._manage_cache_size()
            
            return ai_response
            
        except Exception as e:
            raise Exception(f"AI query failed: {str(e)}")

    def _read_file_content(self, file_path: str) -> str:
        """Efficiently read file content for AI analysis."""
        try:
            file_size = os.path.getsize(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Skip very large files for performance
            if file_size > 5 * 1024 * 1024:  # 5MB limit
                return f"[Large file - {mime_type or 'unknown'}, {file_size} bytes]"
            
            # Read text-based files
            if mime_type and mime_type.startswith('text/'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(self.max_content_chars)
                    if len(content) == self.max_content_chars:
                        content += "... [truncated]"
                    return content
            elif file_path.lower().endswith(('.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv')):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(self.max_content_chars)
                    if len(content) == self.max_content_chars:
                        content += "... [truncated]"
                    return content
            else:
                return f"[Binary file - {mime_type or 'unknown'}, {file_size} bytes]"
                
        except Exception:
            return "[Could not read file]"

    def analyze_file_category(self, file_path: str) -> str:
        """AI analysis for file category."""
        filename = os.path.basename(file_path)
        file_ext = pathlib.Path(file_path).suffix.lower()
        mime_type, _ = mimetypes.guess_type(file_path)
        content_preview = self._read_file_content(file_path)
        
        prompt = f"""Analyze this file and choose the BEST category:

File: {filename}
Extension: {file_ext}
MIME: {mime_type or 'unknown'}
Content: {content_preview[:800]}

Categories:
- Work Documents
- Personal Documents  
- Images
- Screenshots
- Videos
- Audio/Music
- Code/Development
- Archives/Downloads
- Financial Documents
- Educational Materials
- Creative Projects
- System Files
- Entertainment
- Health/Medical
- Travel
- Recipes/Food
- Shopping/Receipts
- Legal Documents
- Reference Materials
- Other

Respond with ONLY the category name."""

        try:
            response = self._query_ai(prompt, max_tokens=30)
            category = response.strip().split('\n')[0]
            category = re.sub(r'^(Category:\s*|Answer:\s*)', '', category, flags=re.IGNORECASE)
            
            valid_categories = {
                "Work Documents", "Personal Documents", "Images", "Screenshots", 
                "Videos", "Audio/Music", "Code/Development", "Archives/Downloads",
                "Financial Documents", "Educational Materials", "Creative Projects",
                "System Files", "Entertainment", "Health/Medical", "Travel", 
                "Recipes/Food", "Shopping/Receipts", "Legal Documents",
                "Reference Materials", "Other"
            }
            
            if category in valid_categories:
                return category
            
            # Try fuzzy matching
            category_lower = category.lower()
            for valid_cat in valid_categories:
                if valid_cat.lower() in category_lower or category_lower in valid_cat.lower():
                    return valid_cat
            
            return "Other"
            
        except Exception as e:
            self.errors.append(f"Category analysis failed for {filename}: {str(e)}")
            return "Other"

    def generate_smart_filename(self, file_path: str, category: str) -> str:
        """AI-powered intelligent file renaming."""
        original_filename = os.path.basename(file_path)
        file_ext = pathlib.Path(file_path).suffix.lower()
        
        # Check rename cache
        cache_key = hash(original_filename + category + file_ext)
        if cache_key in self.rename_cache:
            return self.rename_cache[cache_key]
        
        # Skip renaming for already well-named files
        if self._is_well_named(original_filename):
            return original_filename
        
        content_preview = self._read_file_content(file_path)
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""Generate a clear, descriptive filename for this file. 

Original: {original_filename}
Category: {category}
Extension: {file_ext}
Content: {content_preview[:600]}

Rules:
1. Use descriptive, professional names
2. Include relevant dates if applicable (format: YYYY-MM-DD)
3. Use underscores instead of spaces
4. Keep under 100 characters
5. Be specific about content/purpose
6. Don't include the file extension

Examples:
- "IMG_1234.jpg" → "Screenshot_Login_Page_2024-01-15"
- "document.pdf" → "Contract_Employment_Agreement_2024"
- "untitled.py" → "Data_Processing_Script"

Generate filename (without extension):"""

        try:
            response = self._query_ai(prompt, max_tokens=50)
            new_name = response.strip().split('\n')[0]
            
            # Clean up the response
            new_name = re.sub(r'^(Filename:\s*|Name:\s*)', '', new_name, flags=re.IGNORECASE)
            new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)  # Remove invalid chars
            new_name = re.sub(r'[^\w\-_.]', '_', new_name)  # Keep only safe chars
            new_name = re.sub(r'_+', '_', new_name)  # Remove multiple underscores
            new_name = new_name.strip('_')  # Remove leading/trailing underscores
            
            # Ensure reasonable length
            if len(new_name) > 80:
                new_name = new_name[:80]
            
            # Fallback to original if AI generated something weird
            if len(new_name) < 3 or not new_name:
                new_name = pathlib.Path(original_filename).stem
            
            final_filename = new_name + file_ext
            
            # Cache the result
            self.rename_cache[cache_key] = final_filename
            
            return final_filename
            
        except Exception as e:
            self.errors.append(f"Rename failed for {original_filename}: {str(e)}")
            return original_filename

    def _is_well_named(self, filename: str) -> bool:
        """Check if filename is already well-structured."""
        name_without_ext = pathlib.Path(filename).stem.lower()
        
        # Already has date
        if re.search(r'\d{4}-\d{2}-\d{2}', name_without_ext):
            return True
        
        # Descriptive names (not generic)
        generic_patterns = [
            r'^(img|image)_?\d+$',
            r'^screenshot_?\d*$',
            r'^document_?\d*$',
            r'^file_?\d*$',
            r'^untitled',
            r'^new_?',
            r'^temp',
        ]
        
        for pattern in generic_patterns:
            if re.match(pattern, name_without_ext):
                return False
        
        # Has descriptive words (3+ chars, multiple words)
        words = re.split(r'[_\-\s]+', name_without_ext)
        meaningful_words = [w for w in words if len(w) >= 3]
        
        return len(meaningful_words) >= 2

    def create_category_folder(self, category: str) -> str:
        """Create category folder inside AI Library."""
        category_path = os.path.join(self.library_path, category)
        if not os.path.exists(category_path):
            os.makedirs(category_path)
            self.created_categories.add(category)
            print(f"[INFO] Created category folder: {self.library_name}/{category}")
        return category_path

    def organize_folders(self, dry_run: bool = False) -> List[str]:
        """Move any folders (except AI Library and Manual Library) to Manual Library."""
        if not os.path.exists(self.downloads_path):
            return []
        
        moved_folders = []
        protected_folders = {self.library_name, "Manual Library"}
        
        try:
            for item in os.listdir(self.downloads_path):
                item_path = os.path.join(self.downloads_path, item)
                
                # Skip if not a directory
                if not os.path.isdir(item_path):
                    continue
                
                # Skip hidden folders and protected folders
                if item.startswith('.') or item in protected_folders:
                    continue
                
                # Move folder to Manual Library
                destination_path = os.path.join(self.manual_library_path, item)
                
                if dry_run:
                    print(f"[DRY_RUN] Would move folder: {item} → Manual Library/{item}")
                    moved_folders.append(item)
                else:
                    try:
                        # Handle naming conflicts
                        counter = 1
                        final_destination = destination_path
                        while os.path.exists(final_destination):
                            final_destination = f"{destination_path}_{counter}"
                            counter += 1
                        
                        shutil.move(item_path, final_destination)
                        moved_folders.append(item)
                        print(f"[SUCCESS] Moved folder: {item} → Manual Library/{os.path.basename(final_destination)}")
                        
                        # Send notification for folder organization
                        if self.notifications_enabled:
                            notification_title = "AI Files"
                            notification_message = f"Movida para: Manual Library/{os.path.basename(final_destination)}"
                            notification_subtitle = f"Pasta: {item}"
                            self.send_macos_notification(notification_title, notification_message, notification_subtitle)
                        
                    except Exception as e:
                        error_msg = f"Failed to move folder {item}: {str(e)}"
                        self.errors.append(error_msg)
                        print(f"[ERROR] Error moving folder {item}: {str(e)}")
        
        except Exception as e:
            self.errors.append(f"Error organizing folders: {str(e)}")
        
        return moved_folders

    def process_single_file(self, file_path: str, show_progress: bool = True) -> bool:
        """Process a single file: categorize, rename, and move."""
        if not os.path.isfile(file_path) or os.path.basename(file_path).startswith('.'):
            return False
        
        # Skip files already in AI Library or Manual Library
        if self.library_path in file_path or self.manual_library_path in file_path:
            return False
        
        filename = os.path.basename(file_path)
        if show_progress:
            print(f"[PROCESSING] {filename[:50]}{'...' if len(filename) > 50 else ''}")
        
        try:
            # Step 1: Categorize
            category = self.analyze_file_category(file_path)
            
            # Step 2: Generate smart filename
            new_filename = self.generate_smart_filename(file_path, category)
            
            # Step 3: Create category folder
            category_folder = self.create_category_folder(category)
            
            # Step 4: Move with new name
            destination_path = os.path.join(category_folder, new_filename)
            
            # Handle naming conflicts
            counter = 1
            while os.path.exists(destination_path):
                name, ext = os.path.splitext(new_filename)
                conflict_filename = f"{name}_{counter}{ext}"
                destination_path = os.path.join(category_folder, conflict_filename)
                counter += 1
            
            # Move the file
            shutil.move(file_path, destination_path)
            
            if show_progress:
                if new_filename != filename:
                    print(f"   [RENAME] {filename} → {new_filename}")
                print(f"   [MOVE] {self.library_name}/{category}")
            
            # Send notification for successful processing
            if self.notifications_enabled:
                notification_title = "AI Files - Arquivo Processado"
                notification_message = f"Movido para: {self.library_name}/{category}"
                
                if new_filename != filename:
                    notification_subtitle = f"Renomeado: {new_filename}"
                else:
                    notification_subtitle = f"Nome mantido: {filename}"
                
                print(f"[NOTIFICATION] Sending: {notification_title} - {notification_message} - {notification_subtitle}")
                self.send_macos_notification(notification_title, notification_message, notification_subtitle)
            else:
                print(f"[INFO] Notifications disabled (not macOS)")
            
            self.processed_files.append(destination_path)
            return True
            
        except Exception as e:
            error_msg = f"Failed to process {filename}: {str(e)}"
            self.errors.append(error_msg)
            if show_progress:
                print(f"   [ERROR] {str(e)}")
            return False

    def organize_downloads(self, dry_run: bool = False, max_files: int = None) -> Dict[str, List[str]]:
        """Organize existing files in Downloads."""
        print(f"[INFO] AI Smart Organizer (Model: {self.model})")
        print("=" * 70)
        print(f"[INFO] Downloads: {self.downloads_path}")
        print(f"[INFO] Library: {self.library_path}")
        print(f"[MODE] {'DRY RUN MODE' if dry_run else 'ORGANIZING FILES'}")
        print("-" * 70)
        
        if not os.path.exists(self.downloads_path):
            raise FileNotFoundError(f"Downloads folder not found: {self.downloads_path}")
        
        # Get files to process
        files = []
        for item in os.listdir(self.downloads_path):
            item_path = os.path.join(self.downloads_path, item)
            if (os.path.isfile(item_path) and not item.startswith('.') and 
                self.library_name not in item and "Manual Library" not in item):
                files.append(item_path)
        
        if max_files:
            files = files[:max_files]
        
        if not files:
            print("[INFO] No files to organize!")
            return {}
        
        print(f"[INFO] Found {len(files)} files to process...")
        
        # First, organize any loose folders
        moved_folders = self.organize_folders(dry_run)
        if moved_folders:
            if dry_run:
                print(f"[DRY_RUN] Would move {len(moved_folders)} folders to Manual Library")
            else:
                print(f"[SUCCESS] Moved {len(moved_folders)} folders to Manual Library")
        
        print("-" * 70)
        
        # Process files
        processed_count = 0
        categorized_files = defaultdict(list)
        
        for i, file_path in enumerate(files, 1):
            filename = os.path.basename(file_path)
            print(f"[{i}/{len(files)}] {filename[:50]}{'...' if len(filename) > 50 else ''}")
            
            if not dry_run:
                if self.process_single_file(file_path, show_progress=False):
                    processed_count += 1
            else:
                # For dry run, just categorize
                try:
                    category = self.analyze_file_category(file_path)
                    new_name = self.generate_smart_filename(file_path, category)
                    categorized_files[category].append((file_path, new_name))
                    print(f"   [CATEGORY] {category}")
                    if new_name != filename:
                        print(f"   [RENAME] Would rename to: {new_name}")
                except Exception as e:
                    categorized_files["Other"].append((file_path, filename))
                    print(f"   [ERROR] Other (error: {str(e)})")
        
        # Summary
        print("-" * 70)
        if dry_run:
            print(f"[SUMMARY] Preview Complete! {len(files)} files analyzed")
            for category, file_list in categorized_files.items():
                print(f"   [CATEGORY] {category}: {len(file_list)} files")
        else:
            print(f"[SUCCESS] Processed {processed_count}/{len(files)} files successfully!")
            if self.errors:
                print(f"[ERROR] {len(self.errors)} errors occurred")
        
        return dict(categorized_files)


class DownloadsMonitor:
    """Native file system monitor for Downloads folder."""
    
    def __init__(self, organizer: AISmartOrganizer):
        self.organizer = organizer
        self.processing_lock = threading.Lock()
        self.known_files = set()
        self.last_scan = time.time()
        
        # Initialize with existing files
        self._scan_existing_files()
        
    def _scan_existing_files(self):
        """Scan and record existing files."""
        try:
            for item in os.listdir(self.organizer.downloads_path):
                item_path = os.path.join(self.organizer.downloads_path, item)
                if (os.path.isfile(item_path) and not item.startswith('.') and
                    self.organizer.library_path not in item_path and
                    self.organizer.manual_library_path not in item_path):
                    self.known_files.add(item_path)
        except Exception:
            pass
    
    def check_for_new_files(self):
        """Check for new files and process them."""
        try:
            current_files = set()
            for item in os.listdir(self.organizer.downloads_path):
                item_path = os.path.join(self.organizer.downloads_path, item)
                if os.path.isfile(item_path) and not item.startswith('.'):
                    # Skip files already in AI Library or Manual Library
                    if (self.organizer.library_path in item_path or 
                        self.organizer.manual_library_path in item_path):
                        continue
                    current_files.add(item_path)
            
            # Find new files
            new_files = current_files - self.known_files
            
            for new_file in new_files:
                # Wait a bit for file to be fully written
                try:
                    # Check if file is still being written (size changes)
                    initial_size = os.path.getsize(new_file)
                    time.sleep(1)
                    if os.path.getsize(new_file) == initial_size:
                        with self.processing_lock:
                            print(f"\n[NEW_FILE] Detected: {os.path.basename(new_file)}")
                            success = self.organizer.process_single_file(new_file)
                            if success:
                                print("[SUCCESS] File processed successfully!")
                            else:
                                print("[WARNING] File processing failed or skipped")
                except Exception as e:
                    print(f"[ERROR] Error processing new file {os.path.basename(new_file)}: {e}")
            
            # Update known files
            self.known_files = current_files
            
        except Exception as e:
            print(f"[ERROR] Error scanning directory: {e}")


def run_background_monitor(organizer: AISmartOrganizer):
    """Run the background file monitor using native polling."""
    print(f"[INFO] Starting background monitor...")
    print(f"[INFO] Watching: {organizer.downloads_path}")
    print(f"[INFO] AI Library: {organizer.library_path}")
    print(f"[INFO] Manual Library: {organizer.manual_library_path}")
    print("[INFO] Press Ctrl+C to stop")
    print("-" * 50)
    
    monitor = DownloadsMonitor(organizer)
    organizer.running = True
    
    # Initial folder organization
    moved_folders = organizer.organize_folders(dry_run=False)
    if moved_folders:
        print(f"[SUCCESS] Organized {len(moved_folders)} existing folders")
    
    try:
        folder_check_counter = 0
        while organizer.running:
            monitor.check_for_new_files()
            
            # Check for new folders every 10 iterations (20 seconds)
            folder_check_counter += 1
            if folder_check_counter >= 10:
                moved_folders = organizer.organize_folders(dry_run=False)
                if moved_folders:
                    print(f"\n[SUCCESS] Organized {len(moved_folders)} new folders")
                folder_check_counter = 0
            
            time.sleep(2)  # Check every 2 seconds
    except KeyboardInterrupt:
        print("\n[INFO] Stopping background monitor...")
    finally:
        organizer.running = False


def signal_handler(signum, frame, organizer):
    """Handle shutdown signals gracefully."""
    print(f"\n[INFO] Received signal {signum}, shutting down gracefully...")
    organizer.running = False
    sys.exit(0)


def main():
    """Main function with enhanced command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Smart File Organizer with Background Monitoring")
    parser.add_argument("--path", "-p", help="Downloads folder path (default: ~/Downloads)")
    parser.add_argument("--model", "-m", default="gemma3:4b", help="Ollama model (default: gemma3:4b)")
    parser.add_argument("--library", "-l", default="AI Library", help="Library folder name (default: 'AI Library')")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview without moving files")
    parser.add_argument("--monitor", action="store_true", help="Run in background monitoring mode")
    parser.add_argument("--max-files", type=int, help="Limit files to process (testing)")
    parser.add_argument("--report", "-r", action="store_true", help="Show detailed report")
    
    args = parser.parse_args()
    
    try:
        print(f"[INFO] Initializing AI Smart Organizer...")
        organizer = AISmartOrganizer(args.path, args.model, args.library)
        
        # Set up signal handling for graceful shutdown
        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, organizer))
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, organizer))
        
        if args.monitor:
            # Background monitoring mode
            run_background_monitor(organizer)
        else:
            # One-time organization
            categorized = organizer.organize_downloads(args.dry_run, args.max_files)
            
            if args.report:
                print(f"\n[REPORT] DETAILED SUMMARY")
                print("=" * 30)
                print(f"[INFO] Model: {organizer.model}")
                print(f"[INFO] Library: {organizer.library_path}")
                print(f"[INFO] Processed: {len(organizer.processed_files)}")
                print(f"[INFO] Categories: {len(organizer.created_categories)}")
                print(f"[INFO] Errors: {len(organizer.errors)}")
                print(f"[INFO] Cache size: {len(organizer.ai_cache)}")
            
            if args.dry_run:
                print(f"\n[INFO] Run without --dry-run to actually organize files")
                print(f"[INFO] Use --monitor to run in background mode")
            else:
                print(f"\n[SUCCESS] Organization complete!")
                print(f"[INFO] Use --monitor to keep watching for new files")
    
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\n[TROUBLESHOOTING]")
        print("[INFO] 1. Ensure Ollama is running: ollama serve")
        print("[INFO] 2. Check model availability: ollama list")
        print("[INFO] 3. Test Ollama: ollama run llama3.2")
        sys.exit(1)


if __name__ == "__main__":
    main()
