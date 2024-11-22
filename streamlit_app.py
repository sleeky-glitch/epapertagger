import streamlit as st
import fitz  # PyMuPDF
import openai
import os
import tempfile
import time
from PIL import Image
import io
import base64
from streamlit_extras.colored_header import colored_header

# Set page configuration
st.set_page_config(
  page_title="ગુજરાતી સમાચાર શોધક",
  page_icon="📰",
  layout="wide",
  initial_sidebar_state="expanded"
)

# Custom CSS
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
if 'pdf_content' not in st.session_state:
  st.session_state.pdf_content = None

# Set OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]

def display_pdf(pdf_file):
  """Display the first page of the PDF as an image"""
  try:
      doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
      page = doc[0]  # First page
      pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution
      img_bytes = pix.tobytes()
      img = Image.frombytes("RGB", [pix.width, pix.height], img_bytes)

      # Convert to bytes for displaying
      buf = io.BytesIO()
      img.save(buf, format='PNG')
      st.image(buf, caption="First page preview", use_column_width=True)

      # Reset file pointer
      pdf_file.seek(0)
      return True
  except Exception as e:
      st.error(f"Error displaying PDF preview: {str(e)}")
      return False

def extract_text_from_pdf(pdf_file, progress_bar):
  """Enhanced PDF text extraction with better error handling"""
  try:
      # Create a temporary file
      with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
          tmp_file.write(pdf_file.getvalue())
          tmp_path = tmp_file.name

      # Open the PDF
      doc = fitz.open(tmp_path)
      text = []
      total_pages = len(doc)

      if total_pages == 0:
          raise ValueError("The PDF appears to be empty")

      # Process each page
      for i, page in enumerate(doc):
          # Extract text with enhanced parameters
          page_text = page.get_text("text", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)
          text.append(page_text)

          # Update progress
          progress_bar.progress((i + 1) / total_pages, 
                             f"Processing page {i + 1} of {total_pages}")
          time.sleep(0.1)

      # Clean up
      doc.close()
      os.unlink(tmp_path)

      extracted_text = "\n".join(text)

      # Verify extracted text
      if not extracted_text.strip():
          raise ValueError("No text could be extracted from the PDF")

      return extracted_text

  except Exception as e:
      st.error(f"Error in PDF extraction: {str(e)}")
      if "tmp_path" in locals():
          try:
              os.unlink(tmp_path)
          except:
              pass
      return None

def process_text_with_gpt(text, tag, progress_bar):
  try:
      progress_bar.progress(0.3, "Analyzing content with AI...")

      # Split text into chunks if too long
      max_chunk_size = 4000
      chunks = [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]

      all_results = []
      for i, chunk in enumerate(chunks):
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
                  {"role": "user", "content": f"Find news related to '{tag}' in the following text and translate to English:\n\n{chunk}"}
              ],
              temperature=0.7,
              max_tokens=2000
          )
          all_results.append(response.choices[0].message['content'])
          progress_bar.progress((i + 1) / len(chunks), f"Processing chunk {i + 1} of {len(chunks)}")

      progress_bar.progress(1.0, "Analysis complete!")
      return "\n".join(all_results)
  except Exception as e:
      st.error(f"Error in GPT processing: {str(e)}")
      return None

def main():
  colored_header(
      label="ગુજરાતી સમાચાર શોધક (Gujarati News Finder)",
      description="Upload a Gujarati newspaper PDF and search for specific topics",
      color_name="red-70"
  )

  col1, col2 = st.columns([2, 1])

  with col1:
      pdf_file = st.file_uploader(
          "Upload PDF file", 
          type=['pdf'],
          help="Upload a Gujarati newspaper in PDF format"
      )

      if pdf_file:
          st.session_state.pdf_content = pdf_file.read()
          pdf_file.seek(0)  # Reset file pointer
          display_pdf(pdf_file)

      search_tag = st.text_input(
          "Enter search tag",
          placeholder="Enter topic in English or Gujarati",
          help="Enter the topic you want to search for in the newspaper"
      )

      if st.button("Process Newspaper 📰", key="process_btn"):
          if pdf_file is None:
              st.error("Please upload a PDF file first!")
              return
          if not search_tag:
              st.error("Please enter a search tag!")
              return

          try:
              # PDF Processing
              pdf_progress = st.progress(0, "Starting PDF processing...")
              extracted_text = extract_text_from_pdf(pdf_file, pdf_progress)

              if extracted_text:
                  # Show sample of extracted text for verification
                  with st.expander("Preview of extracted text"):
                      st.text(extracted_text[:500] + "...")

                  # GPT Processing
                  gpt_progress = st.progress(0, "Starting AI analysis...")
                  results = process_text_with_gpt(extracted_text, search_tag, gpt_progress)

                  if results:
                      st.session_state.processed_text = results
                      st.session_state.current_stage = 'results'
                      st.experimental_rerun()
                  else:
                      st.warning("No relevant news found for the given tag.")
              else:
                  st.error("Could not extract text from the PDF. Please ensure the PDF contains searchable text.")
                  st.info("Tip: If the PDF is scanned, it might need OCR processing first.")

          except Exception as e:
              st.error(f"An error occurred: {str(e)}")

  with col2:
      with st.expander("ℹ️ How to use"):
          st.markdown("""
          1. **Upload PDF**: Click 'Browse files' to upload your Gujarati newspaper
          2. **Enter Tag**: Type the topic you want to search for
          3. **Process**: Click 'Process Newspaper' button
          4. **View Results**: See original text, translation, and summary

          **Note**: 
          - The PDF should contain searchable text
          - Scanned PDFs might not work directly
          - Large PDFs might take longer to process
          """)

  # Display results
  if st.session_state.current_stage == 'results' and st.session_state.processed_text:
      st.markdown("### 🔍 Search Results")

      sections = st.session_state.processed_text.split('---')

      for idx, section in enumerate(sections, 1):
          if section.strip():
              with st.expander(f"News Item {idx}", expanded=True):
                  st.markdown(section.strip())

      if st.button("Start New Search 🔄"):
          st.session_state.processed_text = None
          st.session_state.current_stage = 'upload'
          st.session_state.pdf_content = None
          st.experimental_rerun()

  st.markdown("---")
  st.markdown(
      """
      <div style='text-align: center; color: #666;'>
      Made with ❤️ by BeyonData | 
      <a href="mailto:nishant.tomar@beyondatagroup.com">Contact Support</a>
      </div>
      """, 
      unsafe_allow_html=True
  )

if __name__ == "__main__":
  main()
