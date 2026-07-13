import os
import boto3
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import pytz

app = Flask(__name__)

# Konfigurasi koneksi ke MinIO lokal
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='AKIAIOSFODNN7EXAMPLE',
    aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    region_name='us-east-1'
)

BUCKET_NAME = 'galeri-mahasiswa-bucket'

def init_s3():
    try:
        s3_client.create_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' berhasil dibuat di MinIO.")
    except s3_client.exceptions.BucketAlreadyExists:
        pass
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        pass
    except Exception as e:
        print(f"Gagal menginisialisasi S3: {e}")

@app.route('/')
def index():
    karya_list = []
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            # Mengurutkan file berdasarkan waktu upload terbaru
            sorted_contents = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
            
            # Zona waktu lokal Indonesia (WIB)
            tz_jakarta = pytz.timezone('Asia/Jakarta')
            
            for item in sorted_contents:
                file_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME, 'Key': item['Key']},
                    ExpiresIn=3600
                )
                
                # Mengubah zona waktu UTC dari S3 ke WIB dan memformat tampilannya
                waktu_utc = item['LastModified']
                waktu_lokal = waktu_utc.astimezone(tz_jakarta)
                tanggal_str = waktu_lokal.strftime('%d %b %Y, %H:%M WIB')
                
                # Menghitung konversi ukuran file (Bytes ke KB/MB)
                ukuran_bytes = item['Size']
                if ukuran_bytes < 1024 * 1024:
                    ukuran_str = f"{round(ukuran_bytes / 1024, 1)} KB"
                else:
                    ukuran_str = f"{round(ukuran_bytes / (1024 * 1024), 1)} MB"
                
                karya_list.append({
                    'filename': item['Key'], 
                    'url': file_url,
                    'date': tanggal_str,
                    'size': ukuran_str
                })
    except Exception as e:
        print(f"Error membaca data S3: {e}")
        
    return render_template('index.html', karya=karya_list)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file_karya' not in request.files:
        return redirect(request.url)
        
    file = request.files['file_karya']
    if file.filename == '':
        return redirect(request.url)
        
    if file:
        try:
            s3_client.upload_fileobj(file, BUCKET_NAME, file.filename)
            print(f"File {file.filename} sukses di-upload ke MinIO.")
        except Exception as e:
            print(f"Gagal mengunggah file: {e}")
            
        return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete_file():
    try:
        filename = request.form.get('filename')
        if filename:
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=filename)
            print(f"File {filename} berhasil dihapus dari MinIO.")
    except Exception as e:
        print(f"Gagal menghapus file: {e}")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_s3()
    app.run(debug=True, port=5000)