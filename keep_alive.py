import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Shakespeare Bot is awake!"

def run():
    # Grabs the specific port Render assigns, defaulting to 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
