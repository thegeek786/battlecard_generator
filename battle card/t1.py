import streamlit as st
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

# Function to scrape data from URLs
def scrape_data_from_urls(urls):
    scraped_data = {}
    for url in urls:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.find('title').get_text() if soup.find('title') else 'No Title'
                text = soup.get_text(separator=' ', strip=True)
                scraped_data[url] = {
                    'title': title,
                    'text': text[:-1],  # Limit text length for display
                }
            else:
                st.warning(f"Failed to retrieve {url}: Status code {response.status_code}")
        except Exception as e:
            st.error(f"Error scraping {url}: {e}")
    return scraped_data

# Function to generate SWOT analysis using Gemini API
def generate_swot_analysis(data):
    try:
        prompt = "Based on the following data, Create a tabular data for SWOT Analysis and Battle Card Include metrics in Battle card. Both Battle card and SWOT Analysis should be as a table:\n\n"
        for brand, content in data.items():
            prompt += f"Brand: {brand}\n"
            for url, info in content.items():
                prompt += f"URL: {url}\nTitle: {info['title']}\nText: {info['text'][:-1]}...\n\n"
        
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating SWOT analysis: {e}")
        return ""

# Streamlit UI
st.set_page_config(page_title="SWOT Analysis Generator")
st.header("SWOT Analysis Generator")

# Input section for brand name and URLs
st.subheader("Enter Brand and Competitors Information")

brand_name = st.text_input("Enter Your Brand Name")
brand_urls = st.text_area("Enter URLs for Your Brand (comma-separated)").split(',')

competitor_1_name = st.text_input("Enter Competitor 1 Name")
competitor_1_urls = st.text_area("Enter URLs for Competitor 1 (comma-separated)").split(',')

competitor_2_name = st.text_input("Enter Competitor 2 Name")
competitor_2_urls = st.text_area("Enter URLs for Competitor 2 (comma-separated)").split(',')

# Button to start the process
if st.button("Generate SWOT Analysis"):
    if brand_name and brand_urls and competitor_1_name and competitor_1_urls and competitor_2_name and competitor_2_urls:
        st.write("Scraping data from URLs...")
        
        # Scrape data
        data = {
            brand_name: scrape_data_from_urls(brand_urls),
            competitor_1_name: scrape_data_from_urls(competitor_1_urls),
            competitor_2_name: scrape_data_from_urls(competitor_2_urls),
        }
        
        # Display the scraped data
        st.subheader("Scraped Data")
        for brand, content in data.items():
            st.write(f"### Brand: {brand}")
            for url, info in content.items():
                st.write(f"**URL:** {url}")
                st.write(f"**Title:** {info['title']}")
                st.write(f"**Text:** {info['text']}")
                st.write("-" * 50)
        
        st.write("Generating SWOT Analysis...")
        
        # Generate SWOT analysis
        swot_analysis = generate_swot_analysis(data)
        if swot_analysis:
            st.subheader("SWOT Analysis")
            st.write(swot_analysis)
    else:
        st.warning("Please fill in all the fields.")
