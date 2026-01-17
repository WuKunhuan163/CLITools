#!/usr/bin/env python3
"""
EXTRACT_IMG - Unified Image Analysis Tool
Intelligent image analysis tool that routes different image types to appropriate processors
with integrated caching system for both IMG2TEXT and UNIMERNET.
"""

import os
import sys
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import tempfile

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# Import PIL for image processing
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available, image padding will be disabled")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import centralized cache system
try:
    from EXTRACT_IMG_PROJ.cache_system import ImageCacheSystem
    CACHE_AVAILABLE = True
except ImportError:
    logger.warning("Cache system not available")
    CACHE_AVAILABLE = False
    ImageCacheSystem = None

class UnifiedImageProcessor:
    """Unified image processor that routes to IMG2TEXT or UNIMERNET based on content type"""
    
    def __init__(self):
        """Initialize the unified processor"""
        self.script_dir = Path(__file__).parent
        self.cache_system = None
        
        # Initialize cache system
        if CACHE_AVAILABLE:
            try:
                cache_dir = self.script_dir / "EXTRACT_IMG_DATA"
                self.cache_system = ImageCacheSystem(cache_dir)
                logger.info("Cache system initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize cache system: {e}")
                self.cache_system = None
        
        # Check tool availability
        self.img2text_tool = self.script_dir / "IMG2TEXT"
        self.unimernet_tool = self.script_dir / "UNIMERNET" 
        
        self.img2text_available = self.img2text_tool.exists()
        self.unimernet_available = self.unimernet_tool.exists()
        
        if not self.img2text_available:
            logger.warning("IMG2TEXT tool not available")
        if not self.unimernet_available:
            logger.warning("UNIMERNET tool not available")
    
    def detect_image_type(self, image_path: str, type_hint: str = "auto") -> str:
        """
        Detect image type based on filename patterns and hints.
        
        Args:
            image_path: Path to the image file
            type_hint: Type hint ("formula", "table", "image", "auto")
            
        Returns:
            Detected type ("formula", "table", "image")
        """
        if type_hint != "auto":
            return type_hint
        
        # Simple heuristics based on filename
        filename = Path(image_path).name.lower()
        
        # Formula indicators
        if any(word in filename for word in ['formula', 'equation', 'math', 'expr']):
            return "formula"
        
        # Table indicators  
        if any(word in filename for word in ['table', 'tab', 'grid']):
            return "table"
        
        # Default to general image
        return "image"
    
    def get_cache_key(self, image_path: str, content_type: str, mode: str = "academic") -> Optional[str]:
        """
        Generate cache key for image processing.
        
        Args:
            image_path: Path to the image file
            content_type: Type of content ("formula", "table", "image")
            mode: Processing mode (for IMG2TEXT)
            
        Returns:
            Cache key or None if cache not available
        """
        if not self.cache_system:
            return None
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Create composite key including processing parameters
            import hashlib
            param_hash = hashlib.md5(f"{content_type}:{mode}".encode()).hexdigest()[:8]
            
            # Use cache system's dual hash but append parameter hash
            sha256_hash = hashlib.sha256(image_data).hexdigest()
            md5_hash = hashlib.md5(image_data).hexdigest()
            composite_hash = sha256_hash[:32] + md5_hash[:16] + sha256_hash[32:48]
            
            return f"{composite_hash}_{param_hash}"
        except Exception as e:
            logger.warning(f"Failed to generate cache key: {e}")
            return None
    
    def get_cached_result(self, image_path: str, content_type: str, mode: str = "academic") -> Optional[Dict[str, Any]]:
        """
        Get cached result for image processing.
        
        Args:
            image_path: Path to the image file
            content_type: Type of content
            mode: Processing mode
            
        Returns:
            Cached result or None if not found
        """
        if not self.cache_system:
            return None
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Check if we have cached description
            cached_description = self.cache_system.get_cached_description(image_data)
            if cached_description:
                logger.info(f"📋 Found cached data for {Path(image_path).name}")
                # Try to parse as JSON (for structured results)
                try:
                    cached_result = json.loads(cached_description)
                    if isinstance(cached_result, dict):
                        # Check if content type matches or is compatible
                        cached_content_type = cached_result.get('content_type')
                        if cached_content_type == content_type or (
                            content_type in ['formula', 'table'] and cached_content_type in ['formula', 'table']
                        ):
                            cached_result['from_cache'] = True
                            cached_result['timestamp'] = datetime.now().isoformat()
                            logger.info(f"Using cached result for {Path(image_path).name}")
                            return cached_result
                        else:
                            logger.info(f"Warning:  Cached content type '{cached_content_type}' doesn't match requested '{content_type}'")
                except json.JSONDecodeError:
                    logger.info(f"📝 Found plain text cache for {Path(image_path).name}")
                    # Plain text result - wrap in standard format
                    return {
                        "success": True,
                        "result": cached_description,
                        "image_path": image_path,
                        "content_type": content_type,
                        "processor": "img2text" if content_type == "image" else "unimernet",
                        "timestamp": datetime.now().isoformat(),
                        "from_cache": True
                    }
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
        
        return None
    
    def store_result_in_cache(self, image_path: str, result: Dict[str, Any]) -> None:
        """
        Store processing result in cache.
        
        Args:
            image_path: Path to the image file
            result: Processing result to cache
        """
        if not self.cache_system or not result.get('success'):
            return
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Store result as JSON for structured data
            result_copy = result.copy()
            result_copy.pop('from_cache', None)  # Remove cache flag
            
            description = json.dumps(result_copy, ensure_ascii=False, indent=2)
            self.cache_system.store_image_and_description(image_data, description, image_path)
            logger.info(f"Stored result in cache for {Path(image_path).name}")
        except Exception as e:
            logger.warning(f"Failed to store result in cache: {e}")
    
    def process_with_img2text(self, image_path: str, mode: str = "academic", custom_prompt: str = None) -> Dict[str, Any]:
        """
        Process image using IMG2TEXT tool.
        
        Args:
            image_path: Path to the image file
            mode: Processing mode ("academic", "general", "code_snippet")
            custom_prompt: Custom prompt for image analysis
            
        Returns:
            Processing result dictionary
        """
        if not self.img2text_available:
            return {
                "success": False,
                "error": "IMG2TEXT tool not available"
            }
        
        try:
            # Direct IMG2TEXT call
            cmd = [str(self.img2text_tool), image_path, "--mode", mode]
            if custom_prompt:
                cmd.extend(["--prompt", custom_prompt])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "result": result.stdout.strip(),
                    "image_path": image_path,
                    "content_type": "image",
                    "processor": "img2text",
                    "mode": mode,
                    "timestamp": datetime.now().isoformat(),
                    "from_cache": False
                }
            else:
                return {
                    "success": False,
                    "error": f"IMG2TEXT execution failed: {result.stderr}"
                }
                    
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "IMG2TEXT processing timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"IMG2TEXT processing error: {e}"
            }
    
    def process_with_unimernet(self, image_path: str, content_type: str = "auto") -> Dict[str, Any]:
        """
        Process image using UNIMERNET tool.
        
        Args:
            image_path: Path to the image file
            content_type: Content type ("formula", "table", "auto")
            
        Returns:
            Processing result dictionary
        """
        if not self.unimernet_available:
            return {
                "success": False,
                "error": "UNIMERNET tool not available"
            }
        
        try:
            # Direct UNIMERNET call
            logger.info(f"🔄 Calling UNIMERNET directly for {Path(image_path).name}")
            direct_start = datetime.now()
            
            cmd = [str(self.unimernet_tool), image_path, "--json"]
            if content_type != "auto":
                cmd.extend(["--type", content_type])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            direct_elapsed = (datetime.now() - direct_start).total_seconds()
            logger.info(f"⏱️  Direct UNIMERNET call completed in {direct_elapsed:.2f}s")
            
            if result.returncode == 0:
                try:
                    # UNIMERNET output may contain debug info, find the JSON part
                    lines = result.stdout.strip().split('\n')
                    
                    # Find JSON start and end (may span multiple lines)
                    json_start = -1
                    json_end = -1
                    brace_count = 0
                    
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if line.startswith('{') and json_start == -1:
                            json_start = i
                            brace_count = 1
                        elif json_start != -1:
                            brace_count += line.count('{') - line.count('}')
                            if brace_count == 0:
                                json_end = i
                                break
                    
                    if json_start != -1 and json_end != -1:
                        json_lines = lines[json_start:json_end+1]
                        json_str = '\n'.join(json_lines)
                        try:
                            unimernet_result = json.loads(json_str)
                            if unimernet_result.get('success'):
                                # Update content_type if it was auto-detected
                                if unimernet_result.get('content_type') == 'auto' and content_type != 'auto':
                                    unimernet_result['content_type'] = content_type
                                logger.info(f"Direct UNIMERNET call successful")
                                return unimernet_result
                            else:
                                logger.warning(f"Warning:  UNIMERNET returned success=false")
                                return unimernet_result
                        except json.JSONDecodeError as e:
                            logger.error(f"Error: JSON decode error: {e}")
                            logger.error(f"   JSON string: {json_str[:200]}...")
                    
                    logger.error(f"Error: No valid JSON found in output")
                    return {
                        "success": False,
                        "error": f"No valid JSON found in UNIMERNET output: {result.stdout[:200]}..."
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse UNIMERNET output: {e}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"UNIMERNET execution failed: {result.stderr}"
                }
                    
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "UNIMERNET processing timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"UNIMERNET processing error: {e}"
            }
    
    def process_image(self, image_path: str, content_type: str = "auto", mode: str = "academic", 
                     use_cache: bool = True, force: bool = False, custom_prompt: str = None, no_padding: bool = False) -> Dict[str, Any]:
        """
        Process image with appropriate tool based on content type.
        
        Args:
            image_path: Path to the image file
            content_type: Content type hint ("formula", "table", "image", "auto")
            mode: Processing mode for IMG2TEXT
            use_cache: Whether to use cache
            force: Force reprocessing even if cached
            custom_prompt: Custom prompt for image analysis (only for image type)
            
        Returns:
            Processing result dictionary
        """
        if not Path(image_path).exists():
            return {
                "success": False,
                "error": f"Image file not found: {image_path}"
            }
        
        # Detect actual content type
        start_time = datetime.now()
        logger.info(f"🚀 Starting processing: {Path(image_path).name}")
        
        detected_type = self.detect_image_type(image_path, content_type)
        logger.info(f"🔍 Detected type: {detected_type}")
        
        # Check cache first (unless forced)
        if use_cache and not force:
            cache_start = datetime.now()
            cached_result = self.get_cached_result(image_path, detected_type, mode)
            cache_elapsed = (datetime.now() - cache_start).total_seconds()
            logger.info(f"⏱️  Cache check completed in {cache_elapsed:.3f}s")
            
            if cached_result:
                total_elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"Found cached result for {Path(image_path).name} (total: {total_elapsed:.3f}s)")
                return cached_result
        
        # Process based on detected type
        process_start = datetime.now()
        temp_image_path = None
        
        if detected_type in ["formula", "table"]:
            logger.info(f"🔄 Processing {detected_type} with UNIMERNET: {Path(image_path).name}")
            
            # Add padding for better UNIMERNET recognition (unless disabled)
            if no_padding:
                logger.info(f"Warning:  Skipping padding due to --no-padding flag")
                processing_image_path = image_path
            else:
                padded_image_path = self.add_image_padding(image_path)
                if padded_image_path != image_path:
                    temp_image_path = padded_image_path
                    # Copy padded image to EXTRACT_IMG_DATA for inspection
                    try:
                        extract_img_data_dir = self.script_dir / "EXTRACT_IMG_DATA" / "padded_images"
                        extract_img_data_dir.mkdir(parents=True, exist_ok=True)
                        padded_copy = extract_img_data_dir / Path(padded_image_path).name
                        import shutil
                        shutil.copy2(padded_image_path, padded_copy)
                        logger.info(f"📁 Saved padded image to: {padded_copy}")
                    except Exception as e:
                        logger.warning(f"Warning:  Could not save padded image: {e}")
                processing_image_path = padded_image_path
            
            result = self.process_with_unimernet(processing_image_path, detected_type)
        else:  # detected_type == "image"
            logger.info(f"🔄 Processing image with IMG2TEXT: {Path(image_path).name}")
            result = self.process_with_img2text(image_path, mode, custom_prompt)
        
        process_elapsed = (datetime.now() - process_start).total_seconds()
        total_elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️  Processing completed in {process_elapsed:.2f}s (total: {total_elapsed:.2f}s)")
        
        # Add processing time to result
        if result.get('success'):
            result['processing_time'] = total_elapsed
        
        # Clean up temporary padded image if created
        if temp_image_path and temp_image_path != image_path:
            self.cleanup_temp_image(temp_image_path)
        
        # Store result in cache if successful
        if result.get('success') and use_cache:
            logger.info(f"Storing result in cache for {Path(image_path).name}")
            result['content_type'] = detected_type
            self.store_result_in_cache(image_path, result)
        
        return result
    
    def add_image_padding(self, image_path: str, padding_percent: float = 0.2) -> str:
        """
        Add white padding around image for better UNIMERNET recognition.
        
        Args:
            image_path: Path to the original image
            padding_percent: Padding as percentage of image size (default: 20%)
            
        Returns:
            Path to the padded image (temporary file)
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, skipping image padding")
            return image_path
        
        try:
            # Open the image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate padding
                width, height = img.size
                pad_width = int(width * padding_percent)
                pad_height = int(height * padding_percent)
                
                # Add padding (white background)
                padded_img = ImageOps.expand(img, border=(pad_width, pad_height), fill='white')
                
                # Create temporary file
                temp_dir = tempfile.gettempdir()
                temp_filename = f"padded_{Path(image_path).stem}_{hash(image_path) % 10000}.jpg"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                # Save padded image
                padded_img.save(temp_path, 'JPEG', quality=95)
                
                logger.info(f"🖼️  Added padding to image: {Path(image_path).name} -> {temp_filename}")
                return temp_path
                
        except Exception as e:
            logger.warning(f"Failed to add padding to image: {e}")
            return image_path
    
    def cleanup_temp_image(self, temp_path: str) -> None:
        """Clean up temporary padded image file"""
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary image: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache system statistics"""
        if not self.cache_system:
            return {
                "cache_available": False,
                "message": "Cache system not available"
            }
        
        return self.cache_system.get_cache_stats()


