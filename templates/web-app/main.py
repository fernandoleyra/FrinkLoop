"""
Web App project — starter scaffold.
Agents will implement pages, components, and logic based on the BRIEF.
"""

from flask import Flask
from webapp.routes import register_routes
from webapp.config import Config

app = Flask(__name__)
app.config.from_object(Config)
register_routes(app)

if __name__ == "__main__":
    app.run(debug=Config.DEBUG, port=Config.PORT)
