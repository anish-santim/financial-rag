import requests, csv
from bs4 import BeautifulSoup
import datetime
import re
import os
from collections import defaultdict

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
BASE = "https://www.rbi.org.in"

def parse_date_string(date_str):
    """Parse date string to datetime object"""
    if not date_str or date_str == 'No Date':
        return None
    
    # Common date formats from RBI website
    date_formats = [
        '%b %d, %Y',      # Aug 05, 2025
        '%B %d, %Y',      # August 05, 2025
        '%d %b %Y',       # 05 Aug 2025
        '%d %B %Y',       # 05 August 2025
    ]
    
    for fmt in date_formats:
        try:
            return datetime.datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None

def filter_last_7_days_data(data):
    """Filter data to show only last 7 days where data is available"""
    # Group data by date and parse dates
    date_groups = defaultdict(list)
    valid_dates = []
    
    for item in data:
        date_str = item['date']
        parsed_date = parse_date_string(date_str)
        
        if parsed_date:
            date_groups[parsed_date].extend([item])
            if parsed_date not in valid_dates:
                valid_dates.append(parsed_date)
    
    # Sort dates in descending order (newest first)
    valid_dates.sort(reverse=True)
    
    # Take only the last 7 dates where data is available
    last_7_dates = valid_dates[:7]
    
    # Collect data for these dates
    filtered_data = []
    for date in last_7_dates:
        filtered_data.extend(date_groups[date])
    
    print(f"Filtered to last 7 available dates: {[date.strftime('%b %d, %Y') for date in last_7_dates]}")
    return filtered_data

def create_rbi_directory():
    """Create RBI directory in scraped_data folder"""
    rbi_dir = os.path.join("scraped_data", "RBI")
    os.makedirs(rbi_dir, exist_ok=True)
    return rbi_dir

