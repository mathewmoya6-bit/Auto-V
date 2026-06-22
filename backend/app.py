from flask import Flask
import logging

from api.routes.mpesa import mpesa_bp

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")


@app.route("/")
def home():
    return {"status": "AUTO-V API running"}


if __name__ == "__main__":
    app.run(debug=True)
