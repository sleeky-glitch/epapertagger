import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import io
import base64
from PIL import Image
import time
import os
import json
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="ગુજરાતી સમાચાર શોધક",
    page_icon="📰",
    layout="wide",
)

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state
if 'indexed_files' not in st.session_state:
    st.session_state.indexed_files = {}
if 'processed_cache' not in st.session_state:
    st.session_state.processed_cache = {}

# Constants
DATA_DIR = Path("data")
CACHE_FILE = DATA_DIR / "processed_cache.json"

def load_cache():
    """Load processed results from cache file"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache():
    """Save processed results to cache file"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(st.session_state.processed_cache, f, ensure_ascii=False, indent=2)

def encode_image_to_base64(image):
    """Convert PIL Image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

def convert_pdf_page_to_image(page):
    """Convert a PDF page to PIL Image"""
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_data = pix.tobytes("jpeg")
    return Image.open(io.BytesIO(img_data))

def process_image_with_gpt4_vision(image, tag):
    """Process image using GPT-4 Vision API"""
    try:
        base64_image = encode_image_to_base64(image)

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "system",
                    "content": """You are a Gujarati newspaper expert. Analyze the image, find all relevant news related to the given tag, 
                    and provide the following for each news item:
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
                        {"type": "text", "text": f"Find all news related to '{tag}' in this newspaper image. Extract and translate the relevant text."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
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

def index_pdf_files():
    """Index all PDF files in the data directory at startup"""
    if not DATA_DIR.exists():
        os.makedirs(DATA_DIR)
        return

    pdf_files = list(DATA_DIR.glob("*.pdf"))
    with st.spinner("Indexing PDF files..."):
        for pdf_path in pdf_files:
            if pdf_path.name not in st.session_state.indexed_files:
                st.session_state.indexed_files[pdf_path.name] = str(pdf_path)

def process_pdf(pdf_path, tag, progress_bar):
    """Process PDF using PyMuPDF and GPT-4 Vision"""
    try:
        # Check if results are already cached
        cache_key = f"{pdf_path}_{tag}"
        if cache_key in st.session_state.processed_cache:
            return st.session_state.processed_cache[cache_key]

        doc = fitz.open(pdf_path)
        all_results = []
        total_pages = len(doc)

        for i, page in enumerate(doc):
            progress_bar.progress((i + 1) / total_pages,
                              f"Processing page {i + 1} of {total_pages}")

            image = convert_pdf_page_to_image(page)

            if i == 0:
                st.image(image, caption=f"Processing Page {i+1}", use_column_width=True)

            result = process_image_with_gpt4_vision(image, tag)
            if result:
                all_results.append(result)

            time.sleep(1)

        doc.close()

        # Cache the results
        final_result = "\n".join(all_results)
        st.session_state.processed_cache[cache_key] = final_result
        save_cache()

        return final_result

    except Exception as e:
        st.error(f"Error in PDF processing: {str(e)}")
        return None

def main():
    # Load cache at startup
    st.session_state.processed_cache = load_cache()

    # Index PDF files at startup
    index_pdf_files()

    st.title("ગુજરાતી સમાચાર શોધક (Gujarati News Finder)")
    st.write("Search through indexed Gujarati newspapers")

    # Display indexed files
    st.sidebar.header("Indexed Files")
    selected_files = st.sidebar.multiselect(
        "Select files to search",
        options=list(st.session_state.indexed_files.keys())
    )

    # Tag input
    search_tag = st.text_input(
        "Enter search tag",
        placeholder="Enter topic in English or Gujarati",
        help="Enter the topic you want to search for in the newspapers"
    )

    # Process button
    if st.button("Search Newspapers 📰", key="process_btn"):
        if not selected_files:
            st.error("Please select at least one file!")
            return
        if not search_tag:
            st.error("Please enter a search tag!")
            return

        try:
            for filename in selected_files:
                pdf_path = st.session_state.indexed_files[filename]
                st.markdown(f"### Processing file: {filename}")
                progress_bar = st.progress(0, f"Starting processing for {filename}...")

                results = process_pdf(pdf_path, search_tag, progress_bar)

                if results:
                    st.success(f"Processing complete for {filename}!")
                    st.markdown("### 🔍 Search Results")

                    sections = results.split('---')
                    for idx, section in enumerate(sections, 1):
                        if section.strip():
                            with st.container():
                                st.markdown(f"#### News Item {idx}")
                                st.markdown(section.strip())
                                st.markdown("---")
                else:
                    st.error(f"No relevant news found in {filename}.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    # Help section
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. **Select Files**: Choose files from the sidebar
        2. **Enter Tag**: Type the topic you want to search for
        3. **Search**: Click 'Search Newspapers' button
        4. **View Results**: See original text, translation, and summary

        **Note**:
        - Processing may take a few minutes for new searches
        - Results are cached for faster subsequent searches
        """)

if __name__ == "__main__":
    main()
