import io
import base64
# ... existing imports (json, re, docx, boto3, etc)


def generate_docx_base64(content_text):
    # 1. Create the Document in memory
    doc = docx.Document()
    doc.add_heading('Generated Test Strategy', 0)

    # Simple parsing to formatting
    for line in content_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        if line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=1)
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=2)
        else:
            doc.add_paragraph(line)



def stream_strategy_generator(sample_drs, sample_strat, target_drs):
    # ... [Keep Setup, Headers, and Outline logic exactly the same] ...

    # ... [Keep the "for section in sections" loop exactly the same] ...

    # --- FINAL BLOCK ---
    
    # 1. Combine all text
    final_md_text = "\n\n".join(full_document)

    yield '<div class="status-update">Finalizing document format...</div>'

    # 2. Generate the Base64 DOCX string (Happens on server)
    try:
        b64_string = generate_docx_base64(final_md_text)
        
        # 3. Create the Data URI
        # This tells the browser: "The file data is right here in this string"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        data_uri = f"data:{mime_type};base64,{b64_string}"

        yield '<div class="status-success">Generation Complete!</div>'

        # 4. Inject the Download Button
        # We set the 'href' to the data URI and 'download' to the filename
        yield f"""
        <script>
            var btn = document.getElementById('download-btn');
            btn.href = "{data_uri}";
            btn.download = "Generated_Strategy.docx";
            btn.onclick = null; // Remove the old onclick if it existed
            btn.style.display = "inline-block";
            btn.innerText = "Download DOCX Now";
            
            window.scrollTo(0, document.body.scrollHeight);
        </script>
        """
        
    except Exception as e:
        yield f'<div class="error-box">Error creating DOCX: {str(e)}</div>'

    yield "</body></html>"



# New
yield """
<a id="download-btn" style="display:none; background: #6200ea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 20px; cursor: pointer;">
    Processing file...
</a>
"""

    # 2. Save to BytesIO buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # 3. Encode to Base64
    # We read the bytes, encode them to base64, then decode to a UTF-8 string
    encoded_file = base64.b64encode(buffer.read()).decode('utf-8')
    
    return encoded_file



