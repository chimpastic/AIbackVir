# ... imports remain the same
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

# Phase 1 View (process_docx) remains unchanged...

# --- Phase 2 View: LLM Analysis ---
def llm_analysis(request):
    llm_response = ""
    error_message = ""

    if request.method == 'POST':
        form = LLMSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 1. Read all three files
                # Note: We assume these are text/markdown files. 
                # If they are raw .docx, you would need to run the extraction logic on them first.
                sample_drs_content = request.FILES['sample_drs'].read().decode('utf-8')
                sample_strat_content = request.FILES['sample_strategy'].read().decode('utf-8')
                target_drs_content = request.FILES['target_drs'].read().decode('utf-8')

                # 2. Define the Persona
                system_prompt = (
                    "You are an expert QA Test Architect. Your goal is to draft a Test Strategy Document. "
                    "Analyze the provided examples to understand the section headers, mapping logic, and tone. "
                    "Generate the output for the new DRS following the EXACT structure of the examples provided."
                )

                # 3. Construct the Few-Shot Prompt
                # We combine the inputs to simulate the learning process
                combined_prompt = (
                    f"USER:\nHere is Example #1 DRS:\n{sample_drs_content}\n\n"
                    f"ASSISTANT:\nHere is Example #1 Strategy:\n{sample_strat_content}\n\n"
                    f"USER:\nHere is the New DRS. Generate the Test Strategy document based on the style above:\n{target_drs_content}"
                )

                # 4. Initialize Bedrock
                chat = ChatBedrock(
                    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                    model_kwargs={"temperature": 0.2, "max_tokens": 4096} 
                    # lowered temperature to 0.2 to ensure it sticks strictly to the example format
                )

                # 5. Invoke LLM
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=combined_prompt)
                ]

                response = chat.invoke(messages)
                llm_response = response.content

            except UnicodeDecodeError:
                error_message = "Could not read one of the files. Please ensure all uploads are Text or Markdown files."
            except Exception as e:
                error_message = f"Error communicating with Bedrock: {str(e)}"
    else:
        form = LLMSubmissionForm()

    return render(request, 'docx_reader/llm_analysis.html', {
        'form': form,
        'llm_response': llm_response,
        'error_message': error_message
    })
