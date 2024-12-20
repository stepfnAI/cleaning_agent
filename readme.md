# Data Cleaning Advisor

An AI-powered data cleaning tool that analyzes your dataset and provides intelligent suggestions for data quality improvements, with interactive implementation capabilities.

## 🌟 Features

- **Intelligent Data Analysis**: Automatically analyzes your dataset's structure, types, and quality issues
- **Smart Cleaning Suggestions**: Generates contextual data cleaning recommendations
- **Interactive Processing**: Choose between reviewing suggestions one-by-one or batch processing
- **Flexible Data Input**: Supports multiple file formats (CSV, Excel, JSON, Parquet)
- **Real-time Progress Tracking**: Visual feedback on suggestion implementation progress
- **Data Export**: Download cleaned data in CSV format

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:

```bash
    git clone [repository-url]
    cd [repository-name]
```

2. Create and activate a virtual environment:

```bash
python -m venv myenv # or use python3 if you have multiple Python versions
source myenv/bin/activate # Linux/Mac
.\myenv\Scripts\activate # Windows
```

3. Install the package in development mode:
```bash
pip install -e .
```
This step is crucial as it makes the `cleaning_agent` package importable by Python. Without this step, you'll get "ModuleNotFoundError" when trying to run the application.

4. Set up your OpenAI API key:
Create a `.env` file in the root directory and add:
```bash
OPENAI_API_KEY=your_openai_api_key
```

### Running the Application

```bash
streamlit run .\examples\app.py  
```

## 🔄 Workflow

1. **Data Loading**
   - Upload your dataset (CSV, Excel, JSON, or Parquet)
   - Preview the loaded data

2. **Data Analysis & Suggestions**
   - AI analyzes your data for quality issues
   - Generates specific cleaning suggestions based on:
     - Missing values
     - Duplicate records
     - Data types
     - Dataset structure

3. **Suggestion Implementation**
   - Choose between:
     - Individual review mode (one-by-one)
     - Batch processing mode
   - Apply, skip, or review each suggestion
   - Real-time progress tracking

4. **Post Processing**
   - View the cleaned data
   - Download the processed dataset
   - Review cleaning summary

## 🛠️ Architecture

The application follows a modular architecture with these key components:

- **SFNCleanSuggestionsAgent**: Analyzes data and generates cleaning suggestions
- **SFNFeatureCodeGeneratorAgent**: Converts suggestions to executable code
- **SFNCodeExecutorAgent**: Safely executes generated code
- **SFNDataPostProcessor**: Handles data export and final processing
- **SFNStreamlitView**: Manages the user interface
- **SFNSessionManager**: Handles application state

## 🔒 Security

- Sandboxed code execution
- Environment variables for sensitive data
- Input validation for all user data
- Secure data handling

## 📊 Data Analysis Features

The tool analyzes multiple aspects of your data:
- Dataset shape and structure
- Column data types
- Missing value patterns
- Duplicate records
- Data quality metrics

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

Email: puneet@stepfunction.ai
