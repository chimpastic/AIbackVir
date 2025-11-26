import json
import re  # <--- NEW: Import Regex
import docx
import boto3
from django.http import StreamingHttpResponse
from django.shortcuts import render
from .forms import LLMSubmissionForm
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

# --- Helper: Extract Text ---
def extract_text(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith('.docx'):
        doc = docx.Document(uploaded_file)
        full_text = [para.text for para in doc.paragraphs]
        return '\n'.join(full_text)
    else:
        return uploaded_file.read().decode('utf-8')

# --- The Generator Function ---
def stream_strategy_generator(sample_drs, sample_strat, target_drs):
    # 1. Setup Bedrock (SSL Verify False for Corporate Proxy)
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
        verify=False 
    )

    chat = ChatBedrock(
        client=bedrock_client,
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_kwargs={"temperature": 0.1, "max_tokens": 4096}
    )

    # --- HTML Header ---
    yield """
    <html>
    <head>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
            .status-update { background: #e3f2fd; padding: 10px; border-left: 4px solid #2196f3; margin: 10px 0; }
            .status-success { background: #e8f5e9; padding: 10px; border-left: 4px solid #4caf50; margin: 10px 0; }
            .error-box { background: #fff0f0; padding: 10px; border: 1px solid #ffcccc; color: #d32f2f; margin: 10px 0; overflow-x: auto; }
            .outline-list { background: #f5f5f5; padding: 15px 30px; border-radius: 4px; }
            .section-block { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 4px; }
            .section-block h3 { margin-top: 0; color: #6200ea; }
            .content { white-space: pre-wrap; }
            #download-btn { display: none; background: #6200ea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 20px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h2>Generating Test Strategy...</h2>
        <button id="download-btn" onclick="downloadFile()">Download Full Strategy (.md)</button>
        <div id="stream-container">
    """
    
    # 2. Step A: Generate the Outline
    yield '<div class="status-update">Phase 1: Analyzing samples and creating Outline...</div>'
    
    outline_prompt = (
        f"Analyze this Sample Strategy:\n{sample_strat}\n\n"
        "Extract the high-level Section Headers used in this document. "
        "Return ONLY a JSON list of strings. "
        "Do not write any introductory text. "
        "Example: [\"1. Scope\", \"2. Risk Analysis\", \"3. Test Approach\"]"
    )
    
    # --- UPDATED PARSING LOGIC ---
    try:
        response = chat.invoke([HumanMessage(content=outline_prompt)])
        raw_content = response.content.strip()

        # Regex: Find the first '[' and the last ']' and everything in between
        match = re.search(r'\[.*\]', raw_content, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            sections = json.loads(json_str)
        else:
            # If regex fails, try loading the raw content directly
            sections = json.loads(raw_content)
        
        yield f'<div class="status-success">Outline Created: {len(sections)} sections identified.</div>'
        yield '<ul class="outline-list">'
        for sec in sections:
            yield f'<li>{sec}</li>'
        yield '</ul><hr>'

    except json.JSONDecodeError:
        # If it still fails, show the user EXACTLY what the AI returned so we can debug
        yield f'<div class="error-box"><strong>Error Parsing JSON.</strong><br>The AI returned:<br><pre>{raw_content}</pre></div>'
        return
    except Exception as e:
        yield f'<div class="error-box">Error communicating with AI: {str(e)}</div>'
        return

    # 3. Step B: Loop through Sections (Unchanged)
    full_document = []
    
    for section in sections:
        yield f'<div class="status-update">Generating Section: <strong>{section}</strong>...</div>'
        
        section_prompt = (
            f"You are writing a Test Strategy. \n"
            f"STYLE REFERENCE: {sample_strat}\n"
            f"INPUT REQUIREMENT: {target_drs}\n\n"
            f"TASK: Write ONLY the content for the section: '{section}'. "
            "Do not include the section header itself in the output, just the body text. "
            "Maintain the exact tone and formatting of the Style Reference."
        )
        
        chunk_resp = chat.invoke([HumanMessage(content=section_prompt)])
        content = chunk_resp.content
        
        full_document.append(f"## {section}\n{content}")
        yield f'<div class="section-block"><h3>{section}</h3><div class="content">{content}</div></div>'

    # 4. Final Hidden Block
    final_md = "\n\n".join(full_document)
    # Escape backslashes for JS safety
    safe_md = final_md.replace('`', '\`').replace('\\', '\\\\')
    
    yield f'<div id="final-raw-content" style="display:none;">{final_md}</div>'
    yield '<script>document.getElementById("download-btn").style.display = "inline-block";</script>'
    yield '<div class="status-success">Generation Complete!</div>'
    
    yield """
        </div>
        <script>
            function downloadFile() {
                const content = document.getElementById('final-raw-content').innerText;
                const blob = new Blob([content], { type: 'text/markdown' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'generated_strategy.md';
                document.body.appendChild(a);
                a.click();
            }
            window.scrollTo(0, document.body.scrollHeight);
        </script>
    </body>
    </html>
    """

# --- View (Unchanged) ---
def llm_analysis(request):
    if request.method == 'POST':
        form = LLMSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            s_drs = extract_text(request.FILES['sample_drs'])
            s_strat = extract_text(request.FILES['sample_strategy'])
            t_drs = extract_text(request.FILES['target_drs'])

            return StreamingHttpResponse(
                stream_strategy_generator(s_drs, s_strat, t_drs)
            )
    else:
        form = LLMSubmissionForm()

    return render(request, 'docx_reader/llm_analysis.html', {'form': form})
