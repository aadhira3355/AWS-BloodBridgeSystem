from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector.pooling
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a strong secret key for production.

# Database configuration
db_config = {
    "host": "bloodbank-db1.c72yiiqas52k.ap-south-1.rds.amazonaws.com",
    "user": "admin",  # Replace with your RDS master username.
    "password": "Z3phyr_9!",  # Replace with your RDS master password.
    "database": "blood_bank",  # Replace with your database name.
}

# Create a connection pool
db_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **db_config)


def get_db_connection():
    return db_pool.get_connection()


# Test database connection
@app.route('/test-db-connection')
def test_db_connection():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()[0]
        return f"Connected to database: {db_name}"
    except Exception as e:
        return f"Error: {e}"
    finally:
        if connection:
            connection.close()


# Home route
@app.route('/')
def index():
    return render_template("index.html")


# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        blood_type = request.form['blood_type']  # Ensure blood_type is received correctly

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Check if email already exists
            cursor.execute("SELECT * FROM register WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered. Please log in.")
                return redirect('/login')

            # Insert new user
            cursor.execute("INSERT INTO register (fullname, email, password, blood_type) VALUES (%s, %s, %s, %s)",
                           (fullname, email, password, blood_type))
            connection.commit()

            # Store user in session
            session['user'] = {"email": email, "fullname": fullname, "blood_type": blood_type}
            flash("Registration successful!")
            return redirect('/dashboard')
        except Exception as e:
            connection.rollback()
            flash(f"Error: {e}")
        finally:
            cursor.close()
            connection.close()

    return render_template("register.html")


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT * FROM register WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()
            if user:
                session['user'] = {
                    "email": user[2],  # Assuming email is the 3rd column (index 2)
                    "fullname": user[1],  # Assuming fullname is the 2nd column (index 1)
                    "blood_type": user[4]  # Assuming blood_type is the 5th column (index 4)
                }
                return redirect('/dashboard')
            else:
                flash("Invalid email or password.")
        finally:
            cursor.close()
            connection.close()

    return render_template("login.html")


# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please log in to access the dashboard.")
        return redirect('/login')

    print(session['user'])  # Debugging line to check session data

    user = session['user']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT fullname, email, blood_type FROM register WHERE email = %s", (user['email'],))
        user_data = cursor.fetchone()

        cursor.execute("SELECT * FROM request WHERE blood_type = %s AND status = 'pending'", (user['blood_type'],))
        blood_requests = cursor.fetchall()

        return render_template("dashboard.html", user=user_data, requests=blood_requests)
    finally:
        cursor.close()
        connection.close()


# Blood request submission
@app.route('/request', methods=['GET', 'POST'])
def request_blood():
    if 'user' not in session:
        flash("Please log in to make a request.")
        return redirect('/login')

    if request.method == 'POST':
        location = request.form['location']
        blood_type = request.form['blood_type']
        urgency = request.form['urgency']
        user = session['user']

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT id FROM register WHERE email = %s", (user['email'],))
            requester_id = cursor.fetchone()[0]

            cursor.execute("INSERT INTO request (requester_id, location, blood_type, urgency, status) VALUES (%s, %s, %s, %s, 'pending')",
                           (requester_id, location, blood_type, urgency))
            connection.commit()

            flash("Blood request submitted successfully!")
            return redirect('/dashboard')
        except Exception as e:
            connection.rollback()
            flash(f"Error: {e}")
        finally:
            cursor.close()
            connection.close()

    return render_template("request.html")


# Respond to a blood request
@app.route('/respond/<int:request_id>/<int:requester_id>')
def respond(request_id, requester_id):
    if 'user' not in session:
        flash("Please log in to respond to a request.")
        return redirect('/login')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM request WHERE id = %s", (request_id,))
        request_data = cursor.fetchone()

        cursor.execute("SELECT * FROM register WHERE id = %s", (requester_id,))
        requester_data = cursor.fetchone()

        return render_template("respond.html", request=request_data, requester=requester_data)
    finally:
        cursor.close()
        connection.close()


# Confirm blood donation
@app.route('/donate-blood/<int:request_id>')
def donate_blood(request_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("UPDATE request SET status = 'donated' WHERE id = %s", (request_id,))
        connection.commit()
        flash("Donation confirmed. Thank you!")
        return redirect('/dashboard')
    except Exception as e:
        connection.rollback()
        flash(f"Error: {e}")
    finally:
        cursor.close()
        connection.close()
@app.route('/logout')
def logout():
    # Remove the user from the session
    session.pop('user', None)
    flash("You have been logged out.")
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
