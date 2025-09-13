import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect("students.db", check_same_thread=False)
c = conn.cursor()

# Ensure schema includes all necessary columns
c.execute('''CREATE TABLE IF NOT EXISTS students 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              name TEXT, roll_no TEXT, class_section TEXT,
              father_name TEXT, contact TEXT, photo TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS student_remarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                date TEXT,
                remark TEXT,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS attendance 
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              student_id INTEGER, date TEXT, status TEXT,
              FOREIGN KEY(student_id) REFERENCES students(id))''')

c.execute('''CREATE TABLE IF NOT EXISTS activities 
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              student_id INTEGER, date TEXT, note TEXT,
              FOREIGN KEY(student_id) REFERENCES students(id))''')
conn.commit()

# ---------- APP ----------
st.set_page_config(page_title="Teacher Monitoring App", layout="wide")
st.title("📚 Teacher Daily Activity Monitoring")

menu = [
    "Students by Class-Section",
    "Manage Students",
    "Upload Students List",
    "Mark Attendance",
    "Class Attendance Overview",
    "Daily Notes",
    "Reports", "Students Remarks"
]
choice = st.sidebar.selectbox("Menu", menu)

# ---------- MANAGE STUDENTS ----------
if choice == "Manage Students":
    st.subheader("👩‍🎓 Manage Students")

    # Add Student
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Student Name")
        roll_no = st.text_input("Roll No")
        class_section = st.text_input("Class/Section")
        father_name = st.text_input("Father's Name")
        contact = st.text_input("Contact")
        photo = st.text_input("Photo Path (optional)")
        submitted = st.form_submit_button("➕ Add Student")
        if submitted and name and roll_no and class_section:
            c.execute("INSERT INTO students (name, roll_no, class_section, father_name, contact, photo) VALUES (?, ?, ?, ?, ?, ?)", 
                      (name, roll_no, class_section, father_name, contact, photo))
            conn.commit()
            st.success(f"✅ {name} added successfully!")

    students = pd.read_sql("SELECT * FROM students", conn)

    if not students.empty:
        st.write("### 📋 Students List")
        st.dataframe(students)

        sid = st.selectbox("Select a student to Edit/Delete", students['id'])
        student_row = students[students['id']==sid].iloc[0]

        # Edit Student
        with st.form("edit_form"):
            new_name = st.text_input("Name", str(student_row.get('name', "")))
            new_roll = st.text_input("Roll No", str(student_row.get('roll_no', "")))
            new_class = st.text_input("Class/Section", str(student_row.get('class_section', "")))
            new_father = st.text_input("Father’s Name", str(student_row.get('father_name', "")))
            new_contact = st.text_input("Contact", str(student_row.get('contact', "")))
            new_photo = st.text_input("Photo Path", str(student_row.get('photo', "")))

            update = st.form_submit_button("💾 Update Student")
            if update:
                c.execute("""
                    UPDATE students 
                    SET name=?, roll_no=?, class_section=?, father_name=?, contact=?, photo=? 
                    WHERE id=?
                """, (
                    new_name.strip(),
                    new_roll.strip(),
                    new_class.strip(),
                    new_father.strip(),
                    new_contact.strip(),
                    new_photo.strip(),
                    sid
                ))
                conn.commit()
                st.success(f"✅ {new_name} updated successfully!")

        # Delete Student
        if st.button("🗑️ Delete Student"):
            c.execute("DELETE FROM attendance WHERE student_id=?", (sid,))
            c.execute("DELETE FROM activities WHERE student_id=?", (sid,))
            c.execute("DELETE FROM students WHERE id=?", (sid,))
            conn.commit()
            st.warning("❌ Student deleted successfully! Refresh to update list.")

    else:
        st.info("No students added yet. Use the form above to add.")

