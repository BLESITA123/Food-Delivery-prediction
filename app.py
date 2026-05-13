from flask import Flask, render_template, request, redirect, url_for, flash, session
from sympy import re
#why render template is used here?render_template is used to render the html file to browser
#redirect- is used to redirect the user to a different page after a certain action is performed
#url_for- is used to generate the url for a specific function
#flash- is used to display a message to the user after a certain action is performed
#session- is used to store data across multiple requests(login -log out)
#request- is used to access the data sent by the user in a form
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re #regular expression is used to validate the email format and password strength
import joblib
import numpy as np


app=Flask(__name__)
app.secret_key='1122' #to track session data 

#load saved model and encoder
model = joblib.load('delivery_time_model.pkl')
lb = joblib.load('taffic_encoder.pkl')

#database connection

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user="root",
        password="",
        database="food_db",
        #port=3307 if 3306 is not working
    )
    

#only for first page we use / for other pages we can use /about, /contact etc
@app.route('/') #this is the home page of the application or the 1st page to be loaded when the application is run
def index():
    return render_template('index.html') #this will render the index.html file to the browser   

@app.route('/about')
def about():
    return render_template('about.html')    

@app.route('/methodology')
def methodology():
    return render_template('methodology.html') 

@app.route('/predict', methods=['GET', 'POST'])
def predict():

    #check login status
    if 'user_id' not in session:
        flash('Please log in to access the prediction feature.', 'warning')
        return redirect(url_for('login'))
    
    prediction_text = None

    if request.method == 'POST':
        #get form data
        #take user input
        distance= float(request.form['distance'])
        t_level= request.form['t_level']
        p_time= int(request.form['p_time'])
        experience= float(request.form['experience'])
        weather= request.form['weather']
        time= request.form['time']
        vehicle= request.form['vehicle']

        #---------Traffic level encoding---------
        # Clean input
        t_level = t_level.strip().capitalize()

        traffic_map = {
            "Low": 0,
            "Medium": 1,
            "High": 2
        }

        t_level = traffic_map.get(t_level)

        if t_level is None:
            return "Invalid traffic level"
        # ----------- Weather Encoding ------------
        Weather_Clear = 0
        Weather_Foggy = 0
        Weather_Rainy = 0
        Weather_Snowy = 0
        Weather_Windy = 0

        if weather == "Clear":
            Weather_Clear = 1
        elif weather == "Foggy":
            Weather_Foggy = 1
        elif weather == "Rainy":
            Weather_Rainy = 1
        elif weather == "Snowy":
            Weather_Snowy = 1
        else:
            Weather_Windy = 1

        #--------Time of day encoding---------
        Time_of_Day_Afternoon=0
        Time_of_Day_Evening=0
        Time_of_Day_Morning=0
        Time_of_Day_Night=0

        if time == 'Morning':
            Time_of_Day_Morning=1
        elif time == 'Afternoon':
            Time_of_Day_Afternoon=1
        elif time == 'Evening':
            Time_of_Day_Evening=1
        else:
            Time_of_Day_Night=1
            
        #---------Vehicle type encoding------
        Vehicle_Type_Bike=0
        Vehicle_Type_Car=0
        Vehicle_Type_Scooter=0

        if vehicle == 'Bike':
            Vehicle_Type_Bike=1
        elif vehicle == 'Car':
            Vehicle_Type_Car=1
        else:
            Vehicle_Type_Scooter=1
            
        # ----------- Final Feature Vector ------------
        data = [[
            distance,
            t_level,
            p_time,
            experience,
            Weather_Clear,
            Weather_Foggy,
            Weather_Rainy,
            Weather_Snowy,
            Weather_Windy,
            Time_of_Day_Afternoon,
            Time_of_Day_Evening,
            Time_of_Day_Morning,
            Time_of_Day_Night,
            Vehicle_Type_Bike,
            Vehicle_Type_Car,
            Vehicle_Type_Scooter
        ]]

        # Convert to numpy
        data = np.array(data)

        # ----------- Prediction ------------
        prediction = model.predict(data)[0]
        prediction_text=f"Estimated delivery time: {round(prediction, 2)} minutes"
    return render_template('predict.html', prediction_text=prediction_text)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email format.', 'danger')
            return redirect(url_for('login'))   
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('login'))   

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['u_id']
            session['uname'] = user['uname']
            flash('Login successful.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))
        
    return render_template('login.html') 

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['uname']
        email = request.form['email']
        password = request.form['password']

        # Basic validation
        if not uname.strip():
            flash('Username is required.', 'danger')
            return redirect(url_for('register'))
        
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email format.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()

        #check existing email
        cursor.execute('SELECT u_id FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('Email already registered.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('register'))
        
        # Insert new user
        cursor.execute(
            'INSERT INTO users (uname, email, password) VALUES (%s, %s, %s)',
            (uname, email, hashed_password)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

if __name__=='__main__':
    app.run(debug=True, port=4000) #if you want to change the port number you can do it here
