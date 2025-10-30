from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from bytez import Bytez
from youtube_transcript_api import YouTubeTranscriptApi
import gradio as gr
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, parse_qs

load_dotenv("secrets.env")

api_key = os.getenv("BYTEZ_API_KEY")
sdk = Bytez(api_key)

#toy function
def video_id_extractor(link):
    if "watch?v=" in link:
        return link[32:43]
    else:
        return link[17:28]

#production ready function
def video_id_extractor(link):
    parsed_url = urlparse(link)
    
    if "youtube.com" in parsed_url.netloc:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    
    elif "youtu.be" in parsed_url.netloc:
        return parsed_url.path.lstrip("/")
    
    return None

def generate_transcript(video_id):
    trans = YouTubeTranscriptApi()
    try:
        transcript_raw = trans.fetch(video_id = video_id)
    except Exception:
        return None
    transcript = ""
    for i in transcript_raw.snippets:
        transcript += f" {i.text}"
    return transcript

def create_and_save_vs(trans):
    try:
        splitter = RecursiveCharacterTextSplitter(chunk_size = 100, chunk_overlap = 50)
        docs = splitter.split_text(trans)
        embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-mpnet-base-v2')
        vector_store_db = Chroma.from_texts(docs, embeddings, persist_directory='chroma_db')
    except Exception:
        return None
    return vector_store_db

def generate_summary(trans):
    try: 
        model = sdk.model("openai/gpt-4o")
        if len(trans.split(" ")) > 90000:
            trans = trans.split(" ")[0:85000]
            trans = " ".join(trans)
    except Exception:
        return None
    Inp = [{"role": "system", "content": "You are a youtube transcipt sammurizer. Sammurize the transcript under 100 words"}, {"role":"user", "content":trans}]
    trails = 4
    failed = True
    time_to_sleep = 3
    while failed and trails > 0:
        res = model.run(Inp)
        if type(res) == list and len(res) == 3:
            failed = False
            trails -= 1
            return res[0]["content"]
        else:
            time.sleep(time_to_sleep)
            time_to_sleep = time_to_sleep **2
            trails -= 1
    return None

def setter(link):
    yield gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "", ""
    video_id = video_id_extractor(link)
    if not video_id:
        yield gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), "", ""
    transcript = generate_transcript(video_id)
    if not transcript:
        yield gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "", ""
    vectorstore = create_and_save_vs(transcript)
    if not vectorstore:
        yield gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), "", ""
    summary = generate_summary(transcript)
    if not summary:
        yield gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), "", ""
    yield gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), summary, vectorstore

