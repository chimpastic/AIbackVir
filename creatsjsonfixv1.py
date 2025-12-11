    # 2. Step A: Generate the Outline
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

    # --- FIX STARTS HERE ---
    raw_content = "" # Initialize variable here so it exists even if chat.invoke fails

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
        
        # Display Outline with indentation based on level
        yield '<ul class="outline-list">'
        for sec in sections:
            indent = (sec.get('level', 1) - 1) * 20
            yield f'<li style="margin-left: {indent}px;">{sec["title"]}</li>'
        yield '</ul><hr>'

    except Exception as e:
        # Now this will work because raw_content is defined as empty string at minimum
        yield f'<div class="error-box">Error parsing outline: {str(e)}<br>Raw output: {raw_content}</div>'
        return
    # --- FIX ENDS HERE ---
