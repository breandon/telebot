from typing import Final
import requests
# import clever_chat
import os
import random
from dotenv import load_dotenv
from parsel import Selector
# from clever_chat import Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, filters, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TOKEN: Final = '6765549874:AAFQkmLUT7yZJ1bJlV0KBjQhGzkmRX1T6Po'
BOT_USERNAME: Final = 'gowhereeatsgbot'
ENTER_POSTAL, PROCESS_QUERY, DISPLAY_RESULT, CHAT_MESSAGE = range(4)

# Commands
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('You can try chatting or type /reccos for some food recommendation!')

async def reccos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global reccoFlag
    reccoFlag = True
    await update.message.reply_text('Sure, please enter your postal code and I\'ll recommend something!')
    return ENTER_POSTAL

# async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text('Sure, let\'s talk about something!')
#     return CHAT_MESSAGE

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
    query = update.callback_query
    isFiltered = False
    if query.data == '1':
        isFiltered = True
        await query.edit_message_text("Selected option: Open now")
    else: 
        await query.edit_message_text("Selected option: Open anytime")
    url = (queryGenerator(isFiltered, context.user_data["postal"]))

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please hold on while we search...")
    #Scrape results by scrolling to bottom
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-notifications')
    options.add_argument("-incognito")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 1)
    driver.get(url)
    print(url)
    count = 0
    for i in range(5):
        try:
            wait.until(EC.visibility_of_element_located((By.XPATH, "//span[contains(text(),'reached the end')]")))
            barraRolagem = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']//div[@aria-label]")))
            driver.execute_script("arguments[0].scroll(0, arguments[0].scrollHeight);", barraRolagem)
            break
        except:
            barraRolagem = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']//div[@aria-label]")))
            driver.execute_script("arguments[0].scroll(0, arguments[0].scrollHeight);", barraRolagem)
    page_content = driver.page_source
    response = Selector(page_content)

    #construct result   
    dict = {} #key: type of restaurant, value: list of restaurants {name, link, priceRange, type, reviews}
    listings = response.xpath('//div[contains(@aria-label, "Results for")]/div/div[./a]')
    for el in listings:             
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
        categories = mapCategory(type)
        for category in categories:
            if category not in dict:
                dict[category] = [result]
            else: 
                dict[category].append(result)
    driver.close()

    keyboard = []
    for key, value in dict.items():
        keyboard.append([InlineKeyboardButton(key, callback_data=key)])
    context.user_data["results"] = dict
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Filter by restaurant type:", reply_markup=reply_markup)
    return DISPLAY_RESULT

async def display_result(update, context):
    query = update.callback_query
    type = query.data
    await query.edit_message_text("Selected option: " + type)
    results = "How about the following:\n"
    #construct results
    for item in context.user_data["results"][type]:
        results = results + '<a href="{0}">{1}</a>'.format(item['link'], item['name']) + " - " + item['priceRange'] + "\n"
        results = results + item['type'] + "\n" + item['reviews'] + "\n"
        results = results + "\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text= results, parse_mode = 'html')
    return ConversationHandler.END

def mapCategory(type):
    type = type.lower()
    categories = ['All']
    if 'halal' in type or 'muslim' in type or 'malay' in type:
        categories.append('Halal')
    if 'vegetarian' in type:
        categories.append('Vegetarian')
    if 'chinese' in type:
        categories.append('Chinese')
    if 'indian' in type:
        categories.append('Indian')
    if 'western' in type or 'steak' in type or 'grill' in type:
        categories.append('Western')
    if 'thai' in type:
        categories.append('Thai')
    if 'korean' in type:
        categories.append('Korean')
    if 'hot pot' in type:
        categories.append('Hot Pot')
    if 'fast food' in type:
        categories.append('Fast Food')
    if 'cafe' in type:
        categories.append('Cafe')
    if 'hawker' in type:
        categories.append('Hawker')
    if 'food court' in type:
        categories.append('Food Court')
    if 'restaurant' in type:
        categories.append('Restaurant')

    return categories

def queryGenerator(isFiltered, postal):

    additionalFilter = "near+singapore+"+postal
    if isFiltered:
        additionalFilter = additionalFilter+"+open+now"
    list = ["https://www.google.com/maps/search/food+"+additionalFilter,
            "https://www.google.com/maps/search/good+food+"+additionalFilter,
            "https://www.google.com/maps/search/+best+food+"+additionalFilter]
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

# #handle chats
# async def handle_message(update: Update, context:ContextTypes.DEFAULT_TYPE):
#     message_type: str = update.message.chat.type
#     text: str = update.message.text

#     print(f'User({update.message.chat.id} in {message_type}: "{text}"')

#     if message_type == 'group':
#         if BOT_USERNAME in text:
#             new_text: str = text.replace(BOT_USERNAME,'').strip()
#             response: Client.get_response(text)
#         else:
#             return
#     else:
#         response: str =  Client.get_response(text)

#     print('Bot:', response)
#     await update.message.reply_text(response)
#     return CHAT_MESSAGE


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
            DISPLAY_RESULT: [CallbackQueryHandler(display_result)]
        },
        fallbacks=[CommandHandler('quit', quit_command)]
    )
    app.add_handler(recco_handler)

    # conv_handler = ConversationHandler(
    #     entry_points=[CommandHandler('chat', chat_command)], 
    #     states={
    #         CHAT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
    #     },
    #     fallbacks=[CommandHandler('quit', quit_command)]
    # )
    # app.add_handler(conv_handler)
    
    #error
    app.add_error_handler(error)

    #Polls the bot https://docs.python-telegram-bot.org/en/v20.6/telegram.ext.application.html
    app.run_polling(poll_interval=3)
