import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)
from PyPDF2 import PdfMerger
import pikepdf
from pdf2image import convert_from_path
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

user_files = {}  # store uploaded files per user

async def send_action_buttons(update: Update):
    keyboard = [
        [InlineKeyboardButton("Merge PDFs", callback_data='merge')],
        [InlineKeyboardButton("Split PDF", callback_data='split')],
        [InlineKeyboardButton("Compress PDF", callback_data='compress')],
        [InlineKeyboardButton("PDF to Images", callback_data='pdf2img')],
        [InlineKeyboardButton("Images to PDF", callback_data='img2pdf')],
        [InlineKeyboardButton("Clear Files", callback_data='clear')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Choose an action using the buttons below:",
        reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Merge PDFs", callback_data='merge')],
        [InlineKeyboardButton("Split PDF", callback_data='split')],
        [InlineKeyboardButton("Compress PDF", callback_data='compress')],
        [InlineKeyboardButton("PDF to Images", callback_data='pdf2img')],
        [InlineKeyboardButton("Images to PDF", callback_data='img2pdf')],
        [InlineKeyboardButton("Clear Files", callback_data='clear')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! Send me PDF files or images.\n"
        "Choose an action using the buttons below:",
        reply_markup=reply_markup
    )
    user_files[update.effective_user.id] = []

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        file = update.message.document
        if not file:
            await update.message.reply_text("No document found in your message.")
            return

        if file.mime_type != 'application/pdf':
            await update.message.reply_text("Please send a valid PDF file.")
            return

        new_file = await context.bot.get_file(file.file_id)
        file_path = os.path.join(TEMP_DIR, f"{user_id}_{file.file_name}")

        await new_file.download_to_drive(file_path)
        user_files.setdefault(user_id, []).append(file_path)

        await update.message.reply_text(f"PDF received: {file.file_name}")
        await send_action_buttons(update)

    except Exception as e:
        logging.error(f"Error in handle_document: {e}")
        await update.message.reply_text("Oops! Something went wrong while processing your PDF. Please try again.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        photos = update.message.photo
        if not photos:
            await update.message.reply_text("No photo found in your message.")
            return

        photo = photos[-1]  # highest resolution
        new_file = await context.bot.get_file(photo.file_id)
        file_path = os.path.join(TEMP_DIR, f"{user_id}_img_{photo.file_unique_id}.jpg")

        await new_file.download_to_drive(file_path)
        user_files.setdefault(user_id, []).append(file_path)

        await update.message.reply_text("Image received!")
        await send_action_buttons(update)

    except Exception as e:
        logging.error(f"Error in handle_photo: {e}")
        await update.message.reply_text("Oops! Something went wrong while processing your image. Please try again.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = query.from_user.id

    # Because these commands depend on uploaded files, check user_files
    if action == 'merge':
        await merge_pdfs(update, context)
    elif action == 'split':
        await query.edit_message_text(
            "To split a PDF, send the command with the page number, e.g. /split 3"
        )
    elif action == 'compress':
        await compress_pdf(update, context)
    elif action == 'pdf2img':
        await pdf_to_images(update, context)
    elif action == 'img2pdf':
        await images_to_pdf(update, context)
    elif action == 'clear':
        cleanup_files(user_id)
        await query.edit_message_text("Cleared all your uploaded files.")

async def merge_pdfs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    files = [f for f in user_files.get(user_id, []) if f.lower().endswith('.pdf')]

    if len(files) < 2:
        await send_message(update, "Please upload at least two PDF files to merge.")
        return

    merger = PdfMerger()
    try:
        for pdf in files:
            merger.append(pdf)
        output_path = os.path.join(TEMP_DIR, f"{user_id}_merged.pdf")
        merger.write(output_path)
        merger.close()
        await send_document(update, output_path, "merged.pdf")
    except Exception as e:
        logging.error(f"Error merging PDFs: {e}")
        await send_message(update, f"Error merging PDFs: {e}")
    finally:
        cleanup_files(user_id)

async def compress_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    files = [f for f in user_files.get(user_id, []) if f.lower().endswith('.pdf')]

    if not files:
        await send_message(update, "Please upload a PDF file to compress.")
        return

    pdf_path = files[-1]
    output_path = os.path.join(TEMP_DIR, f"{user_id}_compressed.pdf")

    try:
        with pikepdf.open(pdf_path) as pdf:
            pdf.save(output_path)
        await send_document(update, output_path, "compressed.pdf")
    except Exception as e:
        logging.error(f"Error compressing PDF: {e}")
        await send_message(update, f"Error compressing PDF: {e}")
    finally:
        cleanup_files(user_id)

async def pdf_to_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    files = [f for f in user_files.get(user_id, []) if f.lower().endswith('.pdf')]

    if not files:
        await send_message(update, "Please upload a PDF file to convert to images.")
        return

    pdf_path = files[-1]
    try:
        images = convert_from_path(pdf_path)
        for i, img in enumerate(images):
            img_path = os.path.join(TEMP_DIR, f"{user_id}_page_{i+1}.jpg")
            img.save(img_path, 'JPEG')
            await send_photo(update, img_path, f"Page {i+1}")
            os.remove(img_path)
    except Exception as e:
        logging.error(f"Error converting PDF to images: {e}")
        await send_message(update, f"Error converting PDF to images: {e}")
    finally:
        cleanup_files(user_id)

async def images_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    files = [f for f in user_files.get(user_id, []) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if not files:
        await send_message(update, "Please upload images to convert to PDF.")
        return

    try:
        image_list = [Image.open(f).convert('RGB') for f in files]
        output_path = os.path.join(TEMP_DIR, f"{user_id}_images_to_pdf.pdf")
        image_list[0].save(output_path, save_all=True, append_images=image_list[1:])
        await send_document(update, output_path, "images_to_pdf.pdf")
    except Exception as e:
        logging.error(f"Error converting images to PDF: {e}")
        await send_message(update, f"Error converting images to PDF: {e}")
    finally:
        cleanup_files(user_id)

def cleanup_files(user_id):
    files = user_files.get(user_id, [])
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception as e:
            logging.error(f"Error deleting file {f}: {e}")
    user_files[user_id] = []

async def send_message(update, text):
    if update.message:
        await update.message.reply_text(text)
    else:
        await update.callback_query.message.reply_text(text)

async def send_document(update, file_path, filename):
    if update.message:
        await update.message.reply_document(document=open(file_path, 'rb'), filename=filename)
    else:
        await update.callback_query.message.reply_document(document=open(file_path, 'rb'), filename=filename)

async def send_photo(update, photo_path, caption=None):
    if update.message:
        await update.message.reply_photo(photo=open(photo_path, 'rb'), caption=caption)
    else:
        await update.callback_query.message.reply_photo(photo=open(photo_path, 'rb'), caption=caption)

async def split_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    files = [f for f in user_files.get(user_id, []) if f.lower().endswith('.pdf')]

    if not files:
        await update.message.reply_text("Please upload a PDF file to split.")
        return

    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /split <page_number>")
        return

    split_page = int(args[0])
    pdf_path = files[-1]

    from PyPDF2 import PdfReader, PdfWriter

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        if split_page < 1 or split_page >= total_pages:
            await update.message.reply_text(f"Page number must be between 1 and {total_pages - 1}")
            return

        writer1 = PdfWriter()
        for i in range(split_page):
            writer1.add_page(reader.pages[i])
        part1 = os.path.join(TEMP_DIR, f"{user_id}_part1.pdf")
        with open(part1, 'wb') as f:
            writer1.write(f)

        writer2 = PdfWriter()
        for i in range(split_page, total_pages):
            writer2.add_page(reader.pages[i])
        part2 = os.path.join(TEMP_DIR, f"{user_id}_part2.pdf")
        with open(part2, 'wb') as f:
            writer2.write(f)

        await update.message.reply_document(document=open(part1, 'rb'), filename="part1.pdf")
        await update.message.reply_document(document=open(part2, 'rb'), filename="part2.pdf")
    except Exception as e:
        logging.error(f"Error splitting PDF: {e}")
        await update.message.reply_text(f"Error splitting PDF: {e}")
    finally:
        cleanup_files(user_id)

if __name__ == '__main__':
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in environment variables.")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("split", split_pdf_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot is running...")
    app.run_polling()
