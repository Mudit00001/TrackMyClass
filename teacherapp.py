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
    "Reports", "Students Remarks", "AI Insights"
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

# ---------- STUDENTS REMARKS ----------
elif choice == "Students Remarks":
    st.subheader("📝 Students Remarks (Class-wise)")

    students = pd.read_sql("SELECT * FROM students", conn)
    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        # Select Class
        classes_list = students['class_section'].dropna().map(str).str.strip().unique().tolist()
        classes_list = sorted(classes_list)
        selected_class = st.selectbox("Select Class/Section", ["All"] + classes_list)

        if selected_class != "All":
            filtered_students = students[students['class_section'].str.strip() == selected_class]
        else:
            filtered_students = students.copy()

        if filtered_students.empty:
            st.info(f"No students in Class/Section: {selected_class}.")
        else:
            st.write(f"### Students in Class/Section: {selected_class}")

            # Choose number of days to show remarks for
            num_days = st.number_input("Number of days to enter remarks", min_value=1, max_value=31, value=7)
            start_date = st.date_input("Start Date", date.today())

            date_list = [start_date + pd.Timedelta(days=i) for i in range(num_days)]

            for _, student in filtered_students.iterrows():
                st.markdown(f"**{student['name']}** (Roll: {student['roll_no']})")
                cols = st.columns(len(date_list))
                for i, d in enumerate(date_list):
                    # Generate a unique key for each student-date pair
                    remark_key = f"remark_{student['id']}_{d}"
                    existing_remark = pd.read_sql(
                        "SELECT remark FROM student_remarks WHERE student_id=? AND date=?", 
                        conn, params=(student['id'], str(d))
                    )
                    default_text = existing_remark['remark'][0] if not existing_remark.empty else ""
                    remark = cols[i].text_input(str(d), value=default_text, key=remark_key)
                    # Save/update remark immediately
                    if remark != default_text:
                        # Delete old remark if exists
                        c.execute("DELETE FROM student_remarks WHERE student_id=? AND date=?", (student['id'], str(d)))
                        c.execute("INSERT INTO student_remarks (student_id, date, remark) VALUES (?, ?, ?)", 
                                  (student['id'], str(d), remark))
                        conn.commit()
            st.success("✅ Remarks updated successfully!")

# ---------- AI INSIGHTS ----------
elif choice == "AI Insights":
    st.subheader("🤖 AI Insights - Class Summary (Mistral)")

    students = pd.read_sql("SELECT * FROM students", conn)

    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        # Select Class
        classes_list = students['class_section'].dropna().map(str).str.strip().unique().tolist()
        classes_list = sorted(classes_list)

        selected_class = st.selectbox("Select Class/Section", classes_list)

        start_date = st.date_input("Start Date", date.today())
        end_date = st.date_input("End Date", date.today())

        if st.button("🔍 Generate AI Summary"):
            # --- Attendance Data ---
            attendance_query = """
                SELECT s.name, s.roll_no, a.date, a.status
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE s.class_section=? AND date BETWEEN ? AND ?
                ORDER BY a.date
            """
            attendance_df = pd.read_sql(attendance_query, conn, params=(selected_class, str(start_date), str(end_date)))

            # --- Remarks Data ---
            remarks_query = """
                SELECT s.name, sr.date, sr.remark
                FROM student_remarks sr
                JOIN students s ON sr.student_id = s.id
                WHERE s.class_section=? AND date BETWEEN ? AND ?
            """
            remarks_df = pd.read_sql(remarks_query, conn, params=(selected_class, str(start_date), str(end_date)))

            # --- Notes Data ---
            notes_query = """
                SELECT s.name, act.date, act.note
                FROM activities act
                JOIN students s ON act.student_id = s.id
                WHERE s.class_section=? AND date BETWEEN ? AND ?
            """
            notes_df = pd.read_sql(notes_query, conn, params=(selected_class, str(start_date), str(end_date)))

            # --- Build context for AI ---
            summary_text = f"Class {selected_class} summary from {start_date} to {end_date}.\n\n"

            if not attendance_df.empty:
                summary_text += "📋 Attendance Records:\n"
                for _, row in attendance_df.iterrows():
                    summary_text += f"{row['date']}: {row['name']} - {row['status']}\n"
            if not remarks_df.empty:
                summary_text += "\n📝 Remarks:\n"
                for _, row in remarks_df.iterrows():
                    summary_text += f"{row['date']}: {row['name']} - {row['remark']}\n"
            if not notes_df.empty:
                summary_text += "\n📚 Activities/Notes:\n"
                for _, row in notes_df.iterrows():
                    summary_text += f"{row['date']}: {row['name']} - {row['note']}\n"

            # --- AI Summary using Ollama ---
            try:
                import ollama

                prompt = f"""
                You are an assistant helping a teacher.
                Summarize the following class data into a clear report:
                Attendance trends, key remarks, and daily notes.
                Be concise but insightful.

                Data:
                {summary_text}
                """

                response = ollama.chat(model="mistral", messages=[
                    {"role": "user", "content": prompt}
                ])

                ai_summary = response['message']['content']
                st.markdown("### 🤖 AI Generated Summary")
                st.info(ai_summary)

            except Exception as e:
                st.error(f"AI summary could not be generated: {e}")
                st.text_area("Raw data for manual review", summary_text, height=300)

