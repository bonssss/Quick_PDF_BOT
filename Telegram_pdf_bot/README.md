# Quick PDF Bot

A Telegram bot that allows users to manage PDF files and images. Users can merge, split, compress PDFs, convert PDFs to images, and convert images to PDFs—all directly from Telegram.

## Features

- **Merge PDFs**: Combine multiple PDF files into a single file.
- **Split PDF**: Split a PDF into two parts at a specified page.
- **Compress PDF**: Reduce the size of PDF files.
- **PDF to Images**: Convert PDF pages to JPEG images.
- **Images to PDF**: Convert uploaded images into a single PDF.
- **Clear Files**: Delete all uploaded files for a user.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/bonssss/Quick_PDF_BOT.git
cd Quick_PDF_BOT
```
2. Create a virtual environment:
```
python -m venv venv
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate
```
3. Install dependencies:
```
pip install -r requirements.txt

```
4. Create a .env file in the project root and add your Telegram bot token:
```
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
```
5. Run the bot:
```
python pdf-bot.py
```
## Contributing
Contributions are welcome! Please open an issue or submit a pull request to improve the bot.
