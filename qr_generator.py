import qrcode
import os

def generate_qr(emp_id):

    folder = "static/qrcodes"

    if not os.path.exists(folder):
        os.makedirs(folder)

    path = f"{folder}/{emp_id}.png"

    img = qrcode.make(emp_id)
    img.save(path)

    return path