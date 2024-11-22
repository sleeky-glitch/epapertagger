import streamlit as st
import pdf2image
import io
import os
from PIL import Image
import openai
from poppler import load_from_data
import tempfile
import fitz  # PyMuPDF
import re

# Set your OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]

def extract_text_from_pdf(pdf_file):
  try:
      # Create a temporary file to save the uploaded PDF
      with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
          tmp_file.write(pdf_file.getvalue())
          tmp_path = tmp_file.name

      # Open the PDF using PyMuPDF
      doc = fitz.open(tmp_path)
      text = ""

      for page in doc:
          text += page.get_text()

      # Clean up the temporary file
      os.unlink(tmp_path)

      return text
  except Exception as e:
      st.error(f"Error in PDF extraction: {str(e)}")
      return ""

def process_text_with_gpt(text, tag):
  try:
      response = openai.ChatCompletion.create(
          model="gpt-4",
          messages=[
              {"role": "system", "content": """You are a Gujarati news expert. 
              Your task is to:
              1. Identify news articles related to the given tag
              2. Translate them to English
              3. Provide a brief summary
              Format the response as:
              [Original Gujarati Text]
              [English Translation]
              [Brief Summary]
              ---"""},
              {"role": "user", "content": f"Find news related to '{tag}' in the following text and translate to English:\n\n{text}"}
          ],
          temperature=0.7,
          max_tokens=2000
      )
      return response.choices[0].message['content']
  except Exception as e:
      st.error(f"Error in GPT processing: {str(e)}")
      return ""

def main():
  st.title("ગુજરાતી સમાચાર શોધક (Gujarati News Finder)")
  st.write("Upload a Gujarati newspaper PDF and search for specific topics")

  # File uploader
  pdf_file = st.file_uploader("Upload PDF file", type=['pdf'])

  # Tag input
  search_tag = st.text_input("Enter search tag (in English or Gujarati)")

  if pdf_file is not None and search_tag:
      try:
          # Show progress
          with st.spinner('Processing PDF...'):
              extracted_text = extract_text_from_pdf(pdf_file)

          if extracted_text:
              with st.spinner('Analyzing content...'):
                  results = process_text_with_gpt(extracted_text, search_tag)

              # Display results in a nice format
              st.subheader("Search Results")

              if results:
                  # Split results into sections
                  sections = results.split('---')

                  for section in sections:
                      if section.strip():
                          st.markdown(section.strip())
                          st.markdown("---")
              else:
                  st.warning("No relevant news found for the given tag.")

      except Exception as e:
          st.error(f"An error occurred: {str(e)}")

  # Add footer with instructions
  st.markdown("""
  ### Instructions:
  1. Upload a Gujarati newspaper in PDF format
  2. Enter a search tag (topic you're interested in)
  3. Wait for the analysis to complete
  4. View the original text, translation, and summary
  """)

if __name__ == "__main__":
  main()
