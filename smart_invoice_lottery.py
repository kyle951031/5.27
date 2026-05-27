import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import requests
import json
import re
import easyocr
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class LivePrizeUpdater:
    """負責從網路抓取最新發票中獎號碼，若失敗則回退到本地預設號碼。"""

    PRIZE_URL = "https://raw.githubusercontent.com/swes0123/Taiwan-Receipt-Lottery/master/prize.json"

    def __init__(self):
        self.prize_data = self.load_prize_data()

    def load_prize_data(self):
        """嘗試從網路下載 JSON，若失敗則使用本地預設資料。"""
        try:
            response = requests.get(self.PRIZE_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            # 確保資料內含必要欄位
            if not isinstance(data, dict) or 'data' not in data:
                raise ValueError("獎號資料格式錯誤")
            prize_info = data['data']
            return prize_info
        except Exception as err:
            print(f"無法更新中獎號碼：{err}，改用內建預設號碼。")
            return self.default_prize_data()

    @staticmethod
    def default_prize_data():
        """本地預設中獎號碼，可在斷網時使用。"""
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
        """回傳整理後的中獎號碼清單。"""
        prize_numbers = {
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
        return prize_numbers


class InvoiceApp(tk.Tk):
    """主應用程式，整合 Tkinter 介面、OpenCV 即時影像、EasyOCR 文字辨識與中獎比對。"""

    def __init__(self):
        super().__init__()
        self.title("智慧鏡頭即時發票對獎系統")
        self.geometry("1200x720")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.prize_updater = LivePrizeUpdater()
        self.prize_numbers = self.prize_updater.get_prize_numbers()

        # 初始化攝影機
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            messagebox.showerror("相機錯誤", "無法開啟攝影機，請確認是否已連接或驅動程式正常。")
            self.destroy()
            return

        # 初始化 OCR
        self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

        self.create_widgets()
        self.update_frame()
        self.draw_prize_pie([], 0)

    def create_widgets(self):
        """建立 Tkinter 介面元件佈局。"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=10, pady=10)

        self.canvas = tk.Canvas(left_frame, bg='black', width=760, height=560)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(right_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_check = ttk.Button(controls_frame, text="觸發 AI 對獎", command=self.run_invoice_check)
        self.btn_check.pack(fill=tk.X, pady=5)

        self.detected_label = ttk.Label(right_frame, text="偵測到的號碼：--", font=("Helvetica", 16, "bold"), wraplength=380)
        self.detected_label.pack(fill=tk.X, pady=(10, 5))

        self.result_label = ttk.Label(right_frame, text="對獎結果：尚未執行", font=("Helvetica", 16, "bold"), foreground='#1a73e8', wraplength=380)
        self.result_label.pack(fill=tk.X, pady=(0, 10))

        chart_frame = ttk.LabelFrame(right_frame, text="中獎統計圓餅圖")
        chart_frame.pack(fill=tk.BOTH, expand=True)

        self.figure = Figure(figsize=(4.6, 4.0), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas_chart = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas_chart.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_frame(self):
        """從攝影機讀取影格並在 Canvas 上顯示。"""
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            self.current_frame = frame.copy()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)
            image = image.resize((760, 560), Image.ANTIALIAS)
            self.photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        else:
            self.current_frame = None
        self.after(30, self.update_frame)

    def run_invoice_check(self):
        """按鈕事件：擷取當前畫面、OCR 文字辨識、正規比對中獎號碼、更新介面與圖表。"""
        if not hasattr(self, 'current_frame') or self.current_frame is None:
            messagebox.showwarning("警告", "目前沒有可用的相機畫面，請重新啟動程式或檢查相機。")
            return

        frame = self.current_frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        # 如果畫面過大，先縮小以加快 OCR
        scale = 1.0
        if max(h, w) > 1200:
            scale = 1200.0 / max(h, w)
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)))

        results = self.reader.readtext(gray, detail=0, paragraph=True)
        text = " ".join(results)
        numbers = self.extract_eight_digit_numbers(text)

        self.detected_label.config(text=f"偵測到的號碼：{', '.join(numbers) if numbers else '未偵測到 8 碼號碼'}")

        prize_text, prize_counts = self.compare_to_prize(numbers)
        self.result_label.config(text=f"對獎結果：{prize_text}")
        self.draw_prize_pie(numbers, prize_counts)

    @staticmethod
    def extract_eight_digit_numbers(text):
        """使用正規表示式擷取所有 8 碼純數字。"""
        candidates = re.findall(r"\b\d{8}\b", text)
        return list(dict.fromkeys(candidates))

    def compare_to_prize(self, candidates):
        """將擷取到的 8 碼號碼比對中獎號碼，回傳結果文字與統計資料。"""
        if not candidates:
            return ("未偵測到可比對的 8 碼號碼。", 0)

        match_texts = []
        win_count = 0
        for number in candidates:
            prize = self.judge_number(number)
            if prize != '未中獎':
                win_count += 1
            match_texts.append(f"{number} -> {prize}")

        if win_count == 0:
            summary = "很遺憾，這次沒有中獎。"
        else:
            summary = f"共偵測 {len(candidates)} 組號碼，其中 {win_count} 組中獎。\n" + "；".join(match_texts)

        return (summary, win_count)

    def judge_number(self, number):
        """判斷單一號碼對應到哪一個級距的中獎結果。"""
        prize = self.prize_numbers
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

    def draw_prize_pie(self, candidates, win_count):
        """使用 Matplotlib 繪製中獎統計圓餅圖。"""
        total = max(len(candidates), 1)
        win = win_count
        lose = total - win

        labels = [f'中獎 ({win})', f'未中獎 ({lose})']
        sizes = [win, lose]
        colors = ['#4CAF50', '#F44336']

        self.ax.clear()
        self.ax.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90, colors=colors)
        self.ax.axis('equal')
        self.ax.set_title('本次檢測中獎率')
        self.figure.tight_layout()
        self.canvas_chart.draw()

    def on_close(self):
        """關閉視窗時釋放資源。"""
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        self.destroy()


if __name__ == '__main__':
    app = InvoiceApp()
    app.mainloop()
