from flask import Flask
import threading
import time

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    while True:
        try:
            requests.get('https://marvelous-genie-2bce10.netlify.app/')
            time.sleep(60)
        except:
            pass

if __name__ == '__main__':
    t = threading.Thread(target=run)
    t.start()
    
    keep_alive()
