import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import io
import base64
from PIL import Image
import time

# Set page configuration
st.set_page_config(
  page_title="ગુજરાતી સમાચાર શોધક",
  page_icon="📰",
  layout="wide",
)

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state
if 'processed_text' not in st.session_state:
  st.session_state.processed_text = None
if 'current_stage' not in st.session_state:
  st.session_state.current_stage = 'upload'

def encode_image_to_base64(image):
  """Convert PIL Image to base64 string"""
  buffered = io.BytesIO()
  image.save(buffered, format="JPEG")
  return base64.b64encode(buffered.getvalue()).decode()

def convert_pdf_page_to_image(page):
  """Convert a PDF page to PIL Image"""
  pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
  img_data = pix.tobytes("jpeg")
  return Image.open(io.BytesIO(img_data))

def process_image_with_gpt4_vision(image, tag):
  """Process image using GPT-4 Vision API"""
  try:
      base64_image = encode_image_to_base64(image)

      response = client.chat.completions.create(
          model="gpt-4o-mini",  # Updated model name
          messages=[
              {
                  "role": "system",
                  "content": """You are a Gujarati newspaper expert. Analyze the image, find relevant news related to the given tag, 
                  and provide the following:
                  1. The original Gujarati text
                  2. English translation
                  3. Brief summary
                  Format as:
                  [Original Gujarati Text]
                  [English Translation]
                  [Brief Summary]
                  ---"""
              },
              {
                  "role": "user",
                  "content": [
                      {
                          "type": "text",
                          "text": f"Find news related to '{tag}' in this newspaper image. Extract and translate the relevant text."
                      },
                      {
                          "type": "image_url",
                          "image_url": f"data:image/jpeg;base64,{base64_image}"
                      }
                  ]
              }
          ],
          max_tokens=4096
      )
      return response.choices[0].message.content
  except Exception as e:
      st.error(f"Error in GPT-4 Vision processing: {str(e)}")
      return None

def process_pdf(pdf_file, tag, progress_bar):
  """Process PDF using PyMuPDF and GPT-4 Vision"""
  try:
      # Read PDF file
      pdf_data = pdf_file.read()
      doc = fitz.open(stream=pdf_data, filetype="pdf")

      all_results = []
      total_pages = len(doc)

      for i, page in enumerate(doc):
          # Update progress
          progress_bar.progress((i + 1) / total_pages, 
                             f"Processing page {i + 1} of {total_pages}")

          # Convert PDF page to image
          image = convert_pdf_page_to_image(page)

          # Display preview of current page
          if i == 0:  # Show first page preview
              st.image(image, caption=f"Processing Page {i+1}", use_column_width=True)

          # Process image with GPT-4 Vision
          result = process_image_with_gpt4_vision(image, tag)
          if result:
              all_results.append(result)

          # Add a small delay between API calls to avoid rate limits
          time.sleep(1)

      doc.close()
      return "\n".join(all_results)

  except Exception as e:
      st.error(f"Error in PDF processing: {str(e)}")
      return None

def main():
  st.title("ગુજરાતી સમાચાર શોધક (Gujarati News Finder)")
  st.write("Upload a Gujarati newspaper PDF and search for specific topics")

  # File upload
  pdf_file = st.file_uploader(
      "Upload PDF file", 
      type=['pdf'],
      help="Upload a Gujarati newspaper in PDF format"
  )

  # Tag input
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
          # Show processing progress
          progress_bar = st.progress(0, "Starting PDF processing...")

          # Process PDF with GPT-4 Vision
          results = process_pdf(pdf_file, search_tag, progress_bar)

          if results:
              # Display results
              st.success("Processing complete!")
              st.markdown("### 🔍 Search Results")

              # Split results into sections
              sections = results.split('---')

              for idx, section in enumerate(sections, 1):
                  if section.strip():
                      with st.expander(f"News Item {idx}", expanded=True):
                          st.markdown(section.strip())
          else:
              st.error("No relevant news found in the PDF.")

      except Exception as e:
          st.error(f"An error occurred: {str(e)}")

  # Help section
  with st.expander("ℹ️ How to use"):
      st.markdown("""
      1. **Upload PDF**: Click 'Browse files' to upload your Gujarati newspaper
      2. **Enter Tag**: Type the topic you want to search for
      3. **Process**: Click 'Process Newspaper' button
      4. **View Results**: See original text, translation, and summary

      **Note**: 
      - Processing may take a few minutes depending on the PDF size
      - The app works with both searchable and scanned PDFs
      """)

if __name__ == "__main__":
  main()
