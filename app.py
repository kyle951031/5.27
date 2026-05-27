import base64
import io
import re
import requests
import cv2
import numpy as np
import easyocr
from flask import Flask, render_template, request
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


class LivePrizeUpdater:
    """負責從網路抓取最新發票中獎號碼，若失敗則使用本地預設資料。"""

    PRIZE_URL = "https://raw.githubusercontent.com/swes0123/Taiwan-Receipt-Lottery/master/prize.json"

    def __init__(self):
        self.prize_data = self.load_prize_data()

    def load_prize_data(self):
        try:
            response = requests.get(self.PRIZE_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or 'data' not in data:
                raise ValueError("獎號資料格式錯誤")
            return data['data']
        except Exception as err:
            print(f"無法更新中獎號碼：{err}，改用內建預設號碼。")
            return self.default_prize_data()

    @staticmethod
    def default_prize_data():
        return {
            'special': '56983970',
            'grand': '12345678',
            'first': ['56781234', '98765432', '24681357'],
            'second': [],
            'third': [],
            'fourth': [],
            'fifth': [],
            'sixth': [],
            'seventh': []
        }

    def get_prize_numbers(self):
        return {
            'special': self.prize_data.get('special', ''),
            'grand': self.prize_data.get('grand', ''),
            'first': self.prize_data.get('first', []),
            'second': self.prize_data.get('second', []),
            'third': self.prize_data.get('third', []),
            'fourth': self.prize_data.get('fourth', []),
            'fifth': self.prize_data.get('fifth', []),
            'sixth': self.prize_data.get('sixth', []),
            'seventh': self.prize_data.get('seventh', [])
        }


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

prize_updater = LivePrizeUpdater()
prize_numbers = prize_updater.get_prize_numbers()
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)


def extract_eight_digit_numbers(text):
    return list(dict.fromkeys(re.findall(r"\b\d{8}\b", text)))


def judge_number(number):
    prize = prize_numbers
    if number == prize.get('special'):
        return '特別獎（200 萬）'
    if number == prize.get('grand'):
        return '特獎（200 萬）'

    for first_num in prize.get('first', []):
        if number == first_num:
            return '頭獎（20 萬）'
        if number[-7:] == first_num[-7:]:
            return '二獎（4 萬）'
        if number[-6:] == first_num[-6:]:
            return '三獎（1 萬）'
        if number[-5:] == first_num[-5:]:
            return '四獎（4,000 元）'
        if number[-4:] == first_num[-4:]:
            return '五獎（1,000 元）'
        if number[-3:] == first_num[-3:]:
            return '六獎（200 元）'

    if number in prize.get('seventh', []):
        return '增開六獎（200 元）'

    return '未中獎'


def build_pie_chart(win_count, total_count):
    figure = Figure(figsize=(4, 3), dpi=100)
    ax = figure.add_subplot(111)
    win = win_count
    lose = max(total_count - win, 0)
    labels = [f'中獎 ({win})', f'未中獎 ({lose})']
    sizes = [win, lose]
    colors = ['#4CAF50', '#F44336']
    ax.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90, colors=colors)
    ax.axis('equal')
    ax.set_title('本次檢測中獎率')

    canvas = FigureCanvas(figure)
    buf = io.BytesIO()
    canvas.print_png(buf)
    data = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{data}'


def ocr_image_from_base64(image_data):
    header, encoded = image_data.split(',', 1) if ',' in image_data else ('', image_data)
    decoded = base64.b64decode(encoded)
    image_array = np.frombuffer(decoded, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('無法解析圖片資料')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return reader.readtext(gray, detail=0, paragraph=True)


@app.route('/', methods=['GET', 'POST'])
def index():
    result_text = None
    detected_numbers = []
    pie_chart = None
    prize_info = prize_numbers

    if request.method == 'POST':
        image_data = request.form.get('snapshot') or ''
        if not image_data:
            message = '請先拍照或上傳圖片，才能進行 OCR 對獎。'
            return render_template('index.html', result_text=message, detected_numbers=[], pie_chart=None, prize_info=prize_info)

        try:
            ocr_results = ocr_image_from_base64(image_data)
            text = ' '.join(ocr_results)
            detected_numbers = extract_eight_digit_numbers(text)
            if not detected_numbers:
                result_text = '未偵測到 8 碼號碼，請重拍或上傳更清晰的發票圖片。'
                pie_chart = build_pie_chart(0, 0)
            else:
                match_texts = []
                win_count = 0
                for number in detected_numbers:
                    prize = judge_number(number)
                    if prize != '未中獎':
                        win_count += 1
                    match_texts.append(f'{number} → {prize}')
                result_text = '；'.join(match_texts)
                pie_chart = build_pie_chart(win_count, len(detected_numbers))
        except Exception as err:
            result_text = f'處理失敗：{err}'
            pie_chart = build_pie_chart(0, 0)

    return render_template(
        'index.html',
        result_text=result_text,
        detected_numbers=detected_numbers,
        pie_chart=pie_chart,
        prize_info=prize_info
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
