from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'f9b3c6e4a2071a6d3c1e7ef7c4d37f0e'  # Replace with your secret key

# Configure MySQL
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'freshbasket'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password using Scrypt
        hashed_password = generate_password_hash(password, method='scrypt')

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE name LIKE %s", ('%' + query + '%',))
    results = cur.fetchall()
    cur.close()
    return render_template('search_results.html', results=results)

@app.route('/orders')
def orders():
    if 'username' in session:
        username = session['username']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM purchases WHERE username = %s", (username,))
        orders = cur.fetchall()
        cur.close()
        return render_template('index.html', orders=orders)
    else:
        flash('Please log in to view your orders.', 'warning')
        return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        order_id = request.form['order_id']
        status = request.form['status']
        
        cur = mysql.connection.cursor()
        cur.execute("UPDATE purchases SET status = %s WHERE id = %s", (status, order_id))
        mysql.connection.commit()
        cur.close()
        flash(f"Order {order_id} updated to '{status}'", 'success')
        return redirect(url_for('admin'))

    # Fetch all orders for the admin view
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM purchases")
    orders = cur.fetchall()
    cur.close()
    return render_template('admin.html', orders=orders)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):  # Assuming password is in the third column
            session['username'] = username
            flash('Login successful!', 'success')  # Flash a success message
            return redirect(url_for('index'))  # Redirect to the index route on successful login
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/cart', methods=['GET'])
def cart():
    if 'username' in session:
        return render_template('cart.html')  # Render the cart.html template
    else:
        flash('Please log in to view your cart.', 'warning')
        return redirect(url_for('home'))

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'username' not in session:
        flash('Please log in to checkout.', 'warning')
        return redirect(url_for('home'))

    # Get cart data from the request
    cart = request.json.get('cart')

    if not cart:
        flash('Your cart is empty.', 'warning')
        return jsonify({'message': 'No items in cart'}), 400  # Return 400 Bad Request if the cart is empty

    username = session['username']
    total_price = 0.0
    
    cur = mysql.connection.cursor()

    # Insert each item in the cart into the purchases table
    try:
        for item in cart:
            product_name = item.get('name')
            product_price = item.get('price')
            quantity = 1  # Set quantity to 1 as per requirement
            
            # Check for None values
            if not product_name or product_price is None:
                flash('Invalid product data. Please check your cart.', 'danger')
                return jsonify({'message': 'Invalid product data'}), 400  # Bad Request
            
            # Calculate total price
            total_price += product_price * quantity
            
            cur.execute(""" 
                INSERT INTO purchases (username, product_name, product_price, quantity) 
                VALUES (%s, %s, %s, %s)
            """, (username, product_name, product_price, quantity))

        mysql.connection.commit()
        flash(f'Order placed successfully! Total amount: ${total_price:.2f}', 'success')

    except Exception as e:
        mysql.connection.rollback()  # Rollback in case of an error
        flash('An error occurred while placing your order. Please try again.', 'danger')
        print(f"Error: {e}")  # Print the detailed error message for debugging
        return jsonify({'message': 'Order placement failed'}), 500  # Return 500 Internal Server Error on failure

    finally:
        cur.close()

    return jsonify({'message': 'Order placed successfully!', 'total_price': total_price}), 200

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
