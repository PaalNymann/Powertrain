import re
with open("app.py", "r") as f:
    content = f.read()
content = re.sub(r"(app = Flask$name$)", r"\1\nCORS(app, origins="*")", content)
with open("app.py", "w") as f:
    f.write(content)
print("CORS activation added")
