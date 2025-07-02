with open('app.py', 'r') as f:
    lines = f.readlines()

# Legg inn import etter line 2
lines.insert(2, 'from flask_cors import CORS\n')

# Finn linjen med Flask app og legg til CORS(app)
for i, line in enumerate(lines):
    if 'app = Flask(__name__)' in line:
        lines.insert(i + 1, 'CORS(app, origins="*")\n')
        break

with open('app.py', 'w') as f:
    f.writelines(lines)
