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
    # We add 'html-docx.js' and 'FileSaver.js' to handle the DOCX conversion in the browser
    yield """
    <html>
    <head>
        <script src="https://unpkg.com/html-docx-js/dist/html-docx.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js"></script>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; color: #333; }
            .status-update { background: #e3f2fd; padding: 12px; border-left: 5px solid #2196f3; margin: 10px 0; border-radius: 2px; }
            .status-success { background: #e8f5e9; padding: 12px; border-left: 5px solid #4caf50; margin: 10px 0; border-radius: 2px; }
            .error-box { background: #fff0f0; padding: 10px; border: 1px solid #ffcccc; color: #d32f2f; margin: 10px 0; }
            .outline-list { background: #f8f9fa; padding: 20px 40px; border-radius: 8px; border: 1px solid #e9ecef; }
            .section-block { border: 1px solid #ddd; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .section-block h3 { margin-top: 0; color: #6200ea; border-bottom: 1px solid #eee; padding-bottom: 10px; }
            .content { white-space: pre-wrap; line-height: 1.6; }
            
            #download-area { margin-top: 30px; padding: 20px; background: #f0f0f0; text-align: center; border-radius: 8px; display: none; }
            #download-btn { background: #6200ea; color: white; padding: 12px 25px; border: none; font-size: 16px; border-radius: 5px; cursor: pointer; transition: background 0.3s; }
            #download-btn:hover { background: #3700b3; }
        </style>
    </head>
    <body>
        <h2>Generating Test Strategy...</h2>
        
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
        
        # Robust Parsing: Find JSON array in the text
        match = re.search(r'\[.*\]', raw_content, re.DOTALL)
        if match:
            sections = json.loads(match.group(0))
        else:
            sections = json.loads(raw_content)

        yield f'<div class="status-success">Outline Created: {len(sections)} sections identified.</div>'
        yield '<ul class="outline-list">'
        for sec in sections:
            yield f'<li>{sec}</li>'
        yield '</ul><hr>'

    except Exception as e:
        yield f'<div class="error-box">Error creating outline: {str(e)}<br>Raw Output: {raw_content}</div>'
        return

    # 3. Step B: Loop through Sections
    # We maintain a list for the "Hidden" HTML that will become the DOCX
    full_html_document = []

    # Add a title for the DOCX
    full_html_document.append("<h1 style='text-align:center; color:#2E74B5;'>Test Strategy Document</h1><br>")

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

        # -- A. View Output (Screen) --
        yield f'<div class="section-block"><h3>{section}</h3><div class="content">{content}</div></div>'

        # -- B. Docx Output (Hidden) --
        # We replace newlines with <br> tags so they render in Word correctly
        # We wrap the content in <p> or <div> blocks
        formatted_content = content.replace('\n', '<br>')
        
        full_html_document.append(f"""
            <h2 style='color:#2E74B5; border-bottom:1px solid #ccc;'>{section}</h2>
            <div style='font-family:Calibri, sans-serif; font-size:11pt;'>
                {formatted_content}
            </div>
            <br>
        """)

    # 4. Final Hidden Block & Download Script
    final_html_str = "".join(full_html_document)
    
    # We output the final HTML into a hidden div
    yield f'<div id="final-docx-content" style="display:none;">{final_html_str}</div>'
    
    # Show the download button
    yield '<script>document.getElementById("download-area").style.display = "block";</script>'
    yield '<div class="status-success">Generation Complete! You can now download the file.</div>'

    yield """
        </div> <div id="download-area">
            <button id="download-btn" onclick="generateDocx()">Download Generated Strategy (.docx)</button>
        </div>

        <script>
            function generateDocx() {
                // 1. Get the HTML content
                var content = document.getElementById('final-docx-content').innerHTML;

                // 2. Wrap it in a standard HTML document structure with Word-specific namespaces
                var header = "<html xmlns:o='urn:schemas-microsoft-com:office:office' " +
                             "xmlns:w='urn:schemas-microsoft-com:office:word' " +
                             "xmlns='http://www.w3.org/TR/REC-html40'>" +
                             "<head><meta charset='utf-8'><title>Test Strategy</title></head><body>";
                var footer = "</body></html>";
                
                var sourceHTML = header + content + footer;

                // 3. Use html-docx-js to convert the HTML string into a Blob
                // Note: 'html-docx-js' (window.htmlDocx) must be loaded via the script tag
                var converted = htmlDocx.asBlob(sourceHTML);

                // 4. Use FileSaver to save the Blob to the user's computer
                saveAs(converted, 'Generated_Test_Strategy.docx');
            }
            
            // Auto-scroll to bottom
            window.scrollTo(0, document.body.scrollHeight);
        </script>
    </body>
    </html>
    """
