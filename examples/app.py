import sys
import os
from sfn_blueprint import Task
from cleaning_agent.views.streamlit_view import StreamlitCleaningAppView
from sfn_blueprint import SFNSessionManager
from sfn_blueprint import SFNDataLoader
from sfn_blueprint import setup_logger
from sfn_blueprint import SFNFeatureCodeGeneratorAgent
from sfn_blueprint import SFNValidateAndRetryAgent
from sfn_blueprint import SFNCodeExecutorAgent
from sfn_blueprint import SFNDataPostProcessor
from sfn_blueprint import RetryLimitExceededError
from cleaning_agent.agents.clean_suggestions_agent import SFNCleanSuggestionsAgent
from cleaning_agent.config.model_config import DEFAULT_LLM_PROVIDER



def run_app():
    # Initialize view and session using custom view class
    view = StreamlitCleaningAppView(title = "Data Cleaning Advisor")
    session = SFNSessionManager()
    
    col1, col2 = view.create_columns([7, 1])
    with col1:
        view.display_title()
    with col2:
        if view.display_button("🔄", key="reset_button"):
            session.clear()
            view.rerun_script()

    # Setup logger
    logger, handler = setup_logger()
    logger.info('Starting Data Cleaning Advisor')



    # Step 1: Data Loading and Preview
    view.display_header("Step 1: Data Loading and Preview")
    view.display_markdown("---")
    
    uploaded_file = view.file_uploader("Choose a CSV or Excel file", accepted_types=["csv", "xlsx", "json", "parquet"])

    if uploaded_file is not None:
        if session.get('df') is None:
            with view.display_spinner('Loading data...'):

                # Save the uploaded file temporarily and get its path
                file_path = view.save_uploaded_file(uploaded_file)
                logger.info(f'started loading saved file:{file_path}')
                load_task = Task("Load the uploaded file", data=uploaded_file, path=file_path)
                data_loader = SFNDataLoader()
                df = data_loader.execute_task(load_task)
                session.set('df', df)
                logger.info(f"Data loaded successfully. Shape: {df.shape}")
                view.show_message(f"✅ Data loaded successfully. Shape: {df.shape}", "success")
                
                # Display data preview
                view.display_subheader("Data Preview")
                view.display_dataframe(df.head())
                view.display_markdown("---")


    if session.get('df') is not None:
        # Step 2: Generate Cleaning Suggestions
        if session.get('cleaning_suggestions') is None:
            view.display_header("Step 2: Generate Cleaning Suggestions")
            view.display_markdown("---")

            with view.display_spinner('🤖 AI is analyzing your data for cleaning suggestions...'):
                cleaning_agent = SFNCleanSuggestionsAgent(llm_provider=DEFAULT_LLM_PROVIDER)
                
                # Create the main task
                cleaning_task = Task("Generate cleaning suggestions", 
                                   data=session.get('df'))
                
                # Create validation task with same data
                validation_task = Task("Validate cleaning suggestions",
                                     data=session.get('df'))
                
                validate_and_retry_agent = SFNValidateAndRetryAgent(
                    llm_provider=DEFAULT_LLM_PROVIDER,
                    for_agent='clean_suggestions_generator'
                )
                
                try:
                    cleaning_suggestions, validation_message, is_valid = validate_and_retry_agent.complete(
                        agent_to_validate=cleaning_agent,
                        task=cleaning_task,
                        validation_task=validation_task,
                        method_name='execute_task',
                        get_validation_params='get_validation_params',
                        max_retries=2,
                        retry_delay=3.0
                    )
                    
                    # Format validation message right after getting it
                    formatted_message = validation_message.replace("FALSE\n", "").strip() if validation_message else ""
                    
                    if not is_valid:
                        view.show_message("❌ No valid AI suggestions could be generated.", "error")
                        view.show_message("Reason for invalidation:", "info")
                        view.show_message(formatted_message, "warning")
                    
                    logger.info('Cleaning suggestion generation complete')
                    session.set('cleaning_suggestions', cleaning_suggestions)
                    session.set('suggestions_valid', is_valid)
                    if is_valid:
                        session.set('applied_cleaning_suggestions', [])
                        session.set('suggestion_history', [])
                        session.set('current_cleaning_suggestion_index', 0)
                    else:
                        session.set('manual_suggestions', [])
                        session.set('validation_explanation', formatted_message)
                    logger.info(f"Generated {len(cleaning_suggestions)} cleaning suggestions")
                except RetryLimitExceededError as e:
                    view.show_message(f"❌ Error: {str(e)}", "error")
                    logger.error(str(e))
        else:
            # Show Step 2 status
            view.display_header("Step 2: Generate Cleaning Suggestions")
            view.display_markdown("---")
            if session.get('suggestions_valid'):
                view.show_message("✅ AI suggestions were validated and ready for application.", "success")
            else:
                view.show_message("❌ No valid AI suggestions could be generated.", "error")
                view.show_message("Reason for invalidation:", "info")
                view.show_message(session.get('validation_explanation', ''), "warning")
            view.display_markdown("---")

        # Step 3: Handle Suggestions
        if session.get('cleaning_suggestions'):
            view.display_header("Step 3: Handle Suggestions")
            view.display_markdown("---")

            # If suggestions are not valid, show manual input option
            if not session.get('suggestions_valid'):
                view.show_message("✍️ Add your own data cleaning instructions:", "info")
                
                # Show text input for manual suggestion
                manual_suggestion = view.text_input("Enter your cleaning instruction:", 
                                                  key="manual_suggestion_input",
                                                  help="Example: Convert column 'date' to datetime format",
                                                  value=session.get('current_input', ''))

                col1, col2, col3 = view.create_columns(3)
                with col1:
                    if view.display_button("Add Suggestion"):
                        if manual_suggestion:
                            manual_suggestions = session.get('manual_suggestions', [])
                            manual_suggestions.append(manual_suggestion)
                            session.set('manual_suggestions', manual_suggestions)
                            # Reset the input by clearing the session value
                            session.set('current_input', '')
                            view.rerun_script()
                
                with col2:
                    if view.display_button("Finish & Apply All"):
                        if session.get('manual_suggestions'):
                            session.set('cleaning_suggestions', session.get('manual_suggestions'))
                            session.set('suggestions_valid', True)
                            session.set('applied_cleaning_suggestions', [])
                            session.set('suggestion_history', [])
                            session.set('current_cleaning_suggestion_index', 0)
                            session.set('application_mode', 'batch')
                            # Reset the input when finishing
                            session.set('current_input', '')
                            view.rerun_script()
                
                with col3:
                    if view.display_button("Skip Cleaning"):
                        view.show_message("🔄 Operation Summary", "info")
                        view.show_message("No cleaning operations were applied to the dataset.", "info")
                        view.show_message("\nInitial AI Suggestions (Invalid):", "error")
                        for idx, suggestion in enumerate(session.get('cleaning_suggestions', [])):
                            view.show_message(f"{idx + 1}. {suggestion}", "error")
                        view.show_message("\nValidation Failed Because:", "error")
                        view.show_message(session.get('validation_explanation', "No explanation available"), "error")
                        if view.display_button("Confirm & Exit"):
                            # Reset the input when exiting
                            session.set('current_input', '')
                            session.clear()
                            view.rerun_script()
                
                # Show current manual suggestions
                if session.get('manual_suggestions'):
                    view.display_subheader("📋 Added Instructions:")
                    for idx, suggestion in enumerate(session.get('manual_suggestions')):
                        view.show_message(f"{idx + 1}. {suggestion}", "info")
           
            # If suggestions are valid (either AI-generated or manual), show application options
            else:
                total_suggestions = len(session.get('cleaning_suggestions'))
                applied_count = len(session.get('applied_cleaning_suggestions', set()))

                # Initialize agents
                code_generator = SFNFeatureCodeGeneratorAgent(llm_provider=DEFAULT_LLM_PROVIDER)
                code_executor = SFNCodeExecutorAgent()  

                # Application mode selection
                if session.get('application_mode') is None:
                    view.show_message(f"🎯 We have generated **{total_suggestions}** suggestions for your dataset.", "info")
                    col1, col2 = view.create_columns(2)
                    with col1:
                        if view.display_button("Review One by One"):
                            session.set('application_mode', 'individual')
                            view.rerun_script()
                    with col2:
                        if view.display_button("Apply All at Once"):
                            session.set('application_mode', 'batch')
                            view.rerun_script()

                # Individual Review Mode
                elif session.get('application_mode') == 'individual':
                    # Show current progress
                    progress = len(session.get('applied_cleaning_suggestions', [])) / total_suggestions
                    view.load_progress_bar(progress)
                    view.show_message(f"Progress: {applied_count} of {total_suggestions} suggestions processed")

                    current_index = session.get('current_cleaning_suggestion_index', 0)
                    logger.info(f"Current suggestion index: {current_index}")
                    
                    # Show all suggestions with their status
                    view.display_subheader("Suggestions Overview")
                    for idx, suggestion in enumerate(session.get('cleaning_suggestions')):
                        if idx == current_index:
                            view.show_message(f"📍 Current: {suggestion}", "info")
                        elif idx in session.get('applied_cleaning_suggestions', []):
                            history_item = next((item for item in session.get('suggestion_history', []) 
                                            if item['content'] == suggestion), None)
                            if history_item and history_item['status'] == 'applied':
                                view.show_message(f"✅ Applied: {suggestion}", "success")
                            elif history_item and history_item['status'] == 'failed':
                                view.show_message(f" Failed: {suggestion}", "error")
                            elif history_item and history_item['status'] == 'skipped':
                                view.show_message(f"⏭ Skipped: {suggestion}", 'warning')

                    if current_index < total_suggestions:
                        current_suggestion = session.get('cleaning_suggestions')[current_index]
                        view.display_subheader("Current Suggestion")
                        view.show_message(f"```{current_suggestion}```", "info")

                        col1, col2, col3 = view.create_columns(3)
                        with col1:
                            if view.display_button("Apply This Suggestion"):
                                with view.display_spinner('Applying suggestion...'):
                                    try:
                                        logger.info(f"Generating code for suggestion: {current_suggestion}")
                                        task = Task(
                                            description="Generate code",
                                            data={
                                                'suggestion': current_suggestion,
                                                'columns': session.get('df').columns.tolist(),
                                                'dtypes': session.get('df').dtypes.to_dict(),
                                                'sample_records': session.get('df').head().to_dict()
                                            }
                                        )
                                        logger.info("Calling code generator...")
                                        code = code_generator.execute_task(task)
                                        logger.info(f"Generated code: {code}")
                                        
                                        if not code:
                                            raise ValueError("No code was generated")
                                        
                                        logger.info("Creating execution task...")
                                        exec_task = Task(description="Execute code", data=session.get('df'), code=code)
                                        logger.info("Executing code...")
                                        session.set('df', code_executor.execute_task(exec_task))
                                        logger.info("Code execution completed")
                                        
                                        # Get current applied suggestions list
                                        applied_suggestions = session.get('applied_cleaning_suggestions', [])
                                        if current_index not in applied_suggestions:
                                            applied_suggestions.append(current_index)
                                        session.set('applied_cleaning_suggestions', applied_suggestions)

                                        suggestion_history = session.get('suggestion_history', [])
                                        suggestion_history.append({
                                            'type': 'suggestion',
                                            'content': current_suggestion,
                                            'status': 'applied',
                                            'message': 'Successfully applied'
                                        })
                                        session.set('suggestion_history', suggestion_history)
                                        session.set('current_cleaning_suggestion_index', current_index + 1)
                                        logger.info("Suggestion applied successfully, rerunning script...")
                                        view.rerun_script()
                                    except Exception as e:
                                        logger.error(f"Error applying suggestion: {str(e)}")
                                        logger.exception("Full traceback:")
                                        view.show_message(f"Failed to apply suggestion: {str(e)}", "error")
                                        # Get current applied suggestions list
                                        applied_suggestions = session.get('applied_cleaning_suggestions', [])
                                        if current_index not in applied_suggestions:
                                            applied_suggestions.append(current_index)
                                        session.set('applied_cleaning_suggestions', applied_suggestions)
                                        suggestion_history = session.get('suggestion_history', [])
                                        suggestion_history.append({
                                            'type': 'suggestion',
                                            'content': current_suggestion,
                                            'status': 'failed',
                                            'message': str(e)
                                        })
                                        session.set('suggestion_history', suggestion_history)
                                        session.set('current_cleaning_suggestion_index', current_index + 1)
                                        logger.info("Suggestion marked as failed, rerunning script...")
                                        view.rerun_script()

                        with col2:
                            if view.display_button("Skip"):
                                # Get current applied suggestions list
                                applied_suggestions = session.get('applied_cleaning_suggestions', [])
                                if current_index not in applied_suggestions:
                                    applied_suggestions.append(current_index)
                                session.set('applied_cleaning_suggestions', applied_suggestions)
                                suggestion_history = session.get('suggestion_history', [])
                                suggestion_history.append({
                                    'type': 'suggestion',
                                    'content': current_suggestion,
                                    'status': 'skipped',
                                    'message': 'Skipped by user'
                                })
                                session.set('suggestion_history', suggestion_history)
                                session.set('current_cleaning_suggestion_index', current_index + 1)
                                view.rerun_script()

                        with col3:
                            remaining = total_suggestions - (applied_count + 1)
                            if remaining > 0 and view.display_button(f"Apply Remaining ({remaining})"):
                                session.set('application_mode', 'batch')
                                view.rerun_script()

                # Batch Mode
                elif session.get('application_mode') == 'batch':
                    # Create progress tracking elements
                    progress_bar, status_text = view.create_progress_container()

                    
                    # Display all suggestions with processing status
                    view.display_subheader("Processing Suggestions")
                    if not session.get('proceed_to_post_processing'):
                        for i, suggestion in enumerate(session.get('cleaning_suggestions')):
                            if i not in session.get('applied_cleaning_suggestions', set()):
                                progress_value = (i + 1) / total_suggestions
                                view.update_progress(progress_bar, progress_value)
                                view.update_text(status_text, f"Applying suggestion {i + 1}/{total_suggestions}")
                                try:
                                    task = Task(
                                        description="Generate code",
                                        data={
                                            'suggestion': suggestion,
                                            'columns': session.get('df').columns.tolist(),
                                            'dtypes': session.get('df').dtypes.to_dict(),
                                            'sample_records': session.get('df').head().to_dict()
                                        }
                                    )
                                    code = code_generator.execute_task(task)
                                    exec_task = Task(description="Execute code", data=session.get('df'), code=code)
                                    session.set('df', code_executor.execute_task(exec_task))
                                    
                                    # Get current applied suggestions list
                                    applied_suggestions = session.get('applied_cleaning_suggestions', [])
                                    if i not in applied_suggestions:
                                        applied_suggestions.append(i)
                                    session.set('applied_cleaning_suggestions', applied_suggestions)
                                    suggestion_history = session.get('suggestion_history', [])
                                    suggestion_history.append({
                                        'type': 'suggestion',
                                        'content': suggestion,
                                        'status': 'applied',
                                        'message': 'Successfully applied'
                                    })
                                    session.set('suggestion_history', suggestion_history)
                                    view.show_message(f"✅ Applied: {suggestion}", "success")
                                except Exception as e:
                                    # Get current applied suggestions list
                                    applied_suggestions = session.get('applied_cleaning_suggestions', [])
                                    if i not in applied_suggestions:
                                        applied_suggestions.append(i)
                                    session.set('applied_cleaning_suggestions', applied_suggestions)
                                    suggestion_history = session.get('suggestion_history', [])
                                    suggestion_history.append({
                                        'type': 'suggestion',
                                        'content': suggestion,
                                        'status': 'failed',
                                        'message': str(e)
                                    })
                                    session.set('suggestion_history', suggestion_history)
                                    view.show_message(f"❌ Failed: {suggestion} - Error: {str(e)}", "error")
                                
                                progress_bar.progress((len(session.get('applied_cleaning_suggestions', set()))) / total_suggestions)
                            else:
                                history_item = next((item for item in session.get('suggestion_history', []) 
                                                if item['content'] == suggestion), None)
                                if history_item:
                                    if history_item['status'] == 'applied':
                                        view.show_message(f"✅ Applied: {suggestion}", "success")
                                    elif history_item['status'] == 'failed':
                                        view.show_message(f"❌ Failed: {suggestion}", "error")
                                    elif history_item['status'] == 'skipped':
                                        view.show_message(f" Skipped: {suggestion}", 'warning')

                        status_text.text("All AI suggestions processed")

                # Show summary if all suggestions are processed
                if len(session.get('applied_cleaning_suggestions', set())) == total_suggestions:
                    if not session.get('proceed_to_post_processing'):  # Only show if not proceeded to post processing
                        view.display_markdown("---")
                        view.show_message("Would you like to add any custom cleaning instructions?", "info")
                        
                        # Show custom instruction input
                        manual_suggestion = view.text_input("Enter your cleaning instruction:", 
                                                          key="custom_instruction",
                                                          help="Example: Convert column 'date' to datetime format",
                                                          value="")
                        
                        col1, col2 = view.create_columns(2)
                        with col1:
                            if view.display_button("Add Suggestion") and manual_suggestion:
                                manual_suggestions = session.get('manual_suggestions', [])
                                manual_suggestions.append(manual_suggestion)
                                session.set('manual_suggestions', manual_suggestions)
                                # Initialize agents for applying the suggestion
                                code_generator = SFNFeatureCodeGeneratorAgent(llm_provider=DEFAULT_LLM_PROVIDER)
                                code_executor = SFNCodeExecutorAgent()
                                
                                # Generate and execute code for the suggestion
                                try:
                                    task = Task(
                                        description="Generate code",
                                        data={
                                            'suggestion': manual_suggestion,
                                            'columns': session.get('df').columns.tolist(),
                                            'dtypes': session.get('df').dtypes.to_dict(),
                                            'sample_records': session.get('df').head().to_dict()
                                        }
                                    )
                                    generated_code = code_generator.execute_task(task)
                                    
                                    if generated_code:
                                        execution_task = Task(
                                            description="Execute code", 
                                            data=session.get('df'), 
                                            code=generated_code
                                        )
                                        updated_df = code_executor.execute_task(execution_task)
                                        if updated_df is not None:
                                            session.set('df', updated_df)
                                except Exception as e:
                                    view.show_message(f"❌ Failed to apply suggestion: {str(e)}", "error")
                                    suggestion_history.append({
                                        'type': 'custom',
                                        'content': manual_suggestion,
                                        'status': 'failed',
                                        'message': str(e)
                                    })
                                    session.set('suggestion_history', suggestion_history)
                                    view.rerun_script()
                                    return

                                # Add to suggestion history
                                suggestion_history = session.get('suggestion_history', [])
                                suggestion_history.append({
                                    'type': 'custom',
                                    'content': manual_suggestion,
                                    'status': 'applied',
                                    'message': 'Successfully added'
                                })
                                session.set('suggestion_history', suggestion_history)
                                view.rerun_script()
                        
                        with col2:
                            if view.display_button("Proceed to Post Processing"):
                                session.set('proceed_to_post_processing', True)
                                view.rerun_script()

                        # Show all applied custom suggestions
                        if session.get('suggestion_history'):
                            view.display_markdown("---")
                            view.display_subheader("Applied Custom Instructions:")
                            for suggestion in session.get('suggestion_history'):
                                if suggestion['type'] == 'custom' and suggestion['status'] == 'applied':
                                    view.show_message(f"✅ Applied: {suggestion['content']}", "success")
                                elif suggestion['type'] == 'custom' and suggestion['status'] == 'failed':
                                    view.show_message(f"❌ Failed: {suggestion['content']}", "error")

                # Proceed to post processing if selected
                if session.get('proceed_to_post_processing'):
                    # Show AI suggestions first
                    for suggestion in session.get('suggestion_history', []):
                        if suggestion['type'] == 'suggestion' and suggestion['status'] == 'applied':
                            view.show_message(f"✅ AI Applied: {suggestion['content']}", "success")

                    # Then show custom suggestions
                    for suggestion in session.get('suggestion_history', []):
                        if suggestion['type'] == 'custom' and suggestion['status'] == 'applied':
                            view.show_message(f"✅ Custom Applied: {suggestion['content']}", "success")

                    history = session.get('suggestion_history', [])
                    ai_applied = len([s for s in history 
                                    if s['status'] == 'applied' 
                                    and (s['type'] == 'suggestion' or 'type' not in s)])  # Include legacy entries without type
                    custom_applied = len([s for s in history if s['status'] == 'applied' and s['type'] == 'custom'])
                    failed = len([s for s in history if s['status'] == 'failed'])
                    skipped = len([s for s in history if s['status'] == 'skipped'])
                    
                    view.show_message(f"""
                    ### Summary
                    - ✅ AI Suggestions Applied: {ai_applied}
                    - ✅ Custom Instructions Applied: {custom_applied}
                    - ❌ Failed: {failed}
                    - ⏭️ Skipped: {skipped}
                    """)
                    view.show_message("🎉 All cleaning operations completed!", "success")
                    # Post-processing options
                    view.display_header("Step 4: Post Processing")
                    view.display_markdown("---")
                    operation_type = view.radio_select(
                        "Choose an operation:",
                        ["View Data", "Download Data", "Finish"]
                    )

                    if operation_type == "View Data":
                        view.display_dataframe(session.get('df'))
                    
                    elif operation_type == "Download Data":
                        post_processor = SFNDataPostProcessor(session.get('df'))
                        csv_data = post_processor.download_data('csv')
                        view.create_download_button(
                            label="Download CSV",
                            data=csv_data,
                            file_name="processed_data.csv",
                            mime_type="text/csv"
                        )
                    
                    elif operation_type == "Finish":
                        if view.display_button("Confirm Finish"):
                            view.show_message("Thank you for using the Feature Suggestion App!", "success")
                            session.clear()


if __name__ == "__main__":
    run_app()