# ---------- UPLOAD STUDENTS LIST ----------
elif choice == "Upload Students List":
    st.subheader("📤 Upload Students (CSV or Excel)")

    st.markdown("""
    **Required columns:**  
    - name  
    - roll_no  
    - class_section  
    **Optional:** father_name, contact, photo  
    """)

    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.write("Preview of uploaded file:")
            st.dataframe(df.head())

            required_cols = {"name", "roll_no", "class_section"}
            if not required_cols.issubset(df.columns):
                st.error(f"Missing required columns! Required: {required_cols}")
            else:
                if st.button("💾 Save to Database"):
                    for _, row in df.iterrows():
                        c.execute("""
                            INSERT INTO students (name, roll_no, class_section, father_name, contact, photo)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            str(row.get("name", "")),
                            str(row.get("roll_no", "")),
                            str(row.get("class_section", "")),
                            str(row.get("father_name", "")) if "father_name" in df else "",
                            str(row.get("contact", "")) if "contact" in df else "",
                            str(row.get("photo", "")) if "photo" in df else ""
                        ))
                    conn.commit()
                    st.success("✅ Students uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

# ---------- MARK ATTENDANCE ----------
elif choice == "Mark Attendance":
    st.subheader("📋 Mark Attendance")
    today = str(date.today())

    # Get all students
    students = pd.read_sql("SELECT * FROM students", conn)

    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        # Get distinct class/section
        classes = students['class_section'].dropna().map(str).str.strip().unique().tolist()
        classes = sorted(classes)

        # Select class
        selected_class = st.selectbox("Select Class/Section", options=classes)

        # Filter students for this class
        class_students = students[students['class_section'].str.strip() == selected_class]

        if class_students.empty:
            st.info(f"No students in Class/Section: {selected_class}.")
        else:
            with st.form("attendance_form"):
                status_dict = {}
                for _, student in class_students.iterrows():
                    status = st.radio(
                        f"{student['name']} (Roll: {student['roll_no']})",
                        ["Present", "Absent"],
                        key=f"att_{student['id']}_{today}"
                    )
                    status_dict[student['id']] = status

                save_att = st.form_submit_button("💾 Save Attendance")
                if save_att:
                    for sid, status in status_dict.items():
                        # Prevent duplicate entries for same date
                        c.execute("DELETE FROM attendance WHERE student_id=? AND date=?", (sid, today))
                        c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", 
                                  (sid, today, status))
                    conn.commit()
                    st.success(f"✅ Attendance saved for Class {selected_class} on {today}!")


# ---------- CLASS ATTENDANCE OVERVIEW ----------
elif choice == "Class Attendance Overview":
    st.subheader("🏫 Class & Section Attendance Overview")

    classes = pd.read_sql("SELECT DISTINCT class_section FROM students", conn)
    if classes.empty:
        st.warning("No classes found. Please add students first.")
    else:
        selected_class = st.selectbox("Select Class/Section", classes['class_section'])
        students = pd.read_sql(f"SELECT * FROM students WHERE class_section='{selected_class}'", conn)

        if students.empty:
            st.info("No students in this class.")
        else:
            records = []
            for _, student in students.iterrows():
                total_days = pd.read_sql(
                    f"SELECT COUNT(*) as cnt FROM attendance WHERE student_id={student['id']}", conn
                )['cnt'][0]
                present_days = pd.read_sql(
                    f"SELECT COUNT(*) as cnt FROM attendance WHERE student_id={student['id']} AND status='Present'", conn
                )['cnt'][0]

                attendance_pct = round((present_days / total_days) * 100, 2) if total_days > 0 else 0
                records.append({
                    "Name": student['name'],
                    "Roll No": student['roll_no'],
                    "Total Days": total_days,
                    "Present": present_days,
                    "Attendance %": attendance_pct
                })

            df = pd.DataFrame(records)
            st.dataframe(df)

            low_attendance = df[df['Attendance %'] < 75]
            if not low_attendance.empty:
                st.warning("⚠️ Students below 75% attendance:")
                st.dataframe(low_attendance)

            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.bar(df["Name"], df["Attendance %"])
            ax.set_ylabel("Attendance %")
            ax.set_title(f"Attendance % for Class {selected_class}")
            ax.tick_params(axis='x', rotation=45)
            st.pyplot(fig)

# ---------- STUDENTS BY CLASS/SECTION ----------
elif choice == "Students by Class-Section":
    st.subheader("👩‍🏫 Students by Class/Section")

    students = pd.read_sql("SELECT * FROM students", conn)

    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        classes_list = students['class_section'].dropna().map(str).str.strip().unique().tolist()
        classes_list = sorted(classes_list)

        selected_class = st.selectbox("Select Class/Section", options=["All"] + classes_list)

        if selected_class != "All":
            filtered_students = students[students['class_section'].str.strip() == selected_class]
        else:
            filtered_students = students.copy()

        if filtered_students.empty:
            st.info(f"No students found in Class/Section: {selected_class}.")
        else:
            st.write(f"### Students in Class/Section: {selected_class}")
            st.dataframe(
                filtered_students[['name', 'roll_no', 'father_name', 'contact', 'photo', 'class_section']],
                use_container_width=True
            )

            for _, row in filtered_students.iterrows():
                col1, col2 = st.columns([1, 3])
                with col1:
                    if row['photo']:
                        try:
                            st.image(row['photo'], width=80)
                        except:
                            st.text("No photo")
                with col2:
                    st.markdown(f"**{row['name']}** (Roll: {row['roll_no']})")
                    st.text(f"Father: {row['father_name']}")
                    st.text(f"Contact: {row['contact']}")
            st.divider()

# ---------- DAILY NOTES ----------
elif choice == "Daily Notes":
    st.subheader("📝 Add Daily Notes")
    students = pd.read_sql("SELECT * FROM students", conn)
    today = str(date.today())

    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        student = st.selectbox("Select Student", students['name'])
        note = st.text_area("Enter activity/note")
        if st.button("💾 Save Note"):
            sid = students[students['name']==student]['id'].values[0]
            c.execute("INSERT INTO activities (student_id, date, note) VALUES (?, ?, ?)", 
                      (sid, today, note))
            conn.commit()
            st.success(f"✅ Note saved for {student}")

# ---------- STUDENT REMARKS ----------
elif choice == "Student Remarks":
    st.subheader("📝 Student Remarks Tracker")

    # Select class/section
    students = pd.read_sql("SELECT * FROM students", conn)
    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        classes_list = students['class_section'].dropna().map(str).str.strip().unique().tolist()
        classes_list = sorted(classes_list)

        selected_class = st.selectbox("Select Class/Section", classes_list)

        # Filter students
        class_students = students[students['class_section'].str.strip() == selected_class]

        if class_students.empty:
            st.info("No students in this class.")
        else:
            # Let teacher pick date range
            start_date = st.date_input("Start Date", date.today())
            end_date = st.date_input("End Date", date.today())

            if start_date > end_date:
                st.error("Start date cannot be after end date.")
            else:
                # Generate list of dates
                date_list = pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()

                st.write("### Enter remarks for each student")

                # Form to submit all remarks at once
                with st.form("remarks_form"):
                    remarks_data = {}
                    for _, student in class_students.iterrows():
                        st.markdown(f"**{student['name']} (Roll: {student['roll_no']})**")
                        student_remarks = {}
                        for d in date_list:
                            # Check if remark already exists
                            existing = pd.read_sql(
                                f"SELECT remark FROM student_remarks WHERE student_id={student['id']} AND date='{d}'",
                                conn
                            )
                            existing_remark = existing['remark'][0] if not existing.empty else ""
                            student_remarks[d] = st.text_input(f"Remark for {d}", value=existing_remark, key=f"{student['id']}_{d}")
                        remarks_data[student['id']] = student_remarks
                        st.divider()

                    save_remarks = st.form_submit_button("💾 Save Remarks")
                    if save_remarks:
                        for sid, dates_dict in remarks_data.items():
                            for d, remark in dates_dict.items():
                                # Delete old entry
                                c.execute("DELETE FROM student_remarks WHERE student_id=? AND date=?", (sid, d))
                                if remark.strip():  # only save if remark is not empty
                                    c.execute("INSERT INTO student_remarks (student_id, date, remark) VALUES (?, ?, ?)", (sid, d, remark.strip()))
                        conn.commit()
                        st.success("✅ Remarks saved successfully!")


# ---------- REPORTS ----------
elif choice == "Reports":
    st.subheader("📊 Reports")
    students = pd.read_sql("SELECT * FROM students", conn)

    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        student = st.selectbox("Select Student", students['name'])
        if student:
            sid = students[students['name']==student]['id'].values[0]

            st.write("### Attendance Record")
            attendance = pd.read_sql(f"SELECT date, status FROM attendance WHERE student_id={sid}", conn)
            st.dataframe(attendance)

            st.write("### Daily Notes")
            notes = pd.read_sql(f"SELECT date, note FROM activities WHERE student_id={sid}", conn)
            st.dataframe(notes)
