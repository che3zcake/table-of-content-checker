import re
import requests
import fitz  # PyMuPDF
import argparse  # Add this import


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
            "Capítulo"
        ]

    def add_keywords(self, new_keywords):
        """Add additional keywords to check for TOC

        Args:
            new_keywords (list): List of new keywords to add
        """
        self.keywords.extend(new_keywords)

    def is_toc_present(self, pdf_content):
        """Check if TOC is present in the PDF content

        Args:
            pdf_content (bytes): PDF content as bytes

        Returns:
            bool: True if TOC is present, False otherwise
        """
        try:
            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                # toc = doc.get_toc()
                # if toc:
                #     return True

                for page_num in range(min(5, len(doc))):
                    page = doc.load_page(page_num)
                    text = page.get_text("text")
                    if any(keyword in text for keyword in self.keywords):
                        if detect_toc_pattern(text):
                            return True
        except fitz.FileDataError:
            print(" ")
        return False


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
            raise ValueError(f" ")
    except requests.exceptions.RequestException as e:
        print(f" ")
        return None


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
            if pdf_content and toc_checker.is_toc_present(pdf_content):
                print(f"Yes")
            else:
                print(f"No")
        except ValueError as e:
            print(e)