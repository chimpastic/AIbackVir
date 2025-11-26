import json
import docx
import boto3
from django.shortcuts import render
from django.http import StreamingHttpResponse  # <--- Key Import
from .forms import LLMSubmissionForm
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

# --- Helper: Extract Text from File Object ---
def extract_text(uploaded_file):
    """Detects file type and extracts string content."""
    filename = uploaded_file.name.lower()
    
    if filename.endswith('.docx'):
        doc = docx.Document(uploaded_file)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        # Also extract tables if critical, but keeping it simple for now
        return '\n'.join(full_text)
    else:
        # Assume text/md/json
        return uploaded_file.read().decode('utf-8')

# --- The Generator Function (The Brain) ---
def stream_strategy_generator(sample_drs, sample_strat, target_drs):
    """
    Yields HTML chunks to the browser as the LLM generates them.
    """
    
    # 1. Setup Bedrock
    chat = ChatBedrock(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_kwargs={"temperature": 0.1, "max_tokens": 4096}
    )

    # 2. Step A: Generate the Outline
    yield '<div class="status-update">Phase 1: Analyzing samples and creating Outline...</div>'
    
    outline_prompt = (
        f"Analyze this Sample Strategy:\n{sample_strat}\n\n"
        "Extract the high-level Section Headers used in this document. "
        "Return ONLY a JSON list of strings. Example: [\"1. Scope\", \"2. Risk Analysis\", \"3. Test Approach\"]"
    )
    
    try:
        response = chat.invoke([HumanMessage(content=outline_prompt)])
        # Parse JSON from LLM response (cleaning potential markdown code blocks)
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        sections = json.loads(clean_json)
        
        yield f'<div class="status-success">Outline Created: {len(sections)} sections identified.</div>'
        yield '<ul class="outline-list">'
        for sec in sections:
            yield f'<li>{sec}</li>'
        yield '</ul><hr>'

    except Exception as e:
        yield f'<div class="error-box">Error creating outline: {str(e)}</div>'
        return

    # 3. Step B: Loop through Sections
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
        
        # Store for final download
        full_document.append(f"## {section}\n{content}")
        
        # Stream to UI
        yield f'<div class="section-block"><h3>{section}</h3><div class="content">{content}</div></div>'

    # 4. Final Hidden Block for Download
    final_md = "\n\n".join(full_document)
    # We hide this raw data in a div so JavaScript can grab it for the download button
    yield f'<div id="final-raw-content" style="display:none;">{final_md}</div>'
    yield '<script>document.getElementById("download-btn").style.display = "inline-block";</script>'
    yield '<div class="status-success">Generation Complete!</div>'


# --- The View ---
def llm_analysis(request):
    if request.method == 'POST':
        form = LLMSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # Extract content immediately
            s_drs = extract_text(request.FILES['sample_drs'])
            s_strat = extract_text(request.FILES['sample_strategy'])
            t_drs = extract_text(request.FILES['target_drs'])

            # Return the Stream
            response = StreamingHttpResponse(
                stream_strategy_generator(s_drs, s_strat, t_drs)
            )
            # This header keeps the content type compatible with standard browser rendering
            # note: proper streaming often uses SSE (Server Sent Events), but for simple
            # Django apps, streaming HTML directly is a common workaround.
            return response
    else:
        form = LLMSubmissionForm()

    return render(request, 'docx_reader/llm_analysis.html', {'form': form})
