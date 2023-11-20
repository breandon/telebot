from typing import Final
import requests
import clever_chat
import os
import random
from dotenv import load_dotenv
from parsel import Selector
from clever_chat import Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Application, filters, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TOKEN: Final = '6979522872:AAE7oPHzrlqbfuXCXFiIW_95qmoOx1R5dyQ'
BOT_USERNAME: Final = 'breancbot'
ENTER_POSTAL, PROCESS_QUERY, FILTER_REST,  CHAT_MESSAGE = range(4)

# Commands
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('You can try chatting or type /reccos for some food recommendation!')

async def reccos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global reccoFlag
    reccoFlag = True
    await update.message.reply_text('Sure, please enter your postal code and I\'ll recommend something!')
    return ENTER_POSTAL

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Sure, let\'s talk about something!')
    return CHAT_MESSAGE

async def quit_command(update, context):
    await update.message.reply_text('Sure, good bye!')
    return ConversationHandler.END

async def enter_postal(update, context):
    postal = update.message.text
    context.user_data["postal"] = postal
    if validatePostal(postal) == False:
        await update.message.reply_text(f'Please enter a valid Postal Code or just type /quit to quit recommendation')
        return ENTER_POSTAL
    keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data="1"),
                InlineKeyboardButton("No", callback_data="2"),
            ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text="Fillter by opening hours", reply_markup=reply_markup)
    return PROCESS_QUERY


async def process_query(update, context):
    """Show new choice of buttons"""
    query = update.callback_query
    isFiltered = False
    if query.data == '1':
        isFiltered = True
        await query.edit_message_text("Selected option: Open now")
    else: 
        await query.edit_message_text("Selected option: Open anytime")
    url = (queryGenerator(isFiltered, context.user_data["postal"]))
    #Scrape results
    options = Options()
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    page_content = driver.page_source
    response = Selector(page_content)
    dict = {'All':[]}
    for el in response.xpath('//div[contains(@aria-label, "Results for")]/div/div[./a]'):  
        #construct result              
        name = (el.xpath('./a/@aria-label').extract_first(''))
        link =  el.xpath('./a/@href').extract_first('')
        priceRange = el.xpath('./div[2]/div[4]/div[1]/div/div/div[2]/div[3]/div/span[3]/span[2]/text()').extract_first('')
        if priceRange == '':
            priceRange = "No price range yet"
        type = el.xpath('./div[2]/div[4]/div[1]/div/div/div[2]/div[4]/div[1]/span[1]/span/text()').extract_first('')
        reviews = el.xpath('./div[2]/div[4]/div[1]/div/div/div[2]/div[3]/div/span[2]/span/@aria-label').extract_first('')
        if reviews == '':
            reviews = "No reviews yet"
        result =  { "name":name, "link":link, "priceRange":priceRange, "type":type,"reviews":reviews}
        if type not in dict:
            newList = [result]
            dict[type] = newList
        else: 
            dict[type].append(result)
        dict['All'].append(result)
    driver.close()

    keyboard = []
    for key, value in dict.items():
        keyboard.append([InlineKeyboardButton(key, callback_data=key)])
    context.user_data["results"] = dict
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Filter by restaurant type:", reply_markup=reply_markup)
    return FILTER_REST

async def filter_restaurant(update, context):
    query = update.callback_query
    type = query.data
    await query.edit_message_text("Selected option: " + type)
    results = "How about the following:\n"
    for item in context.user_data["results"][type]:
        results = results + '<a href="{0}">{1}</a>'.format(item['link'], item['name']) + " - " + item['priceRange'] + "\n"
        results = results + item['type'] + "\n" + item['reviews'] + "\n"
        results = results + "\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text= results, parse_mode = 'html')
    return ENTER_POSTAL

def queryGenerator(isFiltered, postal):

    additionalFilter = "near+singapore+"+postal
    if isFiltered:
        additionalFilter = additionalFilter+"+open+now"
    list = ["https://www.google.com/maps/search/best+food+"+additionalFilter,
            "https://www.google.com/maps/search/what+to+eat+"+additionalFilter,
            "https://www.google.com/maps/search/good+food+"+additionalFilter,
            "https://www.google.com/maps/search/+restaurants+"+additionalFilter]
    return  random.choice(list)

def validatePostal(postal):
    googleKey = os.getenv('API_KEY') 
    payload = {
		"address": {
			"postalCode": postal,
			"addressLines": ["Singapore"]
		},
		"enableUspsCass": False # set to True for US addresses
	}
    url = "https://addressvalidation.googleapis.com/v1:validateAddress?key=" + googleKey
    response = requests.post(url, json=payload)
    status = response.json()['result']['address']['addressComponents'][1]['confirmationLevel']
    if status == 'CONFIRMED':
        return True
    return False

#handle chats
async def handle_message(update: Update, context:ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User({update.message.chat.id} in {message_type}: "{text}"')

    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME,'').strip()
            response: Client.get_response(text)
        else:
            return
    else:
        response: str =  Client.get_response(text)

    print('Bot:', response)
    await update.message.reply_text(response)
    return CHAT_MESSAGE


#error handling
async def error(update: Update, context:ContextTypes.DEFAULT_TYPE):
    print (f'Update {update} caused error {context.error}')



if __name__=='__main__':
    app = Application.builder().token(TOKEN).build()
    load_dotenv()   

    #Commands
    app.add_handler(CommandHandler('help', help_command))
    
    recco_handler = ConversationHandler(
        entry_points=[CommandHandler('reccos', reccos_command)], 
        states={
            ENTER_POSTAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_postal)],
            PROCESS_QUERY: [CallbackQueryHandler(process_query)],
            FILTER_REST: [CallbackQueryHandler(filter_restaurant)]
        },
        fallbacks=[CommandHandler('quit', quit_command)]
    )
    app.add_handler(recco_handler)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('chat', chat_command)], 
        states={
            CHAT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        },
        fallbacks=[CommandHandler('quit', quit_command)]
    )
    app.add_handler(conv_handler)
    #error
    app.add_error_handler(error)

    #Polls the bot https://docs.python-telegram-bot.org/en/v20.6/telegram.ext.application.html
    app.run_polling(poll_interval=3)
