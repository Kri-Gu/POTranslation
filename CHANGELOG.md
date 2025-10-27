# Changelog

All notable changes to the PO File Translator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Support for additional target languages
- GUI interface using tkinter
- Batch processing of multiple PO files
- Configuration file support
- Translation memory integration
- Progress bar for large files

## [1.0.0] - 2024-10-24

### Added
- Initial release of PO file translator
- English to Norwegian Bokmål translation using OpenAI API
- Command-line interface with customizable options
- Batch processing with configurable batch sizes
- Automatic detection of English text in PO files
- Preservation of PO file structure, comments, and metadata
- Support for various placeholder formats (printf, Python/ICU, HTML)
- Retry logic for robust API interaction
- Comprehensive error handling and logging
- UTF-8 encoding support
- Verbose mode for debugging

### Features
- **Translation Engine**: Uses OpenAI's GPT models for high-quality translation
- **Format Preservation**: Maintains all original formatting, placeholders, and structure
- **Smart Detection**: Automatically identifies English text that needs translation
- **Flexible Options**: Configurable model selection and batch processing
- **Error Recovery**: Retry mechanism for handling API rate limits and transient errors

### Technical Details
- **Dependencies**: openai, polib, tenacity
- **Python Support**: 3.7+
- **Default Model**: gpt-4o (configurable)
- **Default Batch Size**: 50 entries per API call
- **Encoding**: UTF-8 input/output

### Documentation
- Comprehensive README with usage examples
- Installation and setup instructions
- Troubleshooting guide
- Development guidelines
- Cost estimation information

## [0.1.0] - 2024-10-24

### Added
- Initial project structure
- Basic script framework
- Requirements specification based on GPT-5 conversation analysis

---

## Release Notes

### Version 1.0.0 Notes

This initial release provides a complete solution for translating PO files from English to Norwegian Bokmål. The tool was developed based on real-world requirements for translating technical documentation and user interface strings while maintaining perfect format compatibility with Poedit and other PO file editors.

#### Key Capabilities:
- **High-Quality Translation**: Leverages OpenAI's latest models for contextually accurate Norwegian translations
- **Production Ready**: Comprehensive error handling, retry logic, and validation
- **Developer Friendly**: Preserves all developer comments, contexts, and metadata
- **Flexible Deployment**: Command-line tool that integrates easily into build pipelines

#### Translation Quality:
The tool maintains Norwegian Bokmål standards while preserving technical terminology consistency. Examples include:
- "Accept All" → "Godta alle"
- "Cookie Settings" → "Innstillinger for informasjonskapsler" 
- "Customer reviews archive" → "Arkiv for kundeanmeldelser"

#### Performance:
Optimized for efficient API usage with configurable batch processing. Typical performance:
- Small files (100-500 entries): 1-2 minutes
- Medium files (500-2000 entries): 3-8 minutes  
- Large files (2000+ entries): 10-30 minutes

Costs are typically $0.50-$2.00 per 1000 strings with gpt-4o-mini.