from typing import Final
import requests
import clever_chat
import os
import random
from dotenv import load_dotenv
from parsel import Selector
from clever_chat import Client
from telegram import Update
from telegram.ext import Updater, Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


TOKEN: Final = '6979522872:AAE7oPHzrlqbfuXCXFiIW_95qmoOx1R5dyQ'
BOT_USERNAME: Final = 'breancbot'
reccoFlag = False

# Commands

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('You can try chatting or type /reccos for some food recommendation!')

async def reccos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global reccoFlag
    reccoFlag = True
    await update.message.reply_text('Sure, please enter your postal code and I\'ll recommend something!')


#error handling
async def error(update: Update, context:ContextTypes.DEFAULT_TYPE):
    print (f'Update {update} caused error {context.error}')

#Handle Responses
async def handle_message(update: Update, context:ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User({update.message.chat.id} in {message_type}: "{text}"')

    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME,'').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(update, text)


    print('Bot:', response)
    await update.message.reply_text(response)

def handle_response(update: Update, text: str) -> str:
    global reccoFlag
    processed: str = text.lower()

    if '/quit' == processed:
            if reccoFlag is True:
                reccoFlag = False
                return "Ok lor I stop recommending..."
            else:
                return 'Don\'t gaslight leh you didn\'t ask for recommendations..'
    
    if reccoFlag is True:
        chatId = str(update.message.chat.id)
        requests.get("https://api.telegram.org/bot"+str(TOKEN)+"/sendMessage?chat_id="+chatId+"&text=Wait ah, it\'ll take some time...")
        return handleRecommendations(processed)
    return Client.get_response(processed)

def handleRecommendations(postal):
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
     
    if status != 'CONFIRMED':
        return "Enter your postal properly leh or just type /quit to quit reccos"

    url = (queryGenerator() +postal)

    #Scrape results
    options = Options()
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    results = "How about the following:\n"
    page_content = driver.page_source
    response = Selector(page_content)
    for el in response.xpath('//div[contains(@aria-label, "Results for")]/div/div[./a]'):
        results = results + (el.xpath('./a/@aria-label').extract_first('')) + "\n"
        results = results + el.xpath('./a/@href').extract_first('')+ "\n"
        results = results + "\n"

    driver.close()
    reccoFlag = False
    return results

def queryGenerator():
    list = ["https://www.google.com/maps/search/best+food+near+",
            "https://www.google.com/maps/search/what+to+eat+near+",
            "https://www.google.com/maps/search/good+food+near+",
            "https://www.google.com/maps/search/whats+nice+to+eat+near+",
            "https://www.google.com/maps/search/+food+near+"]
    return  random.choice(list)

if __name__=='__main__':
    app = Application.builder().token(TOKEN).build()

    load_dotenv()   
    #Commands
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('reccos', reccos_command))

    #messages
    app.add_handler(MessageHandler(filters.TEXT,handle_message))

    #error
    app.add_error_handler(error)

    #Polls the bot https://docs.python-telegram-bot.org/en/v20.6/telegram.ext.application.html
    app.run_polling(poll_interval=3)
