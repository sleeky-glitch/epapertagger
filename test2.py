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
            model="gpt-4o-mini",  # Using the specified model  
            messages=[  
                {  
                    "role": "system",  
                    "content": """You are a Gujarati newspaper expert. Analyze the image, find all relevant news related to the given tag,   
                    and provide the following for each news item:  
                    1. The original Gujarati text  
                    2. English translation  
                    3. Detailed summary  
                    Format as:  
                    [Original Gujarati Text]  
                    [English Translation]  
                    [Detailed Summary]  
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
    st.write("Upload Gujarati newspaper PDFs and search for specific topics")  

    # File upload (accept multiple files)  
    pdf_files = st.file_uploader(  
        "Upload PDF files",  
        type=['pdf'],  
        accept_multiple_files=True,  
        help="Upload Gujarati newspapers in PDF format"  
    )  

    # Tag input  
    search_tag = st.text_input(  
        "Enter search tag",  
        placeholder="Enter topic in English or Gujarati",  
        help="Enter the topic you want to search for in the newspapers"  
    )  

    # Process button  
    if st.button("Process Newspapers 📰", key="process_btn"):  
        if not pdf_files:  
            st.error("Please upload at least one PDF file!")  
            return  
        if not search_tag:  
            st.error("Please enter a search tag!")  
            return  

        try:  
            # Process each uploaded PDF file  
            for pdf_file in pdf_files:  
                st.markdown(f"### Processing file: {pdf_file.name}")  
                progress_bar = st.progress(0, f"Starting processing for {pdf_file.name}...")  

                # Process PDF with GPT-4 Vision  
                results = process_pdf(pdf_file, search_tag, progress_bar)  

                if results:  
                    # Display results  
                    st.success(f"Processing complete for {pdf_file.name}!")  
                    st.markdown("### 🔍 Search Results")  

                    # Split results into sections  
                    sections = results.split('---')  

                    for idx, section in enumerate(sections, 1):  
                        if section.strip():  
                            with st.container():  # Use container for separate boxes  
                                st.markdown(f"#### News Item {idx}")  
                                st.markdown(section.strip())  
                                st.markdown("---")  # Add a horizontal line for separation  
                else:  
                    st.error(f"No relevant news found in {pdf_file.name}.")  

        except Exception as e:  
            st.error(f"An error occurred: {str(e)}")  

    # Help section  
    with st.expander("ℹ️ How to use"):  
        st.markdown("""  
        1. **Upload PDFs**: Click 'Browse files' to upload one or more Gujarati newspapers  
        2. **Enter Tag**: Type the topic you want to search for  
        3. **Process**: Click 'Process Newspapers' button  
        4. **View Results**: See original text, translation, and summary  

        **Note**:   
        - Processing may take a few minutes depending on the PDF size  
        - The app works with both searchable and scanned PDFs  
        """)  


if __name__ == "__main__":  
    main()  
