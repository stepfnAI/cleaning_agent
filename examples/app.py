import sys
import os
from sfn_blueprint import Task
from sfn_blueprint import SFNSessionManager
from sfn_blueprint import setup_logger
from sfn_blueprint import SFNFeatureCodeGeneratorAgent
from sfn_blueprint import SFNCodeExecutorAgent
from sfn_blueprint import SFNDataPostProcessor
from cleaning_agent.clean_suggestions_agent import SFNCleanSuggestionsAgent
from views.streamlit_views import StreamlitView
from cleaning_agent.utils.custom_data_loader import CustomDataLoader



def run_app():
    # Initialize view and session using sfn_blueprint
    view = StreamlitView(title = "Data Cleaning Advisor")
    session = SFNSessionManager()
    
    col1, col2 = view.create_columns([7, 1])
    with col1:
        view.display_title()
    with col2:
        if view.display_button("🔄 Reset", key="reset_button", use_container_width=True):
            session.clear()
            if 'uploaded_file' in view.session_state:
                del view.session_state['uploaded_file']
            view.rerun_script()

    # Setup logger
    logger, handler = setup_logger()
    logger.info('Starting Data Cleaning Advisor')



    # Step 1: Data Loading and Preview
    view.display_header("Step 1: Data Loading and Preview")
    view.display_markdown("---")
    
    if session.get('df') is None:
        # Only show file uploader if no data is loaded
        uploaded_file = view.file_uploader(
            "Choose a CSV or Excel file",
            key="uploaded_file",
            accepted_types=["csv", "xlsx", "json", "parquet"]
        )
        
        if uploaded_file is not None:
            with view.display_spinner('Loading data...'):
                data_loader = CustomDataLoader()
                load_task = Task("Load the uploaded file", data=uploaded_file)
                df = data_loader.execute_task(load_task)
                session.set('df', df)
                session.set('file_name', uploaded_file.name)  # Store filename in session
                logger.info(f"Data loaded successfully. Shape: {df.shape}")
                view.show_message(f"✅ Data loaded successfully. Shape: {df.shape}", "success")
                view.rerun_script()  # Force refresh to hide uploader
    else:
        # Display the name of currently loaded file
        view.show_message(f"📁 Current file: {session.get('file_name')}", "info")  # Use filename from session
        
        # Display data preview
        view.display_subheader("Data Preview")
        view.display_dataframe(session.get('df').head())
        view.display_header("Step 2: Generate cleaning suggestions and Apply Suggestions")



    if session.get('df') is not None:
        if session.get('suggestions') is None:
            with view.display_spinner('🤖 AI is generating cleaning suggestions...'):
                suggestion_generator = SFNCleanSuggestionsAgent()  
                suggestion_task = Task("Generate cleaning suggestions", 
                                        data=session.get('df'))
                suggestions = suggestion_generator.execute_task(suggestion_task)
                session.set('suggestions', suggestions)
                # Initialize other necessary session variables
                session.set('applied_suggestions', set())
                session.set('suggestion_history', [])
                session.set('current_suggestion_index', 0)
                logger.info(f"Generated {len(suggestions)} suggestions")

        # Step 3: Apply Suggestions
        if session.get('suggestions'):
            total_suggestions = len(session.get('suggestions'))
            applied_count = len(session.get('applied_suggestions', set()))


            # Initialize agents
            code_generator = SFNFeatureCodeGeneratorAgent()
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
                view.load_progress_bar(applied_count / total_suggestions)
                view.show_message(f"Progress: {applied_count} of {total_suggestions} suggestions processed")

                current_index = session.get('current_suggestion_index', 0)
                
                # Show all suggestions with their status
                view.display_subheader("Suggestions Overview")
                for idx, suggestion in enumerate(session.get('suggestions')):
                    if idx == current_index:
                        view.show_message(f"📍 Current: {suggestion}", "info")
                    elif idx in session.get('applied_suggestions', set()):
                        history_item = next((item for item in session.get('suggestion_history', []) 
                                        if item['content'] == suggestion), None)
                        if history_item and history_item['status'] == 'applied':
                            view.show_message(f"✅ Applied: {suggestion}", "success")
                        elif history_item and history_item['status'] == 'failed':
                            view.show_message(f"❌ Failed: {suggestion}", "error")
                        elif history_item and history_item['status'] == 'skipped':
                            view.show_message(f"⏭️ Skipped: {suggestion}", 'warning')

                if current_index < total_suggestions:
                    current_suggestion = session.get('suggestions')[current_index]
                    view.display_subheader("Current Suggestion")
                    view.show_message(f"```{current_suggestion}```", "info")

                    col1, col2, col3 = view.create_columns(3)
                    with col1:
                        if view.display_button("Apply This Suggestion"):
                            with view.display_spinner('Applying suggestion...'):
                                try:
                                    task = Task(
                                        description="Generate code",
                                        data={
                                            'suggestion': current_suggestion,
                                            'columns': session.get('df').columns.tolist(),
                                            'dtypes': session.get('df').dtypes.to_dict(),
                                            'sample_records': session.get('df').head().to_dict()
                                        }
                                    )
                                    code = code_generator.execute_task(task)
                                    exec_task = Task(description="Execute code", data=session.get('df'), code=code)
                                    session.set('df', code_executor.execute_task(exec_task))
                                    
                                    session.get('applied_suggestions').add(current_index)
                                    session.get('suggestion_history').append({
                                        'type': 'suggestion',
                                        'content': current_suggestion,
                                        'status': 'applied',
                                        'message': 'Successfully applied'
                                    })
                                    session.set('current_suggestion_index', current_index + 1)
                                    view.rerun_script()
                                except Exception as e:
                                    view.show_message(f"Failed to apply suggestion: {str(e)}", "error")
                                    session.get('applied_suggestions').add(current_index)
                                    session.get('suggestion_history').append({
                                        'type': 'suggestion',
                                        'content': current_suggestion,
                                        'status': 'failed',
                                        'message': str(e)
                                    })
                                    session.set('current_suggestion_index', current_index + 1)
                                    view.rerun_script()

                    with col2:
                        if view.display_button("Skip"):
                            session.get('applied_suggestions').add(current_index)
                            session.get('suggestion_history').append({
                                'type': 'suggestion',
                                'content': current_suggestion,
                                'status': 'skipped',
                                'message': 'Skipped by user'
                            })
                            session.set('current_suggestion_index', current_index + 1)
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
                
                for i, suggestion in enumerate(session.get('suggestions')):
                    if i not in session.get('applied_suggestions', set()):
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
                            
                            session.get('applied_suggestions').add(i)
                            session.get('suggestion_history').append({
                                'type': 'suggestion',
                                'content': suggestion,
                                'status': 'applied',
                                'message': 'Successfully applied'
                            })
                            view.show_message(f"✅ Applied: {suggestion}", "success")
                        except Exception as e:
                            session.get('applied_suggestions').add(i)
                            session.get('suggestion_history').append({
                                'type': 'suggestion',
                                'content': suggestion,
                                'status': 'failed',
                                'message': str(e)
                            })
                            view.show_message(f"❌ Failed: {suggestion} - Error: {str(e)}", "error")
                        
                        progress_bar.progress((len(session.get('applied_suggestions', set()))) / total_suggestions)
                    else:
                        history_item = next((item for item in session.get('suggestion_history', []) 
                                        if item['content'] == suggestion), None)
                        if history_item:
                            if history_item['status'] == 'applied':
                                view.show_message(f"✅ Applied: {suggestion}", "success")
                            elif history_item['status'] == 'failed':
                                view.show_message(f"❌ Failed: {suggestion}", "error")
                            elif history_item['status'] == 'skipped':
                                view.show_message(f"⏭️ Skipped: {suggestion}", 'warning')

                status_text.text("All suggestions processed")

            # Show summary if all suggestions are processed
            if len(session.get('applied_suggestions', set())) == total_suggestions:
                view.show_message("🎉 All suggestions have been processed!", "success")
                history = session.get('suggestion_history', [])
                applied = len([s for s in history if s['status'] == 'applied'])
                failed = len([s for s in history if s['status'] == 'failed'])
                skipped = len([s for s in history if s['status'] == 'skipped'])
                
                view.show_message(f"""
                ### Summary
                - ✅ Successfully applied: {applied}
                - ❌ Failed: {failed}
                - ⏭️ Skipped: {skipped}
                """)

                # Post-processing options
                view.display_header("Step 3: Post Processing")
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
