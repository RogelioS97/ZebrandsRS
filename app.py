from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, IntegerField, PasswordField, RadioField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)


# Setup SQL
app.config['MYSQL_HOST'] = 'sql3.freemysqlhosting.net'
app.config['MYSQL_USER'] = 'sql3511651'
app.config['MYSQL_PASSWORD'] = 'NY5mXpJysP'
app.config['MYSQL_DB'] = 'sql3511651'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# Init MySQL
mysql = MySQL(app)

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Check if user logged in
def is_logged_in_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session['roleid'] == 1:
            return f(*args, **kwargs)
        else:
            flash('You are not authorized to access this source', 'danger')
            return redirect(url_for('index'))
    return wrap

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
@is_logged_in
def products():
	# Create cursor
    cur = mysql.connection.cursor()

    # Get Products
    result = cur.execute("SELECT * FROM products")

    products = cur.fetchall()

    if result > 0:
        return render_template('products.html', products=products)
    else:
        msg = 'No Products Found'
        return render_template('products.html', msg=msg)
    # Close connection
    cur.close()

@app.route('/product/<string:sku>/')
@is_logged_in
def product(sku):
	# Create cursor
    cur = mysql.connection.cursor()

    # Get Product
    result = cur.execute("SELECT * FROM products WHERE sku = %s", [sku])

    product = cur.fetchone()

    # Check if user_role == 2 the product views will increase, in case of user_role == 1, it will not increase

    if session['roleid'] == 2:

        views = product['views']

        views += 1

        # Execute Query to increase product views
        cur.execute("UPDATE products SET views=%s WHERE sku=%s",(views, sku))

        """ Execute Query to get the updated product with the first view
            Because with a newly created product, the first time it was queried
            The views would not refresh until querying again
        """
        result = cur.execute("SELECT * FROM products WHERE sku = %s", [sku])

        product = cur.fetchone()

        # Commit to DB
        mysql.connection.commit()

    return render_template('product.html', product=product)

class SignUpForm(Form):
    name = StringField('Name', [validators.DataRequired(), validators.Length(min=1, max=100)])
    username = StringField('Username', [validators.DataRequired(), validators.Length(min=4, max=50)])
    email = StringField('Email', [validators.DataRequired(), validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    role = RadioField('Role', choices=[(1, 'Admin'),(2, 'User')])
    confirm = PasswordField('Confirm Password')

# Product Form Class
class ProductForm(Form):
    name = StringField('Name', [validators.DataRequired(), validators.Length(min=6, max=100)])
    price = IntegerField('Price', [validators.DataRequired()])
    brand = StringField('Brand', [validators.DataRequired(), validators.Length(min=5, max=50)])

@app.route('/signup', methods=['GET','POST'])
def signup():
    form = SignUpForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        role = form.role.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password, roleid) VALUES(%s, %s, %s, %s, %s)", (name, email, username, password, role))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Thank you for signing up to Zebrands RS', 'success')

        return redirect(url_for('login'))

    return render_template('signup.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']
            role = data['roleid']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                session['roleid'] = role

                flash('You are now logged in', 'success')
                return redirect(url_for('products'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Logout
@app.route('/logout')
@is_logged_in
@is_logged_in_admin
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Add Product
@app.route('/add_product', methods=['GET', 'POST'])
@is_logged_in_admin
def add_product():
    form = ProductForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        price = form.price.data
        brand = form.brand.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO products(name, price, brand) VALUES(%s, %s, %s)",(name, price, brand))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Prodcut Created', 'success')

        return redirect(url_for('products'))

    return render_template('add_product.html', form=form)

# Edit Product
@app.route('/edit_product/<string:sku>', methods=['GET', 'POST'])
@is_logged_in_admin
def edit_product(sku):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get Product by id
    result = cur.execute("SELECT * FROM products WHERE sku = %s", [sku])

    product = cur.fetchone()
    cur.close()
    # Get form
    form = ProductForm(request.form)

    # Populate Product Form Fields
    form.name.data = product['name']
    form.brand.data = product['brand']
    form.price.data = product['price']

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        brand = request.form['brand']
        price = request.form['price']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(name)

        # Execute
        cur.execute ("UPDATE products SET name=%s, brand=%s, price=%s WHERE sku=%s",(name, brand, price, sku))
        
        # Commit to DB
        mysql.connection.commit()

        # Execute Query to insert modification into products_history table
        cur.execute ("INSERT INTO products_history (product_sku, user) VALUES(%s, %s)", (product['sku'], session['username']))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Product Updated', 'success')

        return redirect(url_for('products'))

    return render_template('edit_product.html', form=form)

# Delete Product
@app.route('/delete_product/<string:sku>', methods=['POST'])
@is_logged_in_admin
def delete_product(sku):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM products WHERE sku = %s", [sku])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Product Deleted', 'success')

    return redirect(url_for('products'))

@app.route('/users')
@is_logged_in_admin
def users():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get Admin Users
    result = cur.execute("SELECT * FROM users WHERE roleid = 1")

    users = cur.fetchall()

    if result > 0:
        return render_template('users.html', users=users)
    else:
        msg = 'No Users Found'
        return render_template('index.html', msg=msg)
    # Close connection
    cur.close()

# Edit User
@app.route('/edit_user/<string:id>', methods=['GET', 'POST'])
@is_logged_in_admin
def edit_user(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get User by id
    result = cur.execute("SELECT * FROM users WHERE id = %s", [id])

    user = cur.fetchone()
    cur.close()
    # Get form
    form = SignUpForm(request.form)

    # Populate Sign Up Form Fields
    form.name.data = user['name']
    form.email.data = user['email']
    form.username.data = user['username']

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = sha256_crypt.encrypt(str(request.form['password']))

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(name)

        # Execute
        cur.execute ("UPDATE users SET name=%s, email=%s, username=%s, password=%s WHERE id=%s",(name, email, username, password, id))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('User Updated', 'success')

        return redirect(url_for('users'))

    return render_template('edit_user.html', form=form)

# Delete User
@app.route('/delete_user/<string:id>', methods=['POST'])
@is_logged_in_admin
def delete_user(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM users WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('User Deleted', 'success')

    return redirect(url_for('users'))

@app.route('/logs')
@is_logged_in_admin
def logs():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get Products
    result = cur.execute("SELECT * FROM products_history")

    logs = cur.fetchall()

    if result > 0:
        return render_template('logs.html', logs=logs)
    else:
        msg = 'No Logs Found'
        return render_template('logs.html', msg=msg)
    # Close connection
    cur.close()


if __name__ == '__main__':
    app.secret_key='ZebrandsRS123'
    app.run(debug=True)
