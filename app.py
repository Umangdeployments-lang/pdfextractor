from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

def crawl_for_pdfs(start_url, max_pages=15):
    """Crawls a website starting at start_url to find PDFs."""
    visited = set()
    to_visit = [start_url]
    pdfs = []
    domain = urlparse(start_url).netloc

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)
        # Remove anchor tags to avoid visiting the same page twice
        current_url = current_url.split('#')[0] 
        
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            # Set a timeout so we don't hang forever
            response = requests.get(current_url, timeout=5)
            
            # Only parse HTML pages
            if 'text/html' not in response.headers.get('Content-Type', ''):
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a'):
                href = link.get('href')
                if not href:
                    continue

                full_url = urljoin(current_url, href)
                parsed_url = urlparse(full_url)

                # If it's a PDF, extract it
                if full_url.lower().endswith('.pdf'):
                    # Get the text of the link for the name, fallback to the filename
                    name = link.text.strip()
                    if not name:
                        name = full_url.split('/')[-1]
                    
                    pdfs.append({
                        "name": name, 
                        "url": full_url, 
                        "found_on": current_url
                    })
                
                # If it's an internal link, add to queue to crawl later
                elif parsed_url.netloc == domain and full_url not in visited:
                    to_visit.append(full_url)

        except Exception as e:
            print(f"Skipping {current_url} due to error: {e}")
            continue

    # Deduplicate PDFs based on their URL
    unique_pdfs = list({v['url']: v for v in pdfs}.values())
    return unique_pdfs

@app.route('/')
def home():
    # Serves the frontend HTML
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "Please provide a valid URL"}), 400

    print(f"Starting extraction for: {url}")
    # Note: max_pages is set to 15 to prevent the server from crashing or taking 10 minutes.
    pdfs = crawl_for_pdfs(url, max_pages=15)
    
    return jsonify({"pdfs": pdfs})

if __name__ == '__main__':
    app.run(debug=True)