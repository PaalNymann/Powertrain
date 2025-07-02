with open('app.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'app = Flask(name)' in line:
        lines.insert(i+1, 'CORS(app, origins="*")\n')
        break
with open('app.py', 'w') as f:
    f.writelines(lines)
print("CORS activation added")