def execute(vec, query):
    try:
        res = vec.similarity_search(query, k=3)
        result = ""
        for i in res:
            result += f"\n{i.page_content}"
        model = sdk.model("openai/gpt-4o")
        inp = [{"role": "system", "content": "You are a helpful assistant - you will be asked a query and provided with a context. You have to answer that query based on the provided context - do not make things up. Do not reveal the whole context, answer as like you already knew the context"}, {"role":"user", "content":f"query: {query} | context: {result}"}]
        res = model.run(inp)
        return res[0]['content'], gr.update(visible=True), gr.update(visible=False)
    except Exception:
        return "", gr.update(visible=False), gr.update(visible=True)

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="indigo",
    ),
    css="""
        /* Global Styles */
        .gradio-container {
            font-family: 'Inter', 'Segoe UI', sans-serif !important;
            max-width: 1200px !important;
            margin: 0 auto !important;
        }
        
        /* Header Branding */
        .header-brand {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
            animation: fadeInDown 0.8s ease-out;
        }
        
        .header-brand h1 {
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header-brand p {
            color: rgba(255,255,255,0.95);
            font-size: 1.1rem;
            margin: 0.5rem 0 0 0;
        }
        
        /* Footer Branding */
        .footer-brand {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin-top: 2rem;
            text-align: center;
            box-shadow: 0 -5px 20px rgba(102, 126, 234, 0.2);
        }
        
        .footer-brand p {
            color: white;
            margin: 0.3rem 0;
            font-size: 0.95rem;
        }
        
        .footer-brand a {
            color: #ffd700;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .footer-brand a:hover {
            color: #fff;
            text-shadow: 0 0 10px rgba(255,255,255,0.5);
        }
        
        /* Main Title Animation */
        .main-title {
            background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
            background-size: 200% auto;
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.4);
            animation: gradientShift 3s ease infinite, fadeIn 1s ease-out;
        }
        
        /* Button Styles */
        .gr-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 12px 32px !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .gr-button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 25px rgba(102, 126, 234, 0.6) !important;
        }
        
        .gr-button:active {
            transform: translateY(0px) !important;
        }
        
        /* Input Fields */
        .gr-textbox, .gr-text-input {
            border-radius: 8px !important;
            border: 2px solid #e0e7ff !important;
            transition: all 0.3s ease !important;
        }
        
        .gr-textbox:focus, .gr-text-input:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        }
        
        /* Loading Animation */
        .loading-container {
            text-align: center;
            padding: 3rem;
        }
        
        .loading-text {
            font-size: 1.5rem;
            color: #667eea;
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        /* Error Messages */
        .error-message {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            font-size: 1.3rem;
            font-weight: 600;
            box-shadow: 0 8px 32px rgba(245, 87, 108, 0.3);
            animation: shake 0.5s ease-in-out;
        }
        
        /* Success/Summary Box */
        .summary-box {
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(168, 237, 234, 0.3);
            animation: fadeInUp 0.6s ease-out;
        }
        
        /* Chat Section */
        .chat-section {
            animation: fadeInUp 0.8s ease-out;
        }
        
        /* Animations */
        @keyframes fadeIn {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }
        
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.5;
            }
        }
        
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }
        
        @keyframes gradientShift {
            0% {
                background-position: 0% 50%;
            }
            50% {
                background-position: 100% 50%;
            }
            100% {
                background-position: 0% 50%;
            }
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .header-brand h1 {
                font-size: 1.8rem;
            }
            .main-title {
                font-size: 1.3rem;
            }
        }
    """
) as ui:
    # Header Branding
    gr.HTML("""
        <div class="header-brand">
            <h1>🎓 AI YouTube Study Assistant</h1>
            <p>Transform lengthy videos into concise knowledge</p>
        </div>
    """)
    
    vs = gr.State()
    gr.HTML('<div class="main-title">📹 Why watch long YouTube videos when you could study from AI?</div>')
    
    with gr.Row(visible=True) as first_page:
        youtube_link = gr.Textbox(
            label="Enter the youtube link here: ", 
            lines=2,
            placeholder="https://www.youtube.com/watch?v=..."
        )
        submit_button = gr.Button("SUBMIT!")
    
    with gr.Row(visible=False) as chat_page:
        with gr.Column():
            summary = gr.Markdown(elem_classes="summary-box")
            gr.Markdown("### 💬 Now ask any question about the video:")
            ques = gr.Textbox(
                label="Enter the question here: ", 
                lines=2,
                placeholder="What is the main topic of this video?"
            )
            submit_answer = gr.Button("SUBMIT!")
            answer = gr.TextArea(label="ANSWER")
    
    with gr.Row(visible=False) as wrong_link_page:
        gr.HTML('<div class="error-message">❌ Sorry, your link wasn\'t correct. Please try again!</div>')
    
    with gr.Row(visible=False) as cc_not_enabled:
        gr.HTML('<div class="error-message">⚠️ The link you provided was either not valid or subtitles weren\'t enabled in that video</div>')
    
    with gr.Row(visible=False) as loading_page:
        gr.HTML('<div class="loading-container"><div class="loading-text">⏳ Loading... Please Wait</div></div>')
    
    with gr.Row(visible=False) as normal_error:
        gr.HTML('<div class="error-message">😔 SORRY, SOME ERROR OCCURRED. PLEASE TRY AGAIN LATER</div>')
    
    # Footer Branding
    gr.HTML("""
        <div class="footer-brand">
            <p><strong>Developed by Darsh Tayal</strong></p>
            <p>📧 <a href="mailto:darshtayal8@gmail.com">darshtayal8@gmail.com</a></p>
            <p style="margin-top: 1rem; font-size: 0.85rem; opacity: 0.9;">© 2024 All Rights Reserved</p>
        </div>
    """)
    
    submit_button.click(setter, inputs=[youtube_link], outputs=[first_page, loading_page, chat_page, wrong_link_page, cc_not_enabled, normal_error, summary, vs])
    submit_answer.click(execute, inputs=[vs, ques], outputs=[answer, chat_page, normal_error])

if __name__ == "__main__":
    demo = gr.Interface(
        fn=generate_summary,
        inputs=gr.Textbox(label="YouTube Link"),
        outputs=gr.Textbox(label="Summary"),
        title="YouTube Summarizer"
    )
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 8080)))
