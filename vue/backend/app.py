from flask import Flask, request
from flask_cors import CORS

# app = Flask(__name__)
# CORS(app)

def create_app():
    app = Flask(__name__)
    import time
    time.sleep(3)
    print("resource initiated")
    return app

app = create_app()
CORS(app)

@app.route("/")
def hello_world():
    return "testtest"

@app.route("/exec_query")
def hande_query():
    text = request.args.get('text', '')
    return text*5

# if __name__ == '__main__':
    # app = Flask(__name__)