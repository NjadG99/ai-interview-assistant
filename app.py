from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/features.html')
def features():
    return render_template('features.html')

@app.route('/hire-ready-ai.html')
def hire_ready_ai():
    return render_template('hire-ready-ai.html')

@app.route('/mock-interview.html')
def mock_interview():
    return render_template('mock-interview.html')

@app.route('/aboutus.html')
def aboutus():
    return render_template('aboutus.html')

if __name__ == '__main__':
    app.run(debug=True)
