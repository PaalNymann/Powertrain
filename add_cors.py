with open('app_backup_before_cors.py', 'r') as f:
    content = f.read()
lines = content.split('\n')
lines.insert(2, 'from flask_cors import CORS')
for i, line in enumerate(lines):
    if 'app = Flask(name)' in line:
        lines.insert(i+1, 'CORS(app, origins="*")')
        break
with open('app.py', 'w') as f:
    f.write('\n'.join(lines))
print("CORS added to app.py")