def extract_rbi_data():
    """Extract RBI press releases organized by date with titles and links"""
    print("Fetching RBI press releases...")
    
    # Get the main press releases page
    url = BASE + "/Scripts/BS_PressReleaseDisplay.aspx"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        print(f"Successfully fetched main page")
        
        # Find all content - we'll parse it to organize by date
        page_text = soup.get_text()
        
        # Extract date-wise organized data
        results = []
        current_date = None
        
        # Get the page content as text and split by lines
        page_content = soup.get_text('\n')
        lines = page_content.split('\n')
        
        # Also get all links for URL mapping
        all_links = soup.find_all('a', href=True)
        link_map = {}  # title -> url mapping
        
        for link in all_links:
            href = link.get('href', '')
            if 'BS_PressReleaseDisplay.aspx?prid=' in href:
                title = link.get_text(strip=True)
                if title and len(title) > 10:
                    # Ensure consistent URL construction
                    if href.startswith('/Scripts/'):
                        full_url = BASE + href
                    elif href.startswith('/'):
                        full_url = BASE + href
                    elif href.startswith('http'):
                        full_url = href
                    elif href.startswith('Scripts/'):
                        full_url = BASE + "/" + href
                    else:
                        # Default case - assume it needs Scripts/ prefix
                        full_url = BASE + "/Scripts/" + href
                    
                    link_map[title] = full_url
        
        # Process lines to find dates and titles
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a date (like "Aug 05, 2025")
            date_patterns = [
                r'^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$',  # Aug 05, 2025
                r'^(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})$',   # 05 Aug 2025
                r'^([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})$'  # Aug 05, 2025 with spaces
            ]
            
            date_found = False
            for pattern in date_patterns:
                if re.match(pattern, line):
                    current_date = line
                    print(f"Found date: {current_date}")
                    date_found = True
                    break
            
            if date_found:
                continue
            
            # Check if this line is a title that has a corresponding link
            if line in link_map:
                results.append({
                    'date': current_date if current_date else 'No Date',
                    'title': line,
                    'url': link_map[line]
                })
        
        print(f"Found {len(results)} press releases")
        return results
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def save_to_html_file(data):
    """Save data to HTML file with clickable links in the scraped_data/RBI folder"""
    # Create RBI directory
    rbi_dir = create_rbi_directory()
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"rbi_news_{timestamp}.html"
    filepath = os.path.join(rbi_dir, filename)
    
    # Group data by date and sort by date (newest first)
    date_groups = defaultdict(list)
    for item in data:
        date = item['date']
        date_groups[date].append(item)
    
    # Sort dates - try to parse them for proper sorting
    sorted_dates = []
    for date_str in date_groups.keys():
        parsed_date = parse_date_string(date_str)
        if parsed_date:
            sorted_dates.append((parsed_date, date_str))
        else:
            sorted_dates.append((datetime.datetime.min, date_str))
    
    sorted_dates.sort(reverse=True, key=lambda x: x[0])
    
    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RBI Press Releases - Last 7 Days</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1e3a8a;
            text-align: center;
            border-bottom: 3px solid #1e3a8a;
            padding-bottom: 10px;
        }}
        .header-info {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-style: italic;
        }}
        .date-section {{
            margin-bottom: 30px;
            border-left: 4px solid #1e3a8a;
            padding-left: 20px;
        }}
        .date-header {{
            color: #1e3a8a;
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 15px;
            background-color: #f0f4ff;
            padding: 10px;
            border-radius: 5px;
        }}
        .news-item {{
            margin-bottom: 15px;
            padding: 15px;
            background-color: #fafafa;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }}
        .news-title {{
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }}
        .news-link {{
            color: #1e3a8a;
            text-decoration: none;
            font-weight: 500;
        }}
        .news-link:hover {{
            text-decoration: underline;
            color: #2563eb;
        }}
        .stats {{
            background-color: #f0f4ff;
            padding: 15px;
            border-radius: 5px;
            margin-top: 30px;
            text-align: center;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏦 RBI Press Releases - Last 7 Days</h1>
        <div class="header-info">
            Generated on: {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
            Total items: {len(data)}
        </div>
"""
    
    # Add each date section
    for _, date_str in sorted_dates:
        items = date_groups[date_str]
        html_content += f"""
        <div class="date-section">
            <div class="date-header">📅 {date_str} ({len(items)} items)</div>
"""
        
        for i, item in enumerate(items, 1):
            html_content += f"""
            <div class="news-item">
                <div class="news-title">{i}. {item['title']}</div>
                <a href="{item['url']}" target="_blank" class="news-link">🔗 View Full Article</a>
            </div>
"""
        
        html_content += "        </div>\n"
    
    # Add footer
    html_content += f"""
        <div class="stats">
            <strong>📊 Summary:</strong> {len(data)} press releases from {len(sorted_dates)} dates
        </div>
        <div class="footer">
            Data sourced from <a href="https://www.rbi.org.in" target="_blank">Reserve Bank of India</a><br>
            Last updated: {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </div>
    </div>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Saved {len(data)} items to {filepath}")
    return filepath

def save_to_markdown_file(data):
    """Save data to Markdown file with clickable links in the scraped_data/RBI folder"""
    # Create RBI directory
    rbi_dir = create_rbi_directory()
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"rbi_news_{timestamp}.md"
    filepath = os.path.join(rbi_dir, filename)
    
    # Group data by date and sort by date (newest first)
    date_groups = defaultdict(list)
    for item in data:
        date = item['date']
        date_groups[date].append(item)
    
    # Sort dates - try to parse them for proper sorting
    sorted_dates = []
    for date_str in date_groups.keys():
        parsed_date = parse_date_string(date_str)
        if parsed_date:
            sorted_dates.append((parsed_date, date_str))
        else:
            sorted_dates.append((datetime.datetime.min, date_str))
    
    sorted_dates.sort(reverse=True, key=lambda x: x[0])
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# 🏦 RBI Press Releases - Last 7 Days\n\n")
        f.write(f"**Generated on:** {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}  \n")
        f.write(f"**Total items:** {len(data)}  \n")
        f.write(f"**Data source:** [Reserve Bank of India](https://www.rbi.org.in)\n\n")
        f.write("---\n\n")
        
        # Write each date group in sorted order
        for _, date_str in sorted_dates:
            items = date_groups[date_str]
            f.write(f"## 📅 {date_str} ({len(items)} items)\n\n")
            
            for i, item in enumerate(items, 1):
                # Create clickable link in markdown format
                f.write(f"{i}. **[{item['title']}]({item['url']})**\n\n")
            
            f.write("---\n\n")
    
    print(f"Saved {len(data)} items to {filepath}")
    return filepath

def save_to_text_file(data):
    """Save data to text file in the scraped_data/RBI folder (backup format)"""
    # Create RBI directory
    rbi_dir = create_rbi_directory()
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"rbi_news_{timestamp}.txt"
    filepath = os.path.join(rbi_dir, filename)
    
    # Group data by date and sort by date (newest first)
    date_groups = defaultdict(list)
    for item in data:
        date = item['date']
        date_groups[date].append(item)
    
    # Sort dates - try to parse them for proper sorting
    sorted_dates = []
    for date_str in date_groups.keys():
        parsed_date = parse_date_string(date_str)
        if parsed_date:
            sorted_dates.append((parsed_date, date_str))
        else:
            sorted_dates.append((datetime.datetime.min, date_str))
    
    sorted_dates.sort(reverse=True, key=lambda x: x[0])
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("RBI Press Releases - Last 7 Days\n")
        f.write("="*50 + "\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n")
        f.write(f"Total items: {len(data)}\n\n")
        
        # Write each date group in sorted order
        for _, date_str in sorted_dates:
            items = date_groups[date_str]
            f.write(f"{date_str}\n")
            f.write("-" * len(date_str) + "\n")
            
            for i, item in enumerate(items, 1):
                f.write(f"{i}. {item['title']}\n")
                f.write(f"   URL: {item['url']}\n\n")
            
            f.write("\n")
    
    print(f"Saved {len(data)} items to {filepath}")
    return filepath

def main():
    """Main function"""
    print("Starting RBI Scraper...")
    print("="*40)
    
    # Extract all data first
    all_data = extract_rbi_data()
    
    if all_data:
        print(f"Total items extracted: {len(all_data)}")
        
        # Filter to last 7 days of available data
        filtered_data = filter_last_7_days_data(all_data)
        
        if filtered_data:
            # Save Markdown file with clickable links and text backup
            markdown_filename = save_to_markdown_file(filtered_data)
            text_filename = save_to_text_file(filtered_data)
            
            print(f"\n✅ Successfully scraped {len(filtered_data)} RBI items from last 7 available dates!")
            print(f"📝 Markdown file (clickable links): {markdown_filename}")
            print(f"📄 Text file (backup): {text_filename}")
            
            # Group by date and show preview
            print("\n📋 Preview by date:")
            current_date = None
            count = 0
            for item in filtered_data[:15]:  # Show first 15 items
                if item['date'] != current_date:
                    current_date = item['date']
                    print(f"\n📅 {current_date}:")
                print(f"  • {item['title']}")
                count += 1
            
            if len(filtered_data) > 15:
                print(f"\n... and {len(filtered_data) - 15} more items")
                
            # Show date distribution
            date_counts = {}
            for item in filtered_data:
                date = item['date']
                date_counts[date] = date_counts.get(date, 0) + 1
            
            print(f"\n📊 Items per date (last 7 available dates):")
            for date, count in date_counts.items():
                print(f"  {date}: {count} items")
        else:
            print("❌ No data found for the last 7 days")
            
    else:
        print("❌ No data extracted")

if __name__ == "__main__":
    main()
