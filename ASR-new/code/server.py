# set the project root directory as the static folder, you can set others.


from flask import Flask
from flask import render_template

# creates a Flask application, named app
app = Flask(__name__)

# a route where we will display a welcome message via an HTML template
@app.route("/")
def hello():
        #message = "Hello, World"
        return render_template('index.html')

        # run the application
if __name__ == "__main__":           
        app.run(host='0.0.0.0', port=6006)
