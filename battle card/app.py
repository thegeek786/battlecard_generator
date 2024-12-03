from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re
from markupsafe import Markup
import pandas as pd
from io import BytesIO

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

app = Flask(__name__)

# Function to scrape data from URLs
def scraper(urls):
    scraped_data = {}
    for url in urls:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.find('title').get_text() if soup.find('title') else 'No Title'
                text = soup.get_text(separator=' ', strip=True)
                
                # Limit text length for display
                scraped_data[url] = {
                    'title': title,
                    'text': text[:200],  # Limit text length for display
                }
            else:
                print(f"Failed to retrieve {url}: Status code {response.status_code}")
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    return scraped_data

# Function to process text for SWOT analysis
def process_swot_text(text):
    """Replace '**' markers with HTML heading tags and '*' with bullet points."""
    text = re.sub(r'\*\*(.*?)\*\*', r'<h2>\1</h2>', text)
    text = re.sub(r'\*\s(.*?)\s*(?=\n|$)', r'<li>\1</li>', text)
    text = re.sub(r'(<li>.*?</li>)(\s*<li>.*?</li>)*', r'<ul>\1</ul>', text, flags=re.DOTALL)
    return Markup(text)

# Function to generate SWOT analysis and battlecard using Gemini API
def generation_of_op(data):
    try:
        swot_results = {}
        battlecard_data = []

        for brand, content in data.items():
            prompt = f"Create a SWOT analysis only for the brand '{brand}' :\n\n"
            for url, info in content.items():
                prompt += f"URL: {url}\nTitle: {info['title']}\nText: {info['text'][:200]}...\n\n"
            
            response = chat.send_message(prompt)
            processed_swot = process_swot_text(response.text)  # Process SWOT text
            swot_results[brand] = processed_swot
        
        # Create a battlecard comparing the brands
        battlecard_prompt = "Create a battlecard in the form of a table comparing them and include metrics and numeric data and do not include key difference and SWOT:\n\n"
        for brand in swot_results:
            battlecard_prompt += f"Brand: {brand}\nSWOT Analysis: {swot_results[brand]}\n\n"
        
        battlecard_response = chat.send_message(battlecard_prompt)
        battlecard_text = battlecard_response.text
        
        # Convert battlecard text to table format
        lines = [line.strip() for line in battlecard_text.split('\n') if line.strip()]
        if not lines:
            return swot_results, "", None

        # Assuming the first line contains headers
        try:
            headers = [header.strip() for header in lines[0].split('|')[1:-1]]
            table_data = [line.split('|')[1:-1] for line in lines[2:]]  # Skip the header and separator lines

            # Check if all rows have the same number of columns as headers
            if any(len(row) != len(headers) for row in table_data):
                raise ValueError("Mismatch between number of columns in header and rows")

            # Create a DataFrame and save as Excel
            df = pd.DataFrame(table_data, columns=headers)
            excel_io = BytesIO()
            df.to_excel(excel_io, index=False, engine='openpyxl')
            excel_io.seek(0)
            
            return swot_results, battlecard_text, excel_io
        except Exception as e:
            print(f"Error processing battlecard table: {e}")
            return swot_results, battlecard_text, None

    except Exception as e:
        print(f"Error generating SWOT analysis and battlecard: {e}")
        return {}, "", None

# Function to convert Markdown table to DataFrame
def md_table_to_dataframe(md_content):
    # Split the Markdown content into lines
    lines = md_content.strip().split('\n')
    
    # Initialize list to store rows
    table_data = []
    
    for line in lines:
        if '|' in line:  # Only process lines with '|'
            # Remove leading and trailing '|', then split by '|'
            row_data = [col.strip() for col in line.strip('|').split('|')]
            table_data.append(row_data)
    
    # The first row should be headers
    if len(table_data) > 1:
        headers = table_data[0]
        data = table_data[1:]
        df = pd.DataFrame(data, columns=headers)
    else:
        df = pd.DataFrame()
    
    return df

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        brand_name = request.form.get('brand_name')
        brand_urls = request.form.get('brand_urls').split(',')
        num_competitors = int(request.form.get('num_competitors'))
        competitors = {}
        
        for i in range(num_competitors):
            competitor_name = request.form.get(f'competitor_name_{i}')
            competitor_urls = request.form.get(f'competitor_urls_{i}').split(',')
            competitors[competitor_name] = competitor_urls

        if brand_name and brand_urls and all(competitors.keys()):
            # Scrape data
            data = {
                brand_name: scraper(brand_urls),
            }
            for competitor_name, competitor_urls in competitors.items():
                data[competitor_name] = scraper(competitor_urls)
            
            # Generate SWOT analysis and battlecard
            swot_analysis, battlecard, excel_file = generation_of_op(data)
            
            if swot_analysis:
                # Save the battlecard temporarily
                file_name = "finalized_battlecard.md"
                with open(file_name, "w") as file:
                    file.write(battlecard)
                
                # Show results with an edit option
                return render_template('results.html', swot_analysis=swot_analysis, battlecard=battlecard, excel_file=excel_file)

        return "Please fill in all the fields."

    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save():
    battlecard_text = request.form.get('battlecard_text')
    file_name = "finalized_battlecard.md"
    
    with open(file_name, "w") as file:
        file.write(battlecard_text)
    
    # Convert Markdown to Excel and return as a download
    with open(file_name, "r") as file:
        md_content = file.read()
    
    df = md_table_to_dataframe(md_content)
    if not df.empty:
        excel_io = BytesIO()
        df.to_excel(excel_io, index=False, engine='openpyxl')
        excel_io.seek(0)
        return send_file(excel_io, as_attachment=True, download_name='finalized_battlecard.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    return send_file(file_name, as_attachment=True)
@app.route('/feedback', methods=['POST'])
def feedback():
    feedback_text = request.form.get('feedback')
    
    if feedback_text:
        # Save feedback to a file (or database)
        with open("feedback.txt", "a") as file:
            file.write(feedback_text + "\n\n")
        
        return "Thank you for your feedback! It has been recorded."
    
    return "Feedback cannot be empty."

if __name__ == '__main__':
    app.run(debug=True)
