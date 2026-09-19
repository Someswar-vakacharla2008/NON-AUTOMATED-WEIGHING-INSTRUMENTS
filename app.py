from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

app = Flask(__name__)

DATABASE = "database.db"
REPORT_FOLDER = "reports"

os.makedirs(REPORT_FOLDER, exist_ok=True)


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer TEXT,
            model TEXT,
            serial_no TEXT,
            capacity REAL,
            min_capacity REAL,
            accuracy_class TEXT,
            test_load REAL,
            indicated_value REAL,
            error REAL,
            mpe REAL,
            result TEXT,
            test_date TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------- MPE CALCULATION ----------------

def calculate_mpe(load, accuracy_class):

    # Simplified prototype implementation.
    # Final production implementation should incorporate
    # the complete applicable OIML R 76 provisions.

    if accuracy_class == "I":
        mpe = load * 0.5 / 100

    elif accuracy_class == "II":
        mpe = load * 1.0 / 100

    elif accuracy_class == "III":
        mpe = load * 1.5 / 100

    elif accuracy_class == "IIII":
        mpe = load * 2.0 / 100

    else:
        mpe = load * 1.5 / 100

    return round(mpe, 3)


# ---------------- HOME ----------------

@app.route("/")
def index():

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM tests"
    ).fetchone()[0]

    passed = conn.execute(
        "SELECT COUNT(*) FROM tests WHERE result='PASS'"
    ).fetchone()[0]

    failed = conn.execute(
        "SELECT COUNT(*) FROM tests WHERE result='FAIL'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total=total,
        passed=passed,
        failed=failed
    )


# ---------------- NEW TEST ----------------

@app.route("/new-test")
def new_test():

    return render_template("new_test.html")


# ---------------- PROCESS TEST ----------------

@app.route("/calculate", methods=["POST"])
def calculate():

    manufacturer = request.form["manufacturer"]
    model = request.form["model"]
    serial_no = request.form["serial_no"]

    capacity = float(request.form["capacity"])
    min_capacity = float(request.form["min_capacity"])

    accuracy_class = request.form["accuracy_class"]

    test_load = float(request.form["test_load"])
    indicated_value = float(request.form["indicated_value"])

    test_date = request.form["test_date"]

    # Error

    error = indicated_value - test_load

    # MPE

    mpe = calculate_mpe(test_load, accuracy_class)

    # Pass / Fail

    if abs(error) <= mpe:
        result = "PASS"
    else:
        result = "FAIL"

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO tests
        (
            manufacturer,
            model,
            serial_no,
            capacity,
            min_capacity,
            accuracy_class,
            test_load,
            indicated_value,
            error,
            mpe,
            result,
            test_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        manufacturer,
        model,
        serial_no,
        capacity,
        min_capacity,
        accuracy_class,
        test_load,
        indicated_value,
        error,
        mpe,
        result,
        test_date
    ))

    test_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return redirect(url_for("result", test_id=test_id))


# ---------------- RESULT ----------------

@app.route("/result/<int:test_id>")
def result(test_id):

    conn = get_db()

    test = conn.execute(
        "SELECT * FROM tests WHERE id=?",
        (test_id,)
    ).fetchone()

    conn.close()

    if test is None:
        return "Test not found"

    return render_template(
        "result.html",
        test=test
    )


# ---------------- HISTORY ----------------

@app.route("/history")
def history():

    conn = get_db()

    tests = conn.execute(
        "SELECT * FROM tests ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "history.html",
        tests=tests
    )


# ---------------- PDF REPORT ----------------

@app.route("/generate-report/<int:test_id>")
def generate_report(test_id):

    conn = get_db()

    test = conn.execute(
        "SELECT * FROM tests WHERE id=?",
        (test_id,)
    ).fetchone()

    conn.close()

    if test is None:
        return "Test not found"

    filename = f"NAWI_Test_Report_{test_id}.pdf"

    filepath = os.path.join(
        REPORT_FOLDER,
        filename
    )

    pdf = canvas.Canvas(
        filepath,
        pagesize=A4
    )

    width, height = A4

    # Header

    pdf.setFont("Helvetica-Bold", 18)

    pdf.drawCentredString(
        width / 2,
        height - 50,
        "NAWI TEST REPORT"
    )

    pdf.setFont("Helvetica", 10)

    pdf.drawCentredString(
        width / 2,
        height - 68,
        "Non-Automatic Weighing Instrument"
    )

    pdf.line(
        50,
        height - 80,
        width - 50,
        height - 80
    )

    y = height - 120

    # Instrument details

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(
        50,
        y,
        "Instrument Details"
    )

    y -= 25

    pdf.setFont("Helvetica", 10)

    details = [
        ("Manufacturer", test["manufacturer"]),
        ("Model", test["model"]),
        ("Serial Number", test["serial_no"]),
        ("Maximum Capacity", f'{test["capacity"]} kg'),
        ("Minimum Capacity", f'{test["min_capacity"]} kg'),
        ("Accuracy Class", test["accuracy_class"]),
        ("Test Date", test["test_date"])
    ]

    for label, value in details:

        pdf.drawString(
            60,
            y,
            f"{label}: {value}"
        )

        y -= 20

    y -= 10

    # Test results

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(
        50,
        y,
        "Test Results"
    )

    y -= 30

    pdf.setFont("Helvetica", 10)

    results = [
        ("Test Load", f'{test["test_load"]} kg'),
        ("Indicated Value", f'{test["indicated_value"]} kg'),
        ("Error", f'{test["error"]} kg'),
        ("Maximum Permissible Error", f'{test["mpe"]} kg')
    ]

    for label, value in results:

        pdf.drawString(
            60,
            y,
            f"{label}: {value}"
        )

        y -= 20

    y -= 15

    # Result

    pdf.setFont("Helvetica-Bold", 14)

    if test["result"] == "PASS":
        pdf.drawString(
            60,
            y,
            "FINAL RESULT: PASS"
        )
    else:
        pdf.drawString(
            60,
            y,
            "FINAL RESULT: FAIL"
        )

    y -= 50

    pdf.setFont("Helvetica", 9)

    pdf.drawString(
        50,
        y,
        "Reference: OIML Recommendation R 76"
    )

    y -= 15

    pdf.drawString(
        50,
        y,
        "This report is generated by the NAWI Test Report System."
    )

    pdf.save()

    return send_file(
        filepath,
        as_attachment=True
    )


# ---------------- RUN ----------------

if __name__ == "__main__":

    create_database()

    app.run(
        debug=True
    )