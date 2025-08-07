# 🤖 AI Smart File Organizer

An intelligent file organization system that uses local AI models via Ollama to automatically categorize, rename, and organize files in your Downloads folder. Say goodbye to messy downloads and hello to an intelligently structured file system!

## ✨ Features

### 🧠 True AI-Powered Organization
- **Content Analysis**: Reads and understands file contents, not just extensions
- **Intelligent Categorization**: 20+ smart categories (Work Documents, Financial Documents, Creative Projects, etc.)
- **Context Understanding**: Distinguishes between "recipe.pdf" and "contract.pdf" by analyzing content
- **Local AI**: Uses Ollama for privacy-first, offline AI processing

### 📝 Smart File Renaming
- **Descriptive Names**: Converts "IMG_1234.jpg" → "Screenshot_Login_Page_2024-01-15.jpg"
- **Professional Naming**: Uses underscores, dates (YYYY-MM-DD), and descriptive terms
- **Content-Based**: Names files based on what they actually contain
- **Conflict Resolution**: Handles duplicate names intelligently

### 📚 Dual Library System
- **AI Library**: Automatically organized files with AI-generated categories
- **Manual Library**: All existing folders automatically moved here for manual organization
- **Clean Structure**: Downloads folder stays organized with just two main libraries

### 🔄 Background Monitoring
- **Real-Time Processing**: Automatically processes new files as they're downloaded
- **Folder Management**: Moves any new folders to Manual Library automatically
- **Resource Efficient**: Low CPU usage with smart caching and polling
- **Graceful Shutdown**: Handles interruptions safely

### ⚡ Performance Optimized
- **AI Response Caching**: Avoids re-analyzing similar files
- **Smart File Reading**: Limits content analysis for large files (5MB+)
- **Memory Management**: Automatic cache size management
- **Timeout Protection**: Prevents hanging on slow AI responses

## 🚀 Installation

