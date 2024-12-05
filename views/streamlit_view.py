import streamlit as st
from sfn_blueprint import SFNStreamlitView

class StreamlitCleaningAppView(SFNStreamlitView):
    def __init__(self, title="Data Cleaning Advisor"):
        super().__init__(title=title)

    def text_input(self, label: str, key: str = None, help: str = None, value: str = "") -> str:
        """
        Display a text input widget.
        
        Args:
            label: Label for the text input
            key: Unique key for the widget
            help: Help text to display
            value: Default value for the input
            
        Returns:
            str: The text entered by the user
        """
        return st.text_input(
            label=label,
            key=key,
            help=help,
            value=value
        )

    def text_area(self, label: str, key: str = None, help: str = None, value: str = "", height: int = None) -> str:
        """
        Display a text area widget for multiline input.
        
        Args:
            label: Label for the text area
            key: Unique key for the widget
            help: Help text to display
            value: Default value for the input
            height: Height of the text area in pixels
            
        Returns:
            str: The text entered by the user
        """
        return st.text_area(
            label=label,
            key=key,
            help=help,
            value=value,
            height=height
        )

    def code_editor(self, label: str, code: str = "", language: str = "python", key: str = None) -> str:
        """
        Display a code editor widget.
        
        Args:
            label: Label for the code editor
            code: Default code to display
            language: Programming language for syntax highlighting
            key: Unique key for the widget
            
        Returns:
            str: The code entered by the user
        """
        return st.code(
            code,
            language=language,
            key=key
        ) 