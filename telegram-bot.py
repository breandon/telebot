from typing import Final
import requests
import clever_chat
import os
from dotenv import load_dotenv
from clever_chat import Client
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN: Final = '6979522872:AAE7oPHzrlqbfuXCXFiIW_95qmoOx1R5dyQ'
BOT_USERNAME: Final = 'breancbot'
reccoFlag = False

# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! thanks for chatting with me!')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('You can try speaking to my manager @thirteenbones')


async def reccos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global reccoFlag
    reccoFlag = True
    await update.message.reply_text('Sure, please enter your postal code and I\'ll recommend something!')

#Chat GPT
def answer_gpt(question):
    return Client.get_response(question)

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

    print(status)       
    if status == 'CONFIRMED':
        return True
    return False
	
    
def handle_reccos(postal):
    if validatePostal(postal) is True:
        return "Opps I am still building the feature to recommend food"
    return "Enter your postal properly leh or just type /quit to quit reccos"

#Responses
def handle_response(text: str) -> str:
    global reccoFlag
    processed: str = text.lower()

    if '/quit' == processed:
            if reccoFlag is True:
                reccoFlag = False
                return "Ok lor I stop recommending..."
            else:
                return 'Don\'t gaslight leh you didn\'t ask for recommendations..'
    
    if reccoFlag is True:
        return handle_reccos(processed)
      
    return answer_gpt(processed)


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
        response: str = handle_response(text)


    print('Bot:', response)
    await update.message.reply_text(response)


async def error(update: Update, context:ContextTypes.DEFAULT_TYPE):
    print (f'Update {update} caused error {context.error}')


if __name__=='__main__':
    app = Application.builder().token(TOKEN).build()

    load_dotenv()   
    #Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('reccos', reccos_command))

    #messages
    app.add_handler(MessageHandler(filters.TEXT,handle_message))

    #error
    app.add_error_handler(error)

    #Polls the bot
    app.run_polling(poll_interval=3)
