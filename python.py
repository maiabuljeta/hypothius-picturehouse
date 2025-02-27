import os
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
from urllib.parse import urljoin

app = Flask(__name__)

# Configuration
GITHUB_USERNAME = "maiabuljeta"  # Replace with your actual GitHub username
REPOSITORY_NAME = "hypothius-picturehouse"  # Replace with your GitHub Pages repository name
BASE_URL = f"http://maiabuljeta.github.io/hypothius-picturehouse/"  # Base URL of your GitHub Pages site
PAGES_TO_CRAWL = []  # This will be populated by the crawler

def crawl_site():
    """Crawl the GitHub Pages website to discover all HTML pages"""
    pages_to_visit = [BASE_URL]
    visited_pages = set()
    discovered_pages = []

    while pages_to_visit:
        current_url = pages_to_visit.pop(0)
        if current_url in visited_pages:
            continue

        try:
            response = requests.get(current_url)
            visited_pages.add(current_url)
            
            if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                soup = BeautifulSoup(response.text, 'html.parser')
                discovered_pages.append({
                    'url': current_url,
                    'content': response.text,
                    'title': soup.title.string if soup.title else current_url
                })
                
                # Find all links on the page
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # Skip external links, anchors, javascript, etc.
                    if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                        continue
                    
                    # Convert relative URLs to absolute
                    full_url = urljoin(current_url, href)
                    
                    # Only include URLs from the same domain
                    if full_url.startswith(BASE_URL) and full_url not in visited_pages:
                        pages_to_visit.append(full_url)
        
        except Exception as e:
            print(f"Error crawling {current_url}: {e}")
    
    return discovered_pages

@app.route('/crawl', methods=['GET'])
def update_page_index():
    """Endpoint to manually trigger crawling of the site"""
    global PAGES_TO_CRAWL
    PAGES_TO_CRAWL = crawl_site()
    return jsonify({
        'status': 'success',
        'message': f'Successfully crawled {len(PAGES_TO_CRAWL)} pages'
    })

@app.route('/search', methods=['GET'])
def search():
    """Search through all crawled pages for a query"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'results': [], 'count': 0})
    
    results = []
    for page in PAGES_TO_CRAWL:
        soup = BeautifulSoup(page['content'], 'html.parser')
        
        # Strip all HTML tags to get plain text
        text_content = soup.get_text()
        
        # Check if query exists in content (case-insensitive)
        if re.search(query, text_content, re.IGNORECASE):
            # Find context for the result preview
            match = re.search(f'.{{0,100}}{re.escape(query)}.{{0,100}}', text_content, re.IGNORECASE)
            preview = '...' + match.group(0) + '...' if match else ''
            
            # Determine the type of page based on the URL structure
            page_type = "Page"
            if "film" in page['url'].lower() or any(film in page['url'].lower() for film in 
                   ["his", "paradise-cost", "womanhood", "plague", "d.a.n.g"]):
                page_type = "Film"
            elif "behind-the-scenes" in page['url'].lower():
                page_type = "Behind the Scenes"
            
            results.append({
                'url': page['url'],
                'title': page['title'],
                'preview': preview,
                'type': page_type
            })
    
    return jsonify({
        'results': results,
        'count': len(results),
        'query': query
    })

@app.route('/')
def search_page():
    """Renders the search form page"""
    return render_template('search.html')

if __name__ == '__main__':
    # Initial crawl when the server starts
    PAGES_TO_CRAWL = crawl_site()
    app.run(debug=True)
