from flask import Flask, request
import os
from sqlalchemy import create_engine
import mysql.connector
import urllib.parse
import face_recognition

app = Flask(__name__)

# Specify the upload folder path
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database configuration
DB_USERNAME = 'faresrahman'
DB_PASSWORD = 'Lead2024#'
DB_HOST = 'faresrahman.mysql.pythonanywhere-services.com'
DB_PORT = '3306'  # MySQL default port
DB_NAME = 'faresrahman$smart_attendance'

# Create the database connection
db_uri = f'mysql+pymysql://{urllib.parse.quote(DB_USERNAME)}:{urllib.parse.quote(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(db_uri)

def compare_faces(employee_name, unknown_name):
    try:
        employee_image = face_recognition.load_image_file(employee_name)
        employee_image_face_encoding = face_recognition.face_encodings(employee_image)[0]

        unknown_image = face_recognition.load_image_file(unknown_name)
        unknown_image_face_encoding = face_recognition.face_encodings(unknown_image)[0]

        results = face_recognition.compare_faces([employee_image_face_encoding], unknown_image_face_encoding)

        if results[0] == True:
            return "Match!"
        else:
            return "Not - match!"
    except Exception as e:
        print(f"Error loading images: {e}")
        return "Error loading images"

def get_image_path(employee_name):
    try:
        connection = mysql.connector.connect(
            user=DB_USERNAME,
            password=DB_PASSWORD,
            host=DB_HOST,
            database=DB_NAME
        )
        db_cursor = connection.cursor()
        db_cursor.execute("SELECT image_path FROM Attendance WHERE empl_name = %s", (employee_name,))
        result = db_cursor.fetchone()
        if result:
            image_path = result[0]
            if image_path:
                if os.path.isfile(image_path):
                    return image_path, True
                else:
                    return image_path, False
            else:
                return None, True
        else:
            return None, False
    except mysql.connector.Error as error:
        print(f"Error retrieving data from the database: {error}")
        return None, False
    finally:
        if 'connection' in locals():
            connection.close()

@app.route("/", methods=['GET', 'POST'])
def face_detect():
    # Test the database connection
    try:
        with engine.connect() as connection:
            connection.execute('SELECT 1')
        db_message = "Database connection successful"
    except Exception as e:
        db_message = f"Error connecting to database: {str(e)}"

    if request.method == 'GET':
        image_url = request.args.get('image')
        employee_name = request.args.get('employeeName')
        if image_url and employee_name:
            image_path, exists = get_image_path(employee_name)
            if image_path and exists:
                match_result = compare_faces(image_path, image_url)
                return f'Image and employee name received successfully<br>Database connection: {db_message}<br>Image path: {image_path}<br>Employee image found: {exists}<br>Face Comparison Result: {match_result}', 200
            elif image_path and not exists:
                return f'Image and employee name received successfully<br>Database connection: {db_message}<br>Image path: {image_path}<br>Employee image found: {exists}'
            elif not image_path and exists:
                return f'Image and employee name received successfully<br>Database connection: {db_message}<br>Image path: Null'
            elif not image_path and not exists:
                return f'Image and employee name received successfully<br>Database connection: {db_message}<br>Employee not in the list'
        elif image_url:
            return f'Image received, but employee name not provided<br>Database connection: {db_message}', 400
        elif employee_name:
            image_path, exists = get_image_path(employee_name)
            if image_path and exists:
                return f'Employee name received, but image not provided<br>Database connection: {db_message}<br>Image path: {image_path}<br>Employee image found: {exists}', 200
            elif image_path and not exists:
                return f'Employee name received, but image not provided<br>Database connection: {db_message}<br>Image path: {image_path}<br>Employee image found: {exists}'
            elif not image_path and exists:
                return f'Employee name received, but image not provided<br>Database connection: {db_message}<br>Image path: Null'
            elif not image_path and not exists:
                return f'Employee name received, but image not provided<br>Database connection: {db_message}<br>Employee not in the list'
        else:
            return f'Neither image nor employee name provided<br>Database connection: {db_message}', 400

    elif request.method == 'POST':
        if 'image' in request.files and 'employeeName' in request.form:
            image_file = request.files['image']
            employee_name = request.form['employeeName']

            # Ensure the upload folder exists
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            # Save the image file to the upload folder
            filename = f'{employee_name}.JPG'
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Insert into database
            try:
                with engine.connect() as connection:
                    connection.execute(
                        "INSERT INTO Attendance (empl_name, image_path) VALUES (%s, %s)",
                        (employee_name, filename)
                    )
                return f'Image and employee name received successfully!<br>Database connection: {db_message}', 200
            except Exception as e:
                return f'Error inserting data into the database: {e}<br>Database connection: {db_message}', 500
        elif 'image' in request.files:
            return f'Employee name not provided<br>Database connection: {db_message}', 400
        elif 'employeeName' in request.form:
            employee_name = request.form['employeeName']
            image_path, exists = get_image_path(employee_name)
            if exists:
                return f'Employee name received successfully!<br>Database connection: {db_message}<br>Image path: {image_path}<br>Employee image found: {exists}', 200
            else:
                return f'Employee name received, but image not provided<br>Database connection: {db_message}', 400
        else:
            return f'Neither image nor employee name received<br>Database connection: {db_message}', 400

if __name__ == '__main__':
    app.run(debug=True)

