import re
import requests
import fitz  # PyMuPDF
import argparse


def detect_toc_pattern(text):
    """Detect TOC-like patterns in the text

    Args:
        text (str): Text extracted from the PDF page

    Returns:
        bool: True if a TOC-like pattern is found, False otherwise
    """
    pattern = r'''
        ^\d+\s+[\w\sÀ-ÿ]+$|           # Numbered lists (1  Introduction)
        \b\d+\.\s+\w+|                # Numbered lists (1. Introduction)
        \b[A-Z]\.\s+\w+|              # Uppercase lettered lists (A. Background)
        \b[a-z]\.\s+\w+|              # Lowercase lettered lists (a. Introduction)
        \(\d+\)\s+\w+|                # Parenthesized numbers ((1) Introduction)
        \([A-Za-z]\)\s+\w+|           # Parenthesized letters ((A) Background)
        [•\-]\s+\w+|                  # Bullet points (• Introduction, - Methodology)
        \b[IVXLCDM]+\.\s+\w+|         # Roman numerals (I. Introduction, II. Methodology)
        \b\d+:\s+\w+|                 # Numbered lists with colons (1: Introduction)
        \b[A-Za-z]:\s+\w+             # Lettered lists with colons (A: Background)
        ^[\w\sÀ-ÿ]+(?:\.{2,}|\s{2,})\d+$|  # Text followed by dots or spaces, ending with a number     
    '''
    return bool(re.search(pattern, text, re.VERBOSE))


class TOCChecker:
    def __init__(self):
        """Initialize with default keywords for TOC detection"""
        self.keywords = [
            "Agenda",
            "Tabla de contenido",
            "Tabla de Contenidos",
            "Contenido",
            "CONTENIDO",
            "En esta noticia",
            "INDICE",
            "Indice",
            "ÍNDICE",
            "Índice",
            "PUNTOS CLAVE",
            # "Capítulo",
            "índice",
            "SUMARIO"
        ]

    def add_keywords(self, new_keywords):
        """Add additional keywords to check for TOC

        Args:
            new_keywords (list): List of new keywords to add
        """
        self.keywords.extend(new_keywords)

    def extract_headings(self, page, keywords):
        """Check if the keywords have different formatting compared to other text on the page

        Args:
            page (fitz.Page): A PDF page object from PyMuPDF
            keywords (list): List of keywords to check for unique formatting

        Returns:
            bool: True if keywords have different formatting, False otherwise
        """
        blocks = page.get_text("dict")["blocks"]
        keyword_formatting = []
        other_formatting = []

        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    if "spans" in line:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            size = span["size"]
                            font = span["font"]
                            is_bold = "bold" in font.lower()

                            if any(keyword.lower() in text.lower() for keyword in keywords):
                                keyword_formatting.append({
                                    "size": size,
                                    "font": font,
                                    "bold": is_bold
                                })
                            else:
                                other_formatting.append({
                                    "size": size,
                                    "font": font,
                                    "bold": is_bold
                                })

        avg_keyword_size = sum(f["size"] for f in keyword_formatting) / len(keyword_formatting)
        avg_other_size = sum(f["size"] for f in other_formatting) / len(other_formatting) if other_formatting else 0

        keyword_fonts = set(f["font"] for f in keyword_formatting)
        other_fonts = set(f["font"] for f in other_formatting) if other_formatting else set()

        keyword_bold = any(f["bold"] for f in keyword_formatting)
        other_bold = any(f["bold"] for f in other_formatting) if other_formatting else False

        if (avg_keyword_size > avg_other_size or
                keyword_fonts - other_fonts or
                keyword_bold and not other_bold):
            return True

        return False

    def is_toc_present(self, pdf_content):
        """Check if TOC is present in the PDF content and match headings with keywords

        Args:
            pdf_content (bytes): PDF content as bytes

        Returns:
            bool: True if TOC is present and headings match keywords, False otherwise
            None: If the PDF is corrupted or cannot be opened
        """
        try:
            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                if len(doc) > 10:
                    for page_num in range(min(7, len(doc))):
                        page = doc.load_page(page_num)
                        text = page.get_text("text")
                        if any(keyword in text for keyword in self.keywords):
                            if self.extract_headings(page, self.keywords):
                                return True
            return False
        except fitz.FileDataError:
            return None


def fetch_pdf(url):
    """Fetch PDF content from a URL

    Args:
        url (str): URL of the PDF file

    Returns:
        bytes: PDF content as bytes, or None if the request fails
    """
    try:
        response = requests.get(url, stream=True, timeout=15)
        if response.status_code == 200:
            return response.content
        else:
            return False
    except requests.exceptions.RequestException as e:
        return False


def read_urls_from_file(file_path):
    """Read URLs from a text file

    Args:
        file_path (str): Path to the text file containing URLs

    Returns:
        list: List of URLs
    """
    try:
        with open(file_path, "r") as file:
            urls = [line.strip() for line in file if line.strip()]
        return urls
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for TOC in PDFs from a list of URLs.")
    parser.add_argument(
        "url_file",
        help="Path to the text file containing URLs (one URL per line)"
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        help="Additional keywords to check for TOC"
    )
    args = parser.parse_args()

    urls = read_urls_from_file(args.url_file)

    if not urls:
        print("No URLs found in the file. Exiting.")
        exit()

    toc_checker = TOCChecker()

    if args.keywords:
        toc_checker.add_keywords(args.keywords)

    for url in urls:
        try:
            pdf_content = fetch_pdf(url)
            if pdf_content:
                toc_result = toc_checker.is_toc_present(pdf_content)
                if toc_result is None:
                    print(" ")
                elif toc_result:
                    print("Yes")
                else:
                    print("No")
            else:
                print(" ")
        except ValueError as e:
            print(e)