# ---------- AI INSIGHTS ----------
elif choice == "AI Insights":
    st.subheader("🤖 AI Insights - Class Summary (Ollama)")

    students = pd.read_sql("SELECT * FROM students", conn)

    if students.empty:
        st.warning("No students found. Please add students first.")
    else:
        # Select Class
        classes_list = students['class_section'].dropna().map(str).str.strip().unique().tolist()
        classes_list = sorted(classes_list)

        selected_class = st.selectbox("Select Class/Section", classes_list)

        start_date = st.date_input("Start Date", date.today())
        end_date = st.date_input("End Date", date.today())

        if st.button("🔍 Generate AI Summary"):
            # --- Attendance Data ---
            attendance_query = """
                SELECT s.name, s.roll_no, a.date, a.status
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE s.class_section=? AND date BETWEEN ? AND ?
                ORDER BY a.date
            """
            attendance_df = pd.read_sql(attendance_query, conn, params=(selected_class, str(start_date), str(end_date)))

            # --- Remarks Data ---
            remarks_query = """
                SELECT s.name, sr.date, sr.remark
                FROM student_remarks sr
                JOIN students s ON sr.student_id = s.id
                WHERE s.class_section=? AND date BETWEEN ? AND ?
            """
            remarks_df = pd.read_sql(remarks_query, conn, params=(selected_class, str(start_date), str(end_date)))

            # --- Notes Data ---
            notes_query = """
                SELECT s.name, act.date, act.note
                FROM activities act
                JOIN students s ON act.student_id = s.id
                WHERE s.class_section=? AND date BETWEEN ? AND ?
            """
            notes_df = pd.read_sql(notes_query, conn, params=(selected_class, str(start_date), str(end_date)))

            # --- Build context for AI ---
            summary_text = f"Class {selected_class} summary from {start_date} to {end_date}.\n\n"

            if not attendance_df.empty:
                summary_text += "📋 Attendance Records:\n"
                for _, row in attendance_df.iterrows():
                    summary_text += f"{row['date']}: {row['name']} - {row['status']}\n"
            if not remarks_df.empty:
                summary_text += "\n📝 Remarks:\n"
                for _, row in remarks_df.iterrows():
                    summary_text += f"{row['date']}: {row['name']} - {row['remark']}\n"
            if not notes_df.empty:
                summary_text += "\n📚 Activities/Notes:\n"
                for _, row in notes_df.iterrows():
                    summary_text += f"{row['date']}: {row['name']} - {row['note']}\n"

            # --- AI Summary using Ollama ---
            try:
                import ollama

                prompt = f"""
                You are an assistant helping a teacher.
                Summarize the following class data into a clear report:
                - Attendance trends (who was frequently absent/present)
                - Key remarks/issues raised
                - Activities or notes worth highlighting
                - Provide an overall summary for the class teacher
                
                Important rule:-
                - Use ONLY the data provided below.
                - If no data is available for a section, explicitly say: "No records available".
                - Do NOT invent or assume extra details.

                Data:
                {summary_text}
                """

                response = ollama.chat(
                    model="mistral",   # or "gemma:2b" if you prefer
                    messages=[{"role": "user", "content": prompt}]
                )

                ai_summary = response["message"]["content"]
                st.markdown("### 🤖 AI Generated Summary")
                st.info(ai_summary)

            except Exception as e:
                st.error(f"AI summary could not be generated: {e}")
                st.text_area("Raw data for manual review", summary_text, height=300)




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
