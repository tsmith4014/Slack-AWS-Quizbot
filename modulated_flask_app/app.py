from flask import Flask
import logging
from config import SLACK_SIGNING_SECRET, SLACK_BOT_TOKEN
from routes import init_routes

app = Flask(__name__)

app.config['SLACK_SIGNING_SECRET'] = SLACK_SIGNING_SECRET
app.config['SLACK_BOT_TOKEN'] = SLACK_BOT_TOKEN

# Initialize routes
init_routes(app)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0')