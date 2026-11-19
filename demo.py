from attendance_chain import AttendanceChain

chain = AttendanceChain()

print("Records before:", chain.get_record_count())

tx = chain.mark_attendance("STU-001")
print("Written, tx hash:", tx)

chain.mark_attendance("STU-002")

for r in chain.get_records():
    print(r["index"], r["member_id"], r["time"])