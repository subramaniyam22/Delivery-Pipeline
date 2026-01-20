
with open('backend/app/models.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Keep lines until the end of the correct ChatLog definition
# The correct definition ends around line 1058 (including blank lines)
# We can search for the line "    project = relationship(\"Project\", backref=\"chat_logs\")"
# and keep one or two empty lines after it.

clean_lines = []
found_chatlog = False
for line in lines:
    clean_lines.append(line)
    if 'project = relationship("Project", backref="chat_logs")' in line:
        found_chatlog = True
        break

if found_chatlog:
    with open('backend/app/models.py', 'w', encoding='utf-8') as f:
        f.writelines(clean_lines)
    print("Cleaned models.py")
else:
    print("Could not find the target line to truncate at.")
