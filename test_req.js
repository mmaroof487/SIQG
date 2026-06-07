const fs = require('fs');
const env = fs.readFileSync('.env', 'utf8');
const token = env.split('\n').find(l => l.startsWith('VITE_TEMP_TOKEN=')).split('=')[1].replace(/["']/g, '').trim();

fetch('http://localhost:8000/api/v1/connections/e1c1d7bd-77ab-41dc-bc0d-dd4d06cec80b/test', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token
  }
}).then(r => r.text().then(t => console.log(r.status, t)));
