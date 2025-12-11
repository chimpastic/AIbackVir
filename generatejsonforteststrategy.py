import json
import re
import boto3
import html  # Import html for safe escaping
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
            .section-block h3 { margin-top: 0; color: #6200ea; }
            .content { white-space: pre-wrap; }
            
            /* Button Styling */
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

    # 2. Step A: Generate the Outline
    yield '<div class="status-update">Phase 1: Analyzing samples and creating Outline...</div>'

    outline_prompt = (
        f"Analyze this Sample Strategy:\n{sample_strat}\n\n"
        "Extract the high-level Section Headers used in this document. "
        "Return ONLY a JSON list of strings. "
        "Do not write any introductory text. "
        "Example: [\"1. Scope\", \"2. Risk Analysis\", \"3. Test Approach\"]"
    )

    try:
        response = chat.invoke([HumanMessage(content=outline_prompt)])
        raw_content = response.content.strip()
        match = re.search(r'\[.*\]', raw_content, re.DOTALL)

        if match:
            json_str = match.group(0)
            sections = json.loads(json_str)
        else:
            sections = json.loads(raw_content)

        yield f'<div class="status-success">Outline Created: {len(sections)} sections identified.</div>'
        yield '<ul class="outline-list">'
        for sec in sections:
            yield f'<li>{sec}</li>'
        yield '</ul><hr>'

    except json.JSONDecodeError:
        yield f'<div class="error-box"><strong>Error Parsing JSON.</strong><br>The AI returned:<br><pre>{raw_content}</pre></div>'
        return
    except Exception as e:
        yield f'<div class="error-box">Error communicating with AI: {str(e)}</div>'
        return

    # 3. Step B: Loop through Sections
    full_document = []
    json_data = []  # <--- NEW: List to hold JSON structure

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

        # Append to MD list
        full_document.append(f"## {section}\n{content}")
        
        # Append to JSON list
        json_data.append({
            "section_title": section,
            "content": content
        })

        yield f'<div class="section-block"><h3>{section}</h3><div class="content">{content}</div></div>'

    # 4. Final Hidden Block
    final_md = "\n\n".join(full_document)
    final_json_str = json.dumps(json_data, indent=4) # <--- NEW: Serialize JSON

    # We use html.escape to safely put the JSON inside a HTML attribute or div if needed, 
    # but strictly putting it inside a hidden div text is usually enough.
    
    yield f'<div id="final-md-content" style="display:none;">{final_md}</div>'
    yield f'<div id="final-json-content" style="display:none;">{final_json_str}</div>'
    
    # Reveal Buttons
    yield """
    <script>
        document.getElementById("download-md-btn").style.display = "inline-block";
        document.getElementById("download-json-btn").style.display = "inline-block";
    </script>
    """
    
    yield '<div class="status-success">Generation Complete!</div>'

    # Updated Script to handle both types
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
                document.body.removeChild(a); // Clean up
                window.URL.revokeObjectURL(url);
            }
            window.scrollTo(0, document.body.scrollHeight);
        </script>
    </body>
    </html>
    """
