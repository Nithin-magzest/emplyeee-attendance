import qrcode
import os

def generate_qr(emp_id):
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "qrcodes")

    if not os.path.exists(folder):
        os.makedirs(folder)

    path = os.path.join(folder, f"{emp_id}.png")
    img = qrcode.make(emp_id)
    img.save(path)
    return path