def main():
    """Main entry point for EXTRACT_IMG"""
    parser = argparse.ArgumentParser(description="Unified Image Analysis Tool")
    parser.add_argument("image_path", nargs="?", help="Path to the image file")
    parser.add_argument("--type", choices=["formula", "table", "image", "auto"], 
                       default="auto", help="Image content type hint")
    parser.add_argument("--mode", choices=["academic", "general", "code_snippet"], 
                       default="academic", help="Processing mode for general images")
    parser.add_argument("--prompt", help="Custom prompt for image analysis (only for image type)")
    parser.add_argument("--force", action="store_true", help="Force reprocessing (ignore cache)")
    parser.add_argument("--no-padding", action="store_true", help="Skip image padding for formula/table processing")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--clear-cache", action="store_true", help="Clear all cached data")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = UnifiedImageProcessor()
    
    # Show cache statistics
    if args.stats:
        stats = processor.get_cache_stats()
        print(json.dumps(stats, indent=2))
        return
    
    # Clear cache if requested
    if args.clear_cache:
        if processor.cache_system:
            try:
                # Clear cache files
                cache_system = processor.cache_system
                if cache_system.images_dir.exists():
                    import shutil
                    shutil.rmtree(cache_system.images_dir)
                    cache_system.images_dir.mkdir()
                if cache_system.cache_file.exists():
                    with open(cache_system.cache_file, 'w') as f:
                        json.dump({}, f)
                cache_system.cache = {}
                print(f"Cache cleared successfully")
            except Exception as e:
                print(f"Error: Failed to clear cache: {e}")
        else:
            print(f"Error: Cache system not available")
        return
    
    # Check for image path
    if not args.image_path:
        parser.error("Image path is required unless using --stats")
    
    # Process image
    result = processor.process_image(
        args.image_path,
        content_type=args.type,
        mode=args.mode,
        use_cache=True,
        force=args.force,
        custom_prompt=args.prompt,
        no_padding=args.no_padding
    )
    
    # Output result
    if args.json:
        output = json.dumps(result, indent=2, ensure_ascii=False)
        print(output)
    else:
        if result.get('success'):
            cache_info = " (from cache)" if result.get('from_cache') else ""
            processor_info = result.get('processor', 'unknown').upper()
            print(f"{processor_info} processing successful{cache_info}")
            print(f"Result:\n{result.get('result', 'No result')}")
        else:
            print(f"Error: Processing failed: {result.get('error', 'Unknown error')}")
            output = json.dumps(result, indent=2, ensure_ascii=False)
            print(output)
    
    # Save to file if requested
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                if args.json:
                    f.write(output)
                else:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Result saved to: {args.output}")
        except Exception as e:
            print(f"Error: Failed to save file: {e}")


if __name__ == "__main__":
    main()
