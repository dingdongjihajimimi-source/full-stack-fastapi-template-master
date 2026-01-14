"""
HTML Cleaner Utility for Data Preprocessing

Strips non-semantic HTML tags to reduce file size and prepare data for AI extraction.
Focuses on removing visual elements while preserving structural and data content.
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from typing import Dict


class HtmlCleaner:
    """Lightweight HTML preprocessing for data extraction."""
    
    # Tags that provide zero semantic value for data extraction
    JUNK_TAGS = ['style', 'script', 'svg', 'path', 'noscript', 'iframe', 'canvas']
    
    # Attributes that are purely visual/technical
    JUNK_ATTRS = ['class', 'id', 'style', 'onclick', 'onload', 'onerror']
    
    @staticmethod
    def strip_non_semantic_tags(html: str, focus_content: bool = False) -> str:
        """
        Remove tags and attributes that don't contribute to data extraction.
        
        Args:
            html: Raw HTML content
            focus_content: Deprecated flag, kept for compatibility.
            
        Returns:
            Cleaned HTML with only semantic content
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Remove entire junk tags
        for tag_name in HtmlCleaner.JUNK_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 2. Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # 3. Remove junk attributes from remaining tags
        for tag in list(soup.find_all(True)):
            if tag is None: continue
            for attr in HtmlCleaner.JUNK_ATTRS:
                if hasattr(tag, 'attrs') and attr in tag.attrs:
                    del tag.attrs[attr]
        
        
        # 5. Collapse excessive whitespace
        cleaned_html = str(soup)
        cleaned_html = re.sub(r'\n\s*\n', '\n', cleaned_html)  # Remove blank lines
        cleaned_html = re.sub(r'  +', ' ', cleaned_html)  # Collapse multiple spaces
        
        return cleaned_html
    
    @staticmethod
    def get_file_size_reduction(original_path: Path, cleaned_content: str) -> Dict[str, any]:
        """
        Calculate size reduction statistics.
        
        Args:
            original_path: Path to original HTML file
            cleaned_content: Cleaned HTML string
            
        Returns:
            Dict with original_size, cleaned_size, reduction_bytes, reduction_percent
        """
        original_size = original_path.stat().st_size
        cleaned_size = len(cleaned_content.encode('utf-8'))
        reduction_bytes = original_size - cleaned_size
        reduction_percent = (reduction_bytes / original_size * 100) if original_size > 0 else 0
        
        return {
            "original_size": original_size,
            "cleaned_size": cleaned_size,
            "reduction_bytes": reduction_bytes,
            "reduction_percent": round(reduction_percent, 2)
        }
    
    @staticmethod
    def clean_file(input_path: Path, output_path: Path) -> Dict[str, any]:
        """
        Clean an HTML file and save the result.
        
        Args:
            input_path: Source HTML file
            output_path: Destination for cleaned HTML
            
        Returns:
            Statistics dict
        """
        try:
            html_content = input_path.read_text(encoding='utf-8')
            cleaned_html = HtmlCleaner.strip_non_semantic_tags(html_content)
            
            output_path.write_text(cleaned_html, encoding='utf-8')
            
            stats = HtmlCleaner.get_file_size_reduction(input_path, cleaned_html)
            stats['output_path'] = str(output_path)
            
            return stats
        except Exception as e:
            import traceback
            print(f"CRITICAL CLEANING ERROR: {e}")
            traceback.print_exc()
            
            # Fallback: Just copy original file if cleaning fails
            output_path.write_text(html_content if 'html_content' in locals() else "", encoding='utf-8')
            return {
                "original_size": 0,
                "cleaned_size": 0,
                "reduction_bytes": 0,
                "reduction_percent": 0.0,
                "output_path": str(output_path),
                "error": str(e)
            }
