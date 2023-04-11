import openai
import json
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters,CallbackContext, Filters
import configparser
import logging
import redis
import logging
global redis1
import requests
import pymongo


#client = pymongo.MongoClient("mongodb+srv://RYL:<password>@cluster1.dgv9hlo.mongodb.net/?retryWrites=true&w=majority")
#db = client.test
conn_str = "mongodb+srv://RYL:RenRenYL@cluster1.dgv9hlo.mongodb.net/?retryWrites=true&w=majority"
# 设置连接超时的时间为500ms（5s）
client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)   
db = client.FirstDB
collection = db.FirstCO
try:
    print("info:\n"+str(client.server_info()))                   # 输出服务信息
    
except Exception:
    print("无法连接到MongoDB服务")  

# 获取 api
def get_config():
    config_file = 'configs'
    with open(config_file, 'r', encoding='utf-8') as f:
        configs = json.loads(f.read())
    return configs
openai.api_key = get_config()['api']

API_KEY = '73787eaea250fccf10c6761975dafe29'
CITY_NAME = 'Qinhuangdao'

def start(update, context):
    """发送欢迎消息"""
    message = "Welcome to use this chatBot! \n If you want to check the weather today, use /weather and input your location \n If you want to chat, type /chat and input the words you want!"
    update.message.reply_text(message)
    # 输出调试信息
    logging.debug(f"Sent a welcome message to {update.effective_chat.id}. Message content: {message}")

class ChatGPT:
    def __init__(self, user):
        self.user = user
        self.messages = [{"role": "system", "content": "hello there"}]
        self.filename = "./user_messages.json"

    def ask_gpt(self):
        # q = "用python实现：提示手动输入3个不同的3位数区间，输入结束后计算这3个区间的交集，并输出结果区间"
        rsp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.messages
        )
        return rsp.get("choices")[0]["message"]["content"]
    '''
    def writeTojson(self):
        try:
            # 判断文件是否存在
            if not os.path.exists(self.filename):
                with open(self.filename, "w") as f:
                    # 创建文件
                    pass
            # 读取
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read()
                msgs = json.loads(content) if len(content) > 0 else {}
            # 追加
            msgs.update({self.user: self.messages})
            # 写入
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(msgs, f)
        except Exception as e:
            print(f"错误代码：{e}")
    '''

def get_weather(city):
    #访问OpenWeather API获取当前天气
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}'
    response=requests.get(url)
    data = response.json()

    #解析返回的JSON数据并提取所需的天气信息
    weather = data['weather'][0]['description']
    temperature = round(data['main']['temp'] - 273.15,1)#将温度从开尔文转换为摄氏度

    # 返回格式化后的天气信息
    return f'City: {city} \nWeather: {weather} \nTemperature: {temperature}℃'
 
def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    updater = Updater(token=(config['TELEGRAM']['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher

    global redis1
    redis1 = redis.Redis(host=(config['REDIS']['HOST']), password=(config['REDIS']['PASSWORD']), port=(config['REDIS']['REDISPORT']))

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater.dispatcher.add_handler(CommandHandler('weather', weather_handler))
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    dispatcher.add_handler(echo_handler)

    dispatcher.add_handler(CommandHandler("chat", ChatGPT_command))
    dispatcher.add_handler(CommandHandler("start", start))


    updater.start_polling()
    updater.idle()

def echo(update, context):
    """回显用户的文本消息"""
    text = update.message.text
    update.message.reply_text(text)
    # 输出调试信息
    logging.debug(f"Echoed the message {text} to {update.effective_chat.id}")

def weather_handler(update: Update, context: CallbackContext) -> None:
    #当用户发送 /weather 命令时，调用get_weather函数并将结果返回给用户
    city = context.args[0]
    message = get_weather(city)
    update.message.reply_text(message)
    collection.insert_one({'question': city,'answer': message})

def ChatGPT_command(update: Update, context: CallbackContext) -> None:
    """使用ChatGPT API回复消息"""
    user = update.message.chat_id
    chat = ChatGPT(user)
    #global redis1

    # 获取命令参数
    message = " ".join(context.args)
    print ('msg:'+message)
    # 将用户输入添加到历史消息中
    chat.messages.append({"role": "user", "content": message})

    # 调用OpenAI的API进行对话生成
    response = chat.ask_gpt()
    print ('res:'+response)
    redis1.incr(response)
    print (response)
    # 将对话生成的结果添加到历史消息中
    chat.messages.append({"role": "assistant", "content": response})

    # 发送回答
    update.message.reply_text(response)

    collection.insert_one({'question': update.message.text,'answer': response})



if __name__ == '__main__':
    main()

