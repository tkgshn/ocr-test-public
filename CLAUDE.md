# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an OCR (Optical Character Recognition) system for Japanese handwritten improvement proposal sheets (改善提案シート). It uses Google Document AI as the primary OCR engine with coordinate-based text extraction and visualization capabilities.

## Common Development Commands

### Running the Application
```bash
# Using the provided script (recommended)
./run.sh

# Or manually with virtual environment
source venv/bin/activate
streamlit run app.py
```

### Setting up Development Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from example
cp env_example.txt .env
# Edit .env to add your API keys
```

## Architecture Overview

### Core Components

1. **app.py** - Streamlit web interface with two processing modes:
   - Single section OCR (Phase 1)
   - Multi-section OCR (Phase 2)

2. **ocr_processor.py** - Google Document AI integration:
   - Processes images/PDFs to extract text with coordinate information
   - Returns structured data with paragraphs, lines, tokens, and blocks
   - Primary OCR engine (OpenAI integration is commented out)

3. **multi_section_processor.py** - Handles documents with multiple sections:
   - Detects and splits document sections
   - Processes each section individually
   - Manages section categorization

4. **section_analyzer.py** - Computer vision analysis:
   - Uses OpenCV to detect horizontal lines and text regions
   - Classifies sections by Japanese keywords (課題, 提案, 対象, etc.)
   - Crops sections for individual processing

5. **ocr_visualizer.py** - Result visualization:
   - Creates overlay images with OCR bounding boxes
   - Supports different highlight levels (paragraphs, lines, tokens)

### Data Flow

1. User uploads handwritten form image → 
2. (Optional) Section analysis and splitting →
3. Google Document AI OCR processing →
4. Coordinate-based visualization →
5. Manual text correction UI →
6. Data organization by categories →
7. Export as Markdown/JSON

### Key Dependencies

- **Google Document AI**: Requires PROJECT_ID, PROCESSOR_ID, LOCATION
- **Streamlit**: Web UI framework
- **OpenCV**: Image processing for section detection
- **PIL/Pillow**: Image manipulation

### Environment Variables Required

```bash
# Google Cloud settings (required)
GOOGLE_CLOUD_PROJECT_ID=your_project_id
GOOGLE_CLOUD_LOCATION=us
GOOGLE_CLOUD_PROCESSOR_ID=your_processor_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT=us-documentai.googleapis.com

# OpenAI (optional, currently unused)
OPENAI_API_KEY=your_openai_key
```

## Important Notes

- The project focuses on Japanese text recognition
- No built-in linting or testing commands - code quality is managed manually
- Primary OCR is Google Document AI (OpenAI code exists but is commented out)
- Coordinate information is preserved throughout the pipeline for visualization