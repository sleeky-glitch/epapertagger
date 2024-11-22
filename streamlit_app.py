import streamlit as st
import fitz  # PyMuPDF
import openai
import os
import tempfile
import time
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.colored_header import colored_header
from streamlit_extras.app_logo import add_logo

# Set page configuration
st.set_page_config(
  page_title="ગુજરાતી સમાચાર શોધક",
  page_icon="📰",
  layout="wide",
  initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
  <style>
  .stButton>button {
      width: 100%;
      border-radius: 5px;
      height: 3em;
      background-color: #FF4B4B;
      color: white;
      font-weight: bold;
  }
  .success-message {
      padding: 1rem;
      border-radius: 0.5rem;
      background-color: #D4EDDA;
      color: #155724;
      margin: 1rem 0;
  }
  .error-message {
      padding: 1rem;
      border-radius: 0.5rem;
      background-color: #F8D7DA;
      color: #721C24;
      margin: 1rem 0;
  }
  .info-box {
      padding: 1rem;
      border-radius: 0.5rem;
      background-color: #E2E3E5;
      margin: 1rem 0;
  }
  </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processed_text' not in st.session_state:
  st.session_state.processed_text = None
if 'current_stage' not in st.session_state:
  st.session_state.current_stage = 'upload'

# Set your OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]

def extract_text_from_pdf(pdf_file, progress_bar):
  try:
      # Create a temporary file
      with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
          tmp_file.write(pdf_file.getvalue())
          tmp_path = tmp_file.name

      # Open the PDF using PyMuPDF
      doc = fitz.open(tmp_path)
      text = ""

      # Update progress bar while processing pages
      total_pages = len(doc)
      for i, page in enumerate(doc):
          text += page.get_text()
          progress_bar.progress((i + 1) / total_pages, 
                             f"Processing page {i + 1} of {total_pages}")
          time.sleep(0.1)  # Add slight delay for visual feedback

      # Clean up
      os.unlink(tmp_path)
      return text
  except Exception as e:
      st.error(f"Error in PDF extraction: {str(e)}")
      return ""

def process_text_with_gpt(text, tag, progress_bar):
  try:
      progress_bar.progress(0.3, "Analyzing content with AI...")

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

      progress_bar.progress(1.0, "Analysis complete!")
      return response.choices[0].message['content']
  except Exception as e:
      st.error(f"Error in GPT processing: {str(e)}")
      return ""

def main():
  # Add logo or header image
  colored_header(
      label="ગુજરાતી સમાચાર શોધક (Gujarati News Finder)",
      description="Upload a Gujarati newspaper PDF and search for specific topics",
      color_name="red-70"
  )

  # Create columns for layout
  col1, col2 = st.columns([2, 1])

  with col1:
      # File upload section
      pdf_file = st.file_uploader(
          "Upload PDF file", 
          type=['pdf'],
          help="Upload a Gujarati newspaper in PDF format"
      )

      # Tag input section
      search_tag = st.text_input(
          "Enter search tag",
          placeholder="Enter topic in English or Gujarati",
          help="Enter the topic you want to search for in the newspaper"
      )

      # Process button
      if st.button("Process Newspaper 📰", key="process_btn"):
          if pdf_file is None:
              st.error("Please upload a PDF file first!")
              return
          if not search_tag:
              st.error("Please enter a search tag!")
              return

          try:
              # Create progress bars
              pdf_progress = st.progress(0, "Starting PDF processing...")

              # Extract text
              extracted_text = extract_text_from_pdf(pdf_file, pdf_progress)

              if extracted_text:
                  # Create another progress bar for GPT processing
                  gpt_progress = st.progress(0, "Starting AI analysis...")

                  # Process with GPT
                  results = process_text_with_gpt(extracted_text, search_tag, gpt_progress)

                  if results:
                      st.session_state.processed_text = results
                      st.session_state.current_stage = 'results'
                      st.experimental_rerun()
                  else:
                      st.warning("No relevant news found for the given tag.")
              else:
                  st.error("Could not extract text from the PDF.")

          except Exception as e:
              st.error(f"An error occurred: {str(e)}")

  with col2:
      # Help section
      with st.expander("ℹ️ How to use"):
          st.markdown("""
          1. **Upload PDF**: Click 'Browse files' to upload your Gujarati newspaper
          2. **Enter Tag**: Type the topic you want to search for
          3. **Process**: Click 'Process Newspaper' button
          4. **View Results**: See original text, translation, and summary
          """)

  # Display results if available
  if st.session_state.current_stage == 'results' and st.session_state.processed_text:
      st.markdown("### 🔍 Search Results")

      # Split results into sections
      sections = st.session_state.processed_text.split('---')

      for idx, section in enumerate(sections, 1):
          if section.strip():
              with st.expander(f"News Item {idx}", expanded=True):
                  st.markdown(section.strip())

      # Reset button
      if st.button("Start New Search 🔄"):
          st.session_state.processed_text = None
          st.session_state.current_stage = 'upload'
          st.experimental_rerun()

  # Footer
  st.markdown("---")
  st.markdown(
      """
      <div style='text-align: center; color: #666;'>
      Made with ❤️ by Your Name | 
      <a href="mailto:your@email.com">Contact Support</a>
      </div>
      """, 
      unsafe_allow_html=True
  )

if __name__ == "__main__":
  main()
