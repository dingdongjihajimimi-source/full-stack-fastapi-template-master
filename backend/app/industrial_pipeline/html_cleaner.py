"""
用于数据预处理的 HTML 清理工具

去除非语义 HTML 标签以减小文件大小并为 AI 提取准备数据。
专注于移除视觉元素，同时保留结构和数据内容。
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from typing import Dict


class HtmlCleaner:
    """用于数据提取的轻量级 HTML 预处理。"""
    
    # 对数据提取没有语义价值的标签
    JUNK_TAGS = ['style', 'script', 'svg', 'path', 'noscript', 'iframe', 'canvas']
    
    # 纯视觉/技术属性
    JUNK_ATTRS = ['class', 'id', 'style', 'onclick', 'onload', 'onerror']
    
    @staticmethod
    def strip_non_semantic_tags(html: str, focus_content: bool = False) -> str:
        """
        移除对数据提取没有贡献的标签和属性。
        
        参数:
            html: 原始 HTML 内容
            focus_content: 已弃用的标志，为兼容性保留。
            
        返回:
            仅包含语义内容的清理后 HTML
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 移除整个垃圾标签
        for tag_name in HtmlCleaner.JUNK_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 2. 移除 HTML 注释
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # 3. 从剩余标签中移除垃圾属性
        for tag in list(soup.find_all(True)):
            if tag is None: continue
            for attr in HtmlCleaner.JUNK_ATTRS:
                if hasattr(tag, 'attrs') and attr in tag.attrs:
                    del tag.attrs[attr]
        
        
        # 5. 合并多余的空格
        cleaned_html = str(soup)
        cleaned_html = re.sub(r'\n\s*\n', '\n', cleaned_html)  # Remove blank lines
        cleaned_html = re.sub(r'  +', ' ', cleaned_html)  # Collapse multiple spaces
        
        return cleaned_html
    
    @staticmethod
    def get_file_size_reduction(original_path: Path, cleaned_content: str) -> Dict[str, any]:
        """
        计算大小缩减统计信息。
        
        参数:
            original_path: 原始 HTML 文件路径
            cleaned_content: 清理后的 HTML 字符串
            
        返回:
            包含 original_size, cleaned_size, reduction_bytes, reduction_percent 的字典
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
        清理 HTML 文件并保存结果。
        
        参数:
            input_path: 源 HTML 文件
            output_path: 清理后 HTML 的目标路径
            
        返回:
            统计信息字典
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
            
            # 回退：如果清理失败，仅复制原始文件
            output_path.write_text(html_content if 'html_content' in locals() else "", encoding='utf-8')
            return {
                "original_size": 0,
                "cleaned_size": 0,
                "reduction_bytes": 0,
                "reduction_percent": 0.0,
                "output_path": str(output_path),
                "error": str(e)
            }