### Prerequisites
1. **Python 3.8+** (included with macOS)
2. **Ollama** - Install from [ollama.ai](https://ollama.ai)
3. **AI Model** - Will be automatically downloaded on first run

### Setup
1. **Clone or download the script:**
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/ai-smart-organizer/main/ai_smart_organizer.py
   chmod +x ai_smart_organizer.py
   ```

2. **Install and start Ollama:**
   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama service
   ollama serve
   ```

3. **Download an AI model** (optional - will auto-download):
   ```bash
   ollama pull llama3.2      # Default model (4GB)
   ollama pull gemma2:9b     # Alternative model (5.5GB)
   ollama pull deepseek-r1   # Code-focused model (5.2GB)
   ```

## 📖 Usage

### Basic Commands

**Preview what will be organized** (recommended first run):
```bash
python3 ai_smart_organizer.py --dry-run
```

**Organize existing files:**
```bash
python3 ai_smart_organizer.py
```

**Run in background monitoring mode:**
```bash
python3 ai_smart_organizer.py --monitor
```

### Advanced Options

**Use a specific AI model:**
```bash
python3 ai_smart_organizer.py --model "gemma2:9b" --dry-run
```

**Custom Downloads path:**
```bash
python3 ai_smart_organizer.py --path "/path/to/folder" --monitor
```

**Test with limited files:**
```bash
python3 ai_smart_organizer.py --max-files 5 --dry-run
```

**Generate detailed report:**
```bash
python3 ai_smart_organizer.py --report
```

**Custom library name:**
```bash
python3 ai_smart_organizer.py --library "My Smart Library" --monitor
```

### Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--model` | `-m` | Ollama model to use | `llama3.2` |
| `--path` | `-p` | Downloads folder path | `~/Downloads` |
| `--library` | `-l` | AI Library folder name | `AI Library` |
| `--dry-run` | `-d` | Preview without moving files | `false` |
| `--monitor` | | Run in background mode | `false` |
| `--max-files` | | Limit files to process | `unlimited` |
| `--report` | `-r` | Show detailed report | `false` |

## 🏗️ How It Works

### File Processing Pipeline
1. **Discovery**: Scans Downloads folder for new files
2. **Content Analysis**: AI reads file content and metadata  
3. **Categorization**: Assigns to one of 20+ intelligent categories
4. **Renaming**: Generates descriptive, professional filename
5. **Organization**: Moves to appropriate subfolder in AI Library

### Folder Management
- **Automatic Detection**: Finds all folders in Downloads
- **Protection**: Never moves AI Library or Manual Library folders
- **Organization**: Moves all other folders to Manual Library
- **Conflict Resolution**: Handles naming conflicts with numbered suffixes

### AI Categories

The system intelligently categorizes files into:

| Category | Examples |
|----------|----------|
| **Work Documents** | Reports, presentations, meeting notes |
| **Personal Documents** | Letters, forms, personal files |
| **Financial Documents** | Invoices, receipts, tax documents |
| **Educational Materials** | Courses, tutorials, research papers |
| **Images** | Photos, graphics, artwork |
| **Screenshots** | Screen captures, UI mockups |
| **Videos** | Movies, tutorials, recordings |
| **Audio/Music** | Songs, podcasts, audio files |
| **Code/Development** | Source code, scripts, documentation |
| **Archives/Downloads** | Zip files, installers, packages |
| **Creative Projects** | Design files, creative work |
| **Health/Medical** | Health records, medical documents |
| **Travel** | Itineraries, tickets, travel docs |
| **Recipes/Food** | Recipes, menu, food-related |
| **Legal Documents** | Contracts, legal papers |
| **Reference Materials** | Manuals, guides, references |
| **Entertainment** | Games, fun content, media |
| **Shopping/Receipts** | Purchase receipts, orders |
| **System Files** | Configuration, system-related |
| **Other** | Unrecognized or miscellaneous |

## 🎯 Background Mode

### Running as a Service
```bash
# Start monitoring (runs in foreground)
python3 ai_smart_organizer.py --monitor

# To run in background (detached)
nohup python3 ai_smart_organizer.py --monitor > ~/ai_organizer.log 2>&1 &
```

### What It Monitors
- **New Files**: Automatically processes any file added to Downloads
- **New Folders**: Moves any new folders to Manual Library
- **File Changes**: Detects when downloads complete
- **Performance**: Monitors every 2 seconds with minimal CPU usage

### Stopping Background Mode
```bash
# If running in foreground
Ctrl+C

# If running in background
pkill -f ai_smart_organizer.py
```

## 📁 Folder Structure

After running the organizer, your Downloads folder will look like:

```
Downloads/
├── AI Library/
│   ├── Work Documents/
│   │   ├── Meeting_Notes_2024-01-15.pdf
│   │   └── Quarterly_Report_Q4_2023.xlsx
│   ├── Images/
│   │   ├── Screenshot_Login_Interface_2024-01-15.png
│   │   └── Product_Photo_Blue_Widget.jpg
│   ├── Code/Development/
│   │   ├── Python_Data_Script.py
│   │   └── API_Documentation.md
│   └── Financial Documents/
│       ├── Invoice_Office_Supplies_2024-01.pdf
│       └── Receipt_Hardware_Store_2024-01-14.pdf
├── Manual Library/
│   ├── Old Project Folder/
│   ├── Random Stuff/
│   └── Photos from Trip/
└── (new files get processed automatically)
```

## 🔧 Configuration

### Performance Tuning
The script includes several performance settings you can modify:

```python
# In the AISmartOrganizer class __init__ method:
self.max_content_chars = 1500    # Max chars to read from files
self.ai_timeout = 25             # AI query timeout (seconds)  
self.cache_max_size = 500        # Max cached responses
```

### AI Model Selection
Choose models based on your needs:

- **llama3.2** (4GB) - Default, good balance of speed and accuracy
- **gemma2:9b** (5.5GB) - Larger, more accurate for complex files
- **deepseek-r1** (5.2GB) - Excellent for code and technical documents
- **qwen2.5:7b** (4.4GB) - Good multilingual support

## 🐛 Troubleshooting

### Common Issues

**"Ollama is not running or installed"**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve
```

**"Model not found"**
```bash
# List available models
ollama list

# Pull a model
ollama pull llama3.2
```

**"AI query timed out"**
- Your model might be too large for your system
- Try a smaller model like `gemma2:2b`
- Increase timeout in the script settings

**Files not being processed**
- Check if files are in AI Library or Manual Library (they're skipped)
- Verify file permissions
- Check the error log with `--report`

### Performance Issues

**High CPU usage:**
- Increase polling interval from 2 to 5 seconds
- Use a smaller AI model
- Reduce `max_content_chars` setting

**AI responses are slow:**
- Use a smaller model
- Increase `ai_timeout` setting
- Check if other apps are using the AI model

### Logs and Debugging

**View detailed errors:**
```bash
python3 ai_smart_organizer.py --report
```

**Run with maximum verbosity:**
```bash
python3 ai_smart_organizer.py --dry-run --max-files 1
```

**Check Ollama status:**
```bash
ollama list
curl http://localhost:11434/api/tags
```

## 🤝 Contributing

### Feature Requests
- Support for cloud AI services (OpenAI, Anthropic)
- Custom categorization rules
- Integration with cloud storage (Dropbox, Google Drive)
- Web interface for management
- Mobile app companion

### Development Setup
```bash
# Clone the repository
git clone https://github.com/your-repo/ai-smart-organizer.git
cd ai-smart-organizer

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) for local AI model serving
- [Meta](https://ai.meta.com) for Llama models
- [Google](https://deepmind.google) for Gemma models
- Python community for excellent libraries

## 📊 Stats

- **Languages**: Python 3.8+
- **Dependencies**: None (uses only standard library + curl)
- **AI Models**: Compatible with all Ollama models
- **File Types**: Supports 100+ file extensions
- **Categories**: 20+ intelligent categories
- **Performance**: <1% CPU usage in background mode

---

**Made with ❤️ for developers who love organized files!**

*If you find this useful, please ⭐ star the repository!*
