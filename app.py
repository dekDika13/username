from flask import Flask, request, jsonify
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

# Ganti dengan token bot Anda
TELEGRAM_BOT_TOKEN = '7705031894:AAGBY7cliOPmzsgFH3XnAE5RarXrvnfEfrM'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'

def check_telegram_username(username):
    """
    Fungsi untuk memeriksa apakah username Telegram tersedia menggunakan Bot API.
    """
    try:
        # Tambahkan parameter acak untuk menghindari cache
        params = {
            'chat_id': f'@{username}',
            't': random.randint(0, 1000000)  # Parameter acak untuk mencegah cache
        }
        
        # Header untuk mencegah caching
        headers = {
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache'
        }
        
        response = requests.get(f'{TELEGRAM_API_URL}/getChat', params=params, headers=headers)
        data = response.json()
        
        if response.status_code == 200 and data.get("ok"):
            # Jika respons berhasil, username ditemukan dan sudah terpakai
            return {"username": username, "available": False, "message": "Username is already taken.", "details": data}
        
        elif response.status_code == 400:
            description = data.get("description", "").lower()
            
            if "not found" in description:
                # Jika deskripsi menunjukkan 'not found', username dianggap tersedia
                return {"username": username, "available": True, "message": "Username is available.", "details": data}
            elif "available for purchase" in description:
                # Jika tersedia untuk pembelian, berarti username sudah terpakai
                return {"username": username, "available": False, "message": "Username is taken and may be available for purchase.", "details": data}
            else:
                # Jika username ditemukan tetapi error lain, berarti sudah terpakai
                return {"username": username, "available": False, "message": "Username is already taken.", "details": data}

        else:
            # Jika status tidak diketahui
            return {"username": username, "available": False, "message": "Could not determine status, please try again later.", "details": data}

    except requests.RequestException as e:
        print(f"Error checking username {username}: {e}")
        return {"username": username, "available": False, "message": "Error accessing Telegram.", "details": {"error": str(e)}}

@app.route('/check-usernames', methods=['POST'])
def check_usernames():
    data = request.get_json()
    
    if not data or 'usernames' not in data:
        return jsonify({"error": "Usernames list is required"}), 400
    
    usernames = data['usernames']
    if not isinstance(usernames, list):
        return jsonify({"error": "Usernames should be a list"}), 400

    results = []
    batch_size = 10  # Jumlah username yang akan dicek secara bersamaan
    delay_between_batches = 2  # Jeda waktu antar batch dalam detik

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for i in range(0, len(usernames), batch_size):
            # Ambil batch username untuk dicek
            batch = usernames[i:i + batch_size]

            # Kirim semua permintaan dalam batch secara paralel
            for username in batch:
                futures.append(executor.submit(check_telegram_username, username))

            # Tunggu semua permintaan dalam batch selesai
            for future in as_completed(futures):
                results.append(future.result())

            # Bersihkan futures untuk batch berikutnya
            futures.clear()

            # Tambahkan jeda antar batch untuk menghindari rate limiting
            time.sleep(delay_between_batches)
    
    return jsonify(results), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9080)
