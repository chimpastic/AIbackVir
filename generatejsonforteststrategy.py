import json
import re
import boto3
import html
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

def stream_strategy_generator(sample_drs, sample_strat, target_drs):
    # 1. Setup Bedrock
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
            /* Dynamic headers in preview */
            .section-block h1 { color: #2c3e50; font-size: 1.8em; }
            .section-block h2 { color: #6200ea; font-size: 1.5em; }
            .section-block h3 { color: #009688; font-size: 1.2em; }
            .content { white-space: pre-wrap; }
            
            .btn-group { margin-top: 20px; display: flex; gap: 10px; }
            .btn { display: none; padding: 10px 20px; text-decoration: none; border-radius: 4px; cursor: pointer; border: none; font-size: 14px; }
            .btn-md { background: #6200ea; color: white; }
            .btn-json { background: #009688; color: white; }
            .btn:hover { opacity: 0.9; }
        </style>
    </head>
    <body>
        <h2>Generating Test Strategy...</h2>
        
        <div class="btn-group">
            <button id="download-md-btn" class="btn btn-md" onclick="downloadFile('md')">Download .MD</button>
            <button id="download-json-btn" class="btn btn-json" onclick="downloadFile('json')">Download .JSON</button>
        </div>

        <div id="stream-container">
    """

    # 2. Step A: Generate the Outline (UPDATED PROMPT)
    yield '<div class="status-update">Phase 1: Analyzing samples and creating Structured Outline...</div>'

    # Matches the prompt in your image
    outline_prompt = (
        f"Analyze this Sample Strategy:\n{sample_strat}\n\n"
        "Extract the Section Headers and Sub-headers used in this document to create a skeletal outline. "
        "Return ONLY a JSON list of objects. Each object must have two keys:\n"
        "1. 'title': The text of the header (remove numbering like 1, 1.1, etc.)\n"
        "2. 'level': An integer representing the hierarchy (1 for Main Header, 2 for Sub-header, 3 for sub-sub-header).\n\n"
        "Example Output format:\n"
        "[\n"
        "  {\"title\": \"Scope\", \"level\": 1},\n"
        "  {\"title\": \"In Scope\", \"level\": 2},\n"
        "  {\"title\": \"Out of Scope\", \"level\": 2},\n"
        "  {\"title\": \"Risk Analysis\", \"level\": 1}\n"
        "]"
    )

    try:
        response = chat.invoke([HumanMessage(content=outline_prompt)])
        raw_content = response.content.strip()
        match = re.search(r'\[.*\]', raw_content, re.DOTALL)

        if match:
            json_str = match.group(0)
            sections = json.loads(json_str) # List of dicts: [{'title': '...', 'level': 1}, ...]
        else:
            sections = json.loads(raw_content)

        yield f'<div class="status-success">Outline Created: {len(sections)} sections identified.</div>'
        
        # Display Outline with indentation based on level
        yield '<ul class="outline-list">'
        for sec in sections:
            indent = (sec.get('level', 1) - 1) * 20
            yield f'<li style="margin-left: {indent}px;">{sec["title"]}</li>'
        yield '</ul><hr>'

    except Exception as e:
        yield f'<div class="error-box">Error parsing outline: {str(e)}<br>Raw output: {raw_content}</div>'
        return

    # 3. Step B: Loop through Sections
    full_document = []
    json_data = [] 

    for section_obj in sections:
        # Extract title and level safely
        title = section_obj.get('title', 'Unknown Section')
        level = int(section_obj.get('level', 1))
        
        yield f'<div class="status-update">Generating: <strong>{title}</strong>...</div>'

        section_prompt = (
            f"You are writing a Test Strategy. \n"
            f"STYLE REFERENCE: {sample_strat}\n"
            f"INPUT REQUIREMENT: {target_drs}\n\n"
            f"TASK: Write ONLY the content for the section: '{title}'. "
            "Do not include the section header itself in the output, just the body text. "
            "Maintain the exact tone and formatting of the Style Reference."
        )

        chunk_resp = chat.invoke([HumanMessage(content=section_prompt)])
        content = chunk_resp.content

        # --- MD Generation: Create hashes (#, ##, ###) based on level ---
        header_hashes = '#' * level
        full_document.append(f"{header_hashes} {title}\n{content}")
        
        # --- JSON Generation: Store title, level, and content ---
        json_data.append({
            "title": title,
            "level": level,
            "content": content
        })

        # --- HTML Preview: Use standard h1-h6 tags ---
        yield f'<div class="section-block"><h{level}>{title}</h{level}><div class="content">{content}</div></div>'

    # 4. Final Hidden Block
    final_md = "\n\n".join(full_document)
    final_json_str = json.dumps(json_data, indent=4)

    yield f'<div id="final-md-content" style="display:none;">{final_md}</div>'
    yield f'<div id="final-json-content" style="display:none;">{final_json_str}</div>'
    
    yield """
    <script>
        document.getElementById("download-md-btn").style.display = "inline-block";
        document.getElementById("download-json-btn").style.display = "inline-block";
    </script>
    """
    
    yield '<div class="status-success">Generation Complete!</div>'

    yield """
        </div>
        <script>
            function downloadFile(type) {
                let content = "";
                let filename = "";
                let mimeType = "";

                if (type === 'md') {
                    content = document.getElementById('final-md-content').innerText;
                    filename = 'generated_strategy.md';
                    mimeType = 'text/markdown';
                } else if (type === 'json') {
                    content = document.getElementById('final-json-content').innerText;
                    filename = 'generated_strategy.json';
                    mimeType = 'application/json';
                }

                const blob = new Blob([content], { type: mimeType });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a); 
                window.URL.revokeObjectURL(url);
            }
            window.scrollTo(0, document.body.scrollHeight);
        </script>
    </body>
    </html>
    """
