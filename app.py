from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    passwd=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')
    
@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/availability')
def availability():
    return render_template('availability.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    cursor = db.cursor()

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        sql = """
        SELECT role FROM users
        WHERE username=%s AND password=%s
        """

        cursor.execute(sql, (username, password))

        user = cursor.fetchone()

        if user and user[0] == 'customer':

            session['username'] = username
            session['role'] = 'customer'

            return redirect('/request')

        return "Invalid Customer Credentials"

    return render_template('login.html')

@app.route('/login2', methods=['GET', 'POST'])
def login2():

    cursor = db.cursor()   

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        sql = """
        SELECT role FROM users
        WHERE username=%s AND password=%s
        """

        cursor.execute(sql, (username, password))
        user = cursor.fetchone()

        if user and user[0] == 'admin':
            session['username'] = username
            session['role'] = 'admin'
            return redirect('/admin/dashboard')

        return "Invalid Admin Credentials"

    return render_template('login2.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
     
     cursor = db.cursor()  

     if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        sql = """
        INSERT INTO users (username, password, role)
        VALUES (%s, %s, %s)
        """

        cursor.execute(sql, (username, password, 'customer'))
        db.commit()

        return redirect('/login')

     return render_template('register.html')

@app.route('/request', methods=['GET', 'POST'])
def request_page():

    cursor = db.cursor()

    if 'role' not in session:
        return redirect('/login')

    if session['role'] != 'customer':
        return redirect('/login')

    if request.method == 'POST':

        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        machine_type = request.form['machine_type']
        problem = request.form['problem']
        preferred_date = request.form['preferred_date']

        customer_sql = """
        INSERT INTO customers (name, phone, address)
        VALUES (%s, %s, %s)
        """

        cursor.execute(customer_sql, (name, phone, address))
        db.commit()

        customer_id = cursor.lastrowid

        repair_sql = """
        INSERT INTO repair_requests
        (customer_id, machine_type, problem, status, preferred_date)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(
            repair_sql,
            (
                customer_id,
                machine_type,
                problem,
                'Pending',
                preferred_date
            )
        )

        db.commit()

        return "Request Submitted Successfully"

    return render_template('request.html')

@app.route('/admin')
def admin():
    if 'role' not in session:
     return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')

    return redirect('/admin/dashboard')
@app.route('/admin/dashboard')
def admin_dashboard():

    if 'role' not in session:
        return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            repair_requests.id,
            customers.name,
            repair_requests.machine_type,
            repair_requests.status

        FROM repair_requests

        JOIN customers
        ON customers.id = repair_requests.customer_id

        ORDER BY
        CASE
            WHEN repair_requests.status='Pending' THEN 1
            WHEN repair_requests.status='Assigned' THEN 2
            WHEN repair_requests.status='In Progress' THEN 3
            WHEN repair_requests.status='Completed' THEN 4
        END,
        repair_requests.id DESC
    """)

    recent_requests = cursor.fetchall()

    count_cursor = db.cursor()

    count_cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = count_cursor.fetchone()[0]

    count_cursor.execute("""
        SELECT COUNT(*)
        FROM repair_requests
        WHERE status='Pending'
    """)
    pending = count_cursor.fetchone()[0]

    count_cursor.execute("""
        SELECT COUNT(*)
        FROM repair_requests
        WHERE status='Completed'
    """)
    completed = count_cursor.fetchone()[0]

    count_cursor.execute("SELECT COUNT(*) FROM workers")
    workers = count_cursor.fetchone()[0]

    return render_template(
        'admin_dashboard.html',
        total_customers=total_customers,
        pending=pending,
        completed=completed,
        workers=workers,
        recent_requests=recent_requests
    )

@app.route('/admin/requests')
def admin_requests():

    if 'role' not in session:
        return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')
   
    search = request.args.get('search', '')
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            repair_requests.id,
            customers.name,
            customers.phone,
            repair_requests.machine_type,
            repair_requests.problem,
            repair_requests.status

        FROM repair_requests

        JOIN customers
        ON customers.id = repair_requests.customer_id
        WHERE customers.name LIKE %s
                

        ORDER BY
        CASE
            WHEN repair_requests.status='Pending' THEN 1
            WHEN repair_requests.status='Assigned' THEN 2
            WHEN repair_requests.status='In Progress' THEN 3
            WHEN repair_requests.status='Completed' THEN 4
        END,
        repair_requests.id DESC
    """, ('%' + search + '%',))

    requests = cursor.fetchall()

    return render_template(
        'admin_requests.html',
        requests=requests
    )   
    
@app.route('/assign_worker/<int:id>', methods=['GET','POST'])
def assign_worker(id):

    if 'role' not in session:
        return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')

    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':

        worker_id = request.form['worker_id']

        cursor.execute("""
            UPDATE repair_requests
            SET worker_id=%s,
                status='Assigned'
            WHERE id=%s
        """, (worker_id, id))

        db.commit()

        return redirect('/admin/requests')

    cursor.execute("SELECT * FROM workers")

    workers = cursor.fetchall()

    return render_template(
        'assign_worker.html',
        workers=workers
    )
@app.route('/admin/workers')
def admin_workers():

    if 'role' not in session:
        return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM workers")

    workers = cursor.fetchall()

    return render_template(
        'admin_workers.html',
        workers=workers
    )
@app.route('/admin/add_worker', methods=['GET', 'POST'])
def add_worker():

    if 'role' not in session:
        return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')

    if request.method == 'POST':

        name = request.form['name']
        phone = request.form['phone']

        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO workers(name, phone)
            VALUES(%s, %s)
        """, (name, phone))

        db.commit()

        return redirect('/admin/workers')

    return render_template('add_worker.html')

@app.route('/delete_worker/<int:id>')
def delete_worker(id):

    if 'role' not in session:
        return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')

    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM workers WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect('/admin/workers')


@app.route('/update_status/<int:id>/<status>')
def update_status(id, status):

    if 'role' not in session:
        return redirect('/login2')

    if session['role'] != 'admin':
        return redirect('/login2')

    cursor = db.cursor()

    cursor.execute("""
        UPDATE repair_requests
        SET status=%s
        WHERE id=%s
    """, (status, id))

    db.commit()

    return redirect('/admin/requests')

@app.route('/my_requests')
def my_requests():

    if 'role' not in session:
        return redirect('/login')

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            repair_requests.id,
            repair_requests.machine_type,
            repair_requests.problem,
            repair_requests.status
        FROM repair_requests
        JOIN customers
        ON customers.id = repair_requests.customer_id
        ORDER BY repair_requests.id DESC
    """)

    requests = cursor.fetchall()

    return render_template(
        'my_requests.html',
        requests=requests
    )

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

 
# ---------------- RUN APP ----------------

if __name__ == '__main__':
    app.run()
