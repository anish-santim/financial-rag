# Financial RAG ChatBot with Government Updates

A comprehensive document analysis chatbot with automated government website scraping for the latest regulatory updates from Indian government agencies.

## 🚀 Features

### 📄 Document Analysis
- **Multi-format Support**: PDF, Word documents, text files, CSV files, and web URLs
- **AI-Powered Chat**: Ask questions about your uploaded documents
- **Smart Extraction**: Automatic text extraction from PDFs and Word documents
- **Interactive Viewing**: View documents with download options

### 🌐 Government Updates
- **5 Government Websites**: RBI, CBDT, ICAI, CBIC, MCA
- **Daily Scraping**: Automated daily updates via cron jobs
- **Real-time Display**: Latest updates shown in organized tabs
- **Historical Data**: 30-day retention of scraped content

### 💬 Chat System
- **Persistent Chats**: Save and load conversation history
- **User Management**: Secure login and registration system
- **Context Awareness**: AI remembers conversation context
- **Export Options**: Download chat history and documents

## 📋 Prerequisites

- Python 3.8 or higher
- Google API key for Gemini AI
- Unix-like system (Linux/macOS) for cron jobs

## 🛠️ Installation

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd financial-rag
pip install -r requirements.txt
```

### 2. Configure API Keys
Create `.streamlit/secrets.toml`:
```toml
GOOGLE_API_KEY = "your_google_api_key_here"
```

### 3. Run the Application
```bash
streamlit run main.py
```

## 🤖 Automated Scraping Setup

### Quick Setup (Recommended)
```bash
python setup_cron.py
```

This interactive script will:
- ✅ Test the scraper
- ✅ Set up cron job automatically
- ✅ Configure logging
- ✅ Provide manual instructions if needed

### Manual Cron Setup
1. Open crontab editor:
   ```bash
   crontab -e
   ```

2. Add this line for daily scraping at 6:00 AM:
   ```bash
   0 6 * * * /usr/bin/python3 /path/to/your/project/scraper.py >> /path/to/your/project/scraper_cron.log 2>&1
   ```

3. Save and verify:
   ```bash
   crontab -l
   ```

### Alternative Schedules
- **Twice daily**: `0 6,18 * * *`
- **Every 6 hours**: `0 */6 * * *`
- **Weekdays only**: `0 6 * * 1-5`
- **Weekly**: `0 6 * * 1`

## 📁 Project Structure

```
financial-rag/
├── main.py                 # Main Streamlit application
├── utils.py               # Utility functions
├── scraper.py             # Web scraping script
├── setup_cron.py          # Cron job setup helper
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .streamlit/
│   └── secrets.toml      # API keys (create this)
├── scraped_data/         # Scraped government data
│   ├── RBI/
│   ├── CBDT/
│   ├── ICAI/
│   ├── CBIC/
│   └── MCA/
├── user_data/            # User documents and chats
└── logs/                 # Application logs
```

## 🌐 Supported Government Websites

| Website | Full Name | Updates |
|---------|-----------|---------|
| **RBI** | Reserve Bank of India | Monetary policy, banking regulations |
| **CBDT** | Central Board of Direct Taxes | Income tax notifications, circulars |
| **ICAI** | Institute of Chartered Accountants | CA exams, accounting standards |
| **CBIC** | Central Board of Indirect Taxes | GST updates, customs notifications |
| **MCA** | Ministry of Corporate Affairs | Company law, compliance updates |

## 💻 Usage

### 1. User Registration/Login
- Create account or login with existing credentials
- Each user has isolated document storage and chat history

### 2. Document Upload
- Upload PDFs, Word docs, text files, or CSV files
- Or provide web URLs for analysis
- Documents are processed and indexed for AI chat

### 3. Government Updates
- Click "🌐 Government Updates" in sidebar
- Select any government website to view latest updates
- Updates are automatically fetched daily

### 4. AI Chat
- Start new chat or continue existing conversations
- Ask questions about uploaded documents
- Get intelligent responses with source references

### 5. File Viewing
- Click 👁️ (eye) button to view any uploaded file
- PDFs show extracted text with download option
- CSV files display as interactive tables

## 🔧 Configuration

### Scraper Settings
Edit `scraper.py` to customize:
- **Scraping frequency**: Modify cron schedule
- **Content retention**: Change `days_to_keep` parameter
- **Website URLs**: Update website configurations
- **Selectors**: Adjust CSS selectors for content extraction

### Streamlit Settings
Edit `main.py` to customize:
- **Page layout**: Modify `st.set_page_config()`
- **File upload limits**: Adjust file type restrictions
- **UI elements**: Customize sidebar and main content

## 📊 Monitoring

### Log Files
- **Application logs**: Check Streamlit console output
- **Scraper logs**: `scraper.log` and `scraper_cron.log`
- **Error tracking**: All errors logged with timestamps

### Health Checks
```bash
# Test scraper manually
python scraper.py

# Check cron job status
crontab -l

# View recent scraper logs
tail -f scraper_cron.log
```

## 🚨 Troubleshooting

### Common Issues

**1. Scraper Not Running**
```bash
# Check cron service
sudo service cron status

# Test scraper manually
python scraper.py

# Check permissions
chmod +x scraper.py
```

**2. API Key Issues**
- Verify Google API key in `.streamlit/secrets.toml`
- Check API quotas and billing
- Ensure Gemini API is enabled

**3. File Upload Problems**
- Check file size limits
- Verify file format support
- Ensure proper permissions on user_data folder

**4. Missing Dependencies**
```bash
pip install -r requirements.txt
```

### Windows Users
- Cron jobs not available on Windows
- Use Windows Task Scheduler instead
- Run `setup_cron.py` for manual instructions

## 🔒 Security

- **User Authentication**: Secure password hashing
- **Data Isolation**: Each user's data is separate
- **API Security**: Keys stored in secure config files
- **Input Validation**: File type and size restrictions

## 📈 Performance

- **Efficient Processing**: Chunked document processing
- **Caching**: Vector store caching for faster responses
- **Cleanup**: Automatic old file removal
- **Rate Limiting**: Respectful scraping with delays

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review log files for errors
3. Test components individually
4. Create an issue with detailed error information

## 🔄 Updates

The system automatically:
- ✅ Scrapes government websites daily
- ✅ Cleans up old files (30+ days)
- ✅ Logs all activities
- ✅ Handles errors gracefully
- ✅ Maintains data consistency

---

**Happy Document Analysis! 🚀📄🤖**
